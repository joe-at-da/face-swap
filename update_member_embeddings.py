#!/usr/bin/env python3
"""
Systematic script to identify and update parliament member embeddings with poor matches.
This script analyzes member embeddings against real Parliament TV frames and updates
embeddings for members with poor matching scores.

Usage:
    python update_member_embeddings.py [--video_path VIDEO_PATH] [--threshold THRESHOLD] [--update]

Arguments:
    --video_path: Path to the Parliament TV video file (default: uses a sample video)
    --threshold: Similarity threshold below which to update embeddings (default: 0.7)
    --update: If provided, updates embeddings; otherwise, just reports issues
"""
import os
import sys
import json
import logging
import argparse
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Tuple

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.db.session import get_db
from backend.services.recognition.face_recognition import FaceRecognitionService
from backend.services.recognition.member_matching.matcher import ParliamentMemberMatcher
from backend.services.recognition.member_matching.database import load_members, save_members_to_cache
from backend.services.recognition.member_matching.embedding import compute_similarity
from backend.services.integration.supabase_client import SupabaseService

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
CACHE_PATH = "/app/data/cache/parliament_members.json"
MP_PHOTOS_DIR = "/app/data/mp_photos"
FRAMES_OUTPUT_DIR = "/app/data/member_frames"
SAMPLE_VIDEO_PATH = "/app/data/sample_videos/parliament_sample.mp4"
FRAME_INTERVAL = 10  # Extract a frame every 10 seconds


def extract_frames(video_path: str, output_dir: str, interval: int = FRAME_INTERVAL) -> List[str]:
    """
    Extract frames from a video at regular intervals
    
    Args:
        video_path: Path to the video file
        output_dir: Directory to save extracted frames
        interval: Interval in seconds between frames
        
    Returns:
        List of paths to extracted frames
    """
    import cv2
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Open the video
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        logger.error(f"Error opening video file: {video_path}")
        return []
    
    # Get video properties
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps
    
    logger.info(f"Video: {video_path}")
    logger.info(f"Duration: {duration:.2f} seconds")
    logger.info(f"FPS: {fps}")
    logger.info(f"Total frames: {total_frames}")
    logger.info(f"Extracting frames every {interval} seconds")
    
    frame_paths = []
    
    # Extract frames at regular intervals
    for second in range(0, int(duration), interval):
        # Set the position
        cap.set(cv2.CAP_PROP_POS_MSEC, second * 1000)
        
        # Read the frame
        ret, frame = cap.read()
        if not ret:
            logger.warning(f"Failed to read frame at {second} seconds")
            continue
        
        # Save the frame
        frame_path = os.path.join(output_dir, f"frame_{second}.jpg")
        cv2.imwrite(frame_path, frame)
        frame_paths.append(frame_path)
        
        logger.info(f"Extracted frame at {second} seconds: {frame_path}")
    
    # Release the video
    cap.release()
    
    return frame_paths


def detect_faces_in_frames(face_service: FaceRecognitionService, frame_paths: List[str]) -> Dict[str, List[Dict]]:
    """
    Detect faces in all frames
    
    Args:
        face_service: FaceRecognitionService instance
        frame_paths: List of paths to frames
        
    Returns:
        Dictionary mapping frame paths to lists of detected faces
    """
    frame_faces = {}
    
    for frame_path in frame_paths:
        faces = face_service.detect_faces(frame_path)
        if faces:
            frame_faces[frame_path] = faces
            logger.info(f"Detected {len(faces)} faces in {frame_path}")
        else:
            logger.info(f"No faces detected in {frame_path}")
    
    return frame_faces


def extract_embeddings(face_service: FaceRecognitionService, frame_faces: Dict[str, List[Dict]]) -> Dict[str, List[Dict]]:
    """
    Extract embeddings for all detected faces
    
    Args:
        face_service: FaceRecognitionService instance
        frame_faces: Dictionary mapping frame paths to lists of detected faces
        
    Returns:
        Dictionary mapping frame paths to lists of faces with embeddings
    """
    frame_embeddings = {}
    
    for frame_path, faces in frame_faces.items():
        face_embeddings = []
        
        for face in faces:
            face_box = face['box']
            embedding_result = face_service.extract_face_embedding(frame_path, face_box)
            
            if embedding_result:
                face_with_embedding = face.copy()
                face_with_embedding['embedding'] = embedding_result['embedding']
                face_embeddings.append(face_with_embedding)
                logger.info(f"Extracted embedding for face in {frame_path}")
            else:
                logger.warning(f"Failed to extract embedding for face in {frame_path}")
        
        if face_embeddings:
            frame_embeddings[frame_path] = face_embeddings
    
    return frame_embeddings


def match_faces_to_members(matcher: ParliamentMemberMatcher, frame_embeddings: Dict[str, List[Dict]]) -> Dict[str, List[Dict]]:
    """
    Match faces to members
    
    Args:
        matcher: ParliamentMemberMatcher instance
        frame_embeddings: Dictionary mapping frame paths to lists of faces with embeddings
        
    Returns:
        Dictionary mapping frame paths to lists of faces with match results
    """
    frame_matches = {}
    
    for frame_path, faces in frame_embeddings.items():
        face_matches = []
        
        for face in faces:
            embedding = face['embedding']
            match_result = matcher.match_face_to_member({'embedding': embedding}, confidence_threshold=0.1)
            
            if match_result:
                face_with_match = face.copy()
                face_with_match['match'] = match_result
                face_matches.append(face_with_match)
                
                member_id = match_result.get('member_id')
                member_name = match_result.get('name')
                confidence = match_result.get('confidence')
                
                logger.info(f"Matched face in {frame_path} to {member_name} (ID: {member_id}) with confidence {confidence:.4f}")
            else:
                logger.warning(f"No match found for face in {frame_path}")
        
        if face_matches:
            frame_matches[frame_path] = face_matches
    
    return frame_matches


def identify_poor_matches(matcher: ParliamentMemberMatcher, frame_matches: Dict[str, List[Dict]], threshold: float = 0.7) -> List[Tuple[str, Dict, Dict]]:
    """
    Identify poor matches where the confidence is below the threshold
    
    Args:
        matcher: ParliamentMemberMatcher instance
        frame_matches: Dictionary mapping frame paths to lists of faces with match results
        threshold: Confidence threshold below which a match is considered poor
        
    Returns:
        List of tuples (frame_path, face, match_result) for poor matches
    """
    poor_matches = []
    
    for frame_path, faces in frame_matches.items():
        for face in faces:
            match_result = face['match']
            confidence = match_result.get('confidence', 0.0)
            
            if confidence < threshold:
                poor_matches.append((frame_path, face, match_result))
                
                member_id = match_result.get('member_id')
                member_name = match_result.get('name')
                
                logger.info(f"Poor match: {member_name} (ID: {member_id}) with confidence {confidence:.4f} in {frame_path}")
    
    return poor_matches


def update_member_embedding(face_service: FaceRecognitionService, member_id: str, frame_path: str, face_box: Dict) -> bool:
    """
    Update a member's embedding with one extracted from a frame
    
    Args:
        face_service: FaceRecognitionService instance
        member_id: Member ID
        frame_path: Path to the frame
        face_box: Face bounding box
        
    Returns:
        True if successful, False otherwise
    """
    # Extract embedding for the face
    embedding_result = face_service.extract_face_embedding(frame_path, face_box)
    
    if not embedding_result:
        logger.error(f"Failed to extract embedding for member {member_id} from {frame_path}")
        return False
    
    # Get the embedding
    embedding = embedding_result['embedding']
    
    # Convert to list for JSON serialization
    if hasattr(embedding, 'flatten'):
        embedding_list = embedding.flatten().tolist()
    else:
        embedding_list = embedding
    
    # Save the embedding to the MP photos directory
    mp_photos_path = f"{MP_PHOTOS_DIR}/{member_id}.json"
    cache_path = f"/app/data/cache/mp_embeddings/{member_id}.json"
    
    # Create directories if they don't exist
    os.makedirs(os.path.dirname(mp_photos_path), exist_ok=True)
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    
    # Save the embedding
    with open(mp_photos_path, 'w') as f:
        json.dump(embedding_list, f)
    logger.info(f"Saved embedding to {mp_photos_path}")
    
    # Also save to cache location
    with open(cache_path, 'w') as f:
        json.dump(embedding_list, f)
    logger.info(f"Saved embedding to cache location: {cache_path}")
    
    # Save a copy of the face image for reference
    face_image_path = f"{MP_PHOTOS_DIR}/{member_id}.jpg"
    
    # Extract the face region from the frame
    import cv2
    image = cv2.imread(frame_path)
    if image is not None:
        x, y, w, h = face_box
        face_image = image[y:y+h, x:x+w]
        cv2.imwrite(face_image_path, face_image)
        logger.info(f"Saved face image to {face_image_path}")
    
    return True


def update_member_embeddings_in_cache(supabase_service: SupabaseService, member_ids: List[str], frame_matches: Dict[str, List[Dict]]) -> bool:
    """
    Update member embeddings in the cache file
    
    Args:
        supabase_service: SupabaseService instance
        member_ids: List of member IDs to update
        frame_matches: Dictionary mapping frame paths to lists of faces with match results
        
    Returns:
        True if successful, False otherwise
    """
    # Get all members
    members = load_members(supabase_service, CACHE_PATH)
    if not members:
        logger.error("Failed to load parliament members")
        return False
    
    # Find the best match for each member
    for member_id in member_ids:
        best_match = None
        best_confidence = 0.0
        
        for frame_path, faces in frame_matches.items():
            for face in faces:
                match_result = face['match']
                matched_id = match_result.get('member_id')
                confidence = match_result.get('confidence', 0.0)
                
                if str(matched_id) == str(member_id) and confidence > best_confidence:
                    best_match = face
                    best_confidence = confidence
        
        if best_match:
            # Update the member's embedding in the cache
            embedding = best_match['embedding']
            
            # Convert to list for JSON serialization
            if hasattr(embedding, 'flatten'):
                embedding_list = embedding.flatten().tolist()
            else:
                embedding_list = embedding
            
            # Find the member in the cache
            for member in members:
                if str(member.get('member_id')) == str(member_id):
                    member['embedding'] = embedding_list
                    logger.info(f"Updated embedding for {member.get('name')} (ID: {member_id}) in memory")
                    break
    
    # Save the updated members to the cache
    save_members_to_cache(members, CACHE_PATH)
    logger.info(f"Saved updated embeddings to cache: {CACHE_PATH}")
    
    return True


def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Update parliament member embeddings')
    parser.add_argument('--video_path', type=str, default=None,
                        help='Path to the Parliament TV video file')
    parser.add_argument('--frame_path', type=str, default=None,
                        help='Path to a single Parliament TV frame')
    parser.add_argument('--frames_dir', type=str, default=None,
                        help='Path to a directory containing Parliament TV frames')
    parser.add_argument('--threshold', type=float, default=0.7,
                        help='Similarity threshold below which to update embeddings')
    parser.add_argument('--update', action='store_true',
                        help='If provided, updates embeddings; otherwise, just reports issues')
    
    args = parser.parse_args()
    
    # Initialize services
    db = next(get_db())
    face_service = FaceRecognitionService()
    matcher = ParliamentMemberMatcher(db)
    supabase_service = SupabaseService()
    
    # Load parliament members
    matcher.load_parliament_members()
    logger.info(f'Loaded {len(matcher.members)} members and {len(matcher.member_embeddings)} embeddings')
    
    # Create output directory for frames
    os.makedirs(FRAMES_OUTPUT_DIR, exist_ok=True)
    
    # Get frame paths based on input arguments
    frame_paths = []
    
    if args.video_path:
        # Extract frames from the video
        logger.info(f"Extracting frames from video: {args.video_path}")
        frame_paths = extract_frames(args.video_path, FRAMES_OUTPUT_DIR)
    elif args.frame_path:
        # Use a single frame
        logger.info(f"Using single frame: {args.frame_path}")
        frame_paths = [args.frame_path]
    elif args.frames_dir:
        # Use all frames in a directory
        logger.info(f"Using frames from directory: {args.frames_dir}")
        import glob
        frame_paths = glob.glob(os.path.join(args.frames_dir, "*.jpg"))
        logger.info(f"Found {len(frame_paths)} frames in directory")
    else:
        logger.error("No input source specified. Use --video_path, --frame_path, or --frames_dir")
        return
    
    # Detect faces in frames
    frame_faces = detect_faces_in_frames(face_service, frame_paths)
    
    # Extract embeddings for detected faces
    frame_embeddings = extract_embeddings(face_service, frame_faces)
    
    # Match faces to members
    frame_matches = match_faces_to_members(matcher, frame_embeddings)
    
    # Identify poor matches
    poor_matches = identify_poor_matches(matcher, frame_matches, args.threshold)
    
    # Report poor matches
    logger.info(f"Found {len(poor_matches)} poor matches below threshold {args.threshold}")
    
    if args.update and poor_matches:
        # Update embeddings for poor matches
        member_ids_to_update = set()
        
        for frame_path, face, match_result in poor_matches:
            member_id = match_result.get('member_id')
            member_ids_to_update.add(str(member_id))
        
        logger.info(f"Updating embeddings for {len(member_ids_to_update)} members")
        
        # Update embeddings in the cache
        success = update_member_embeddings_in_cache(supabase_service, list(member_ids_to_update), frame_matches)
        
        if success:
            logger.info("Successfully updated member embeddings")
        else:
            logger.error("Failed to update member embeddings")
    
    logger.info("Done")


if __name__ == "__main__":
    main()
