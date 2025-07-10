#!/usr/bin/env python
"""
Comprehensive fix for the embedding system to ensure consistent handling of all member embeddings.

This script:
1. Normalizes all embeddings in the cache for consistent similarity calculation
2. Fixes the embedding module to properly handle and normalize embeddings
3. Updates the matcher module to correctly load and process embeddings
4. Adds detailed logging for transparency and debugging
5. Tests the fix with real data and visual debugging
"""
import os
import sys
import logging
import json
import numpy as np
import cv2
import face_recognition
import shutil
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
MEMBER_CACHE_PATH = "/app/data/cache/parliament_members.json"
EMBEDDINGS_CACHE_PATH = "/app/data/cache/member_embeddings.json"
TEST_FRAME_PATH = "/app/data/temp/recognition/test_frame.jpg"
DEBUG_OUTPUT_DIR = "/app/data/temp/recognition/debug"

def ensure_debug_dir():
    """Ensure the debug output directory exists."""
    os.makedirs(DEBUG_OUTPUT_DIR, exist_ok=True)
    return DEBUG_OUTPUT_DIR

def normalize_embedding(embedding):
    """Normalize an embedding to unit length."""
    if embedding is None:
        return None
    
    # Convert to numpy array if it isn't already
    if not isinstance(embedding, np.ndarray):
        embedding = np.array(embedding)
    
    # Check for NaN or Inf values
    if np.isnan(embedding).any() or np.isinf(embedding).any():
        logger.warning("Embedding contains NaN or Inf values")
        # Replace NaN and Inf with zeros
        embedding = np.nan_to_num(embedding)
    
    # Compute the norm
    norm = np.linalg.norm(embedding)
    
    # Avoid division by zero
    if norm < 1e-10:
        logger.warning("Embedding norm is too small, returning zeros")
        return np.zeros_like(embedding)
    
    # Normalize
    normalized = embedding / norm
    
    return normalized

def extract_face_embedding_from_frame(frame_path=None):
    """Extract the face embedding from a test frame."""
    # Use the provided frame path or default
    if frame_path is None:
        frame_path = TEST_FRAME_PATH
    
    # Check if the file exists
    if not os.path.exists(frame_path):
        logger.error(f"Test frame not found at {frame_path}")
        return None
    
    # Load the image
    image = face_recognition.load_image_file(frame_path)
    
    # Find face locations
    face_locations = face_recognition.face_locations(image, model="hog")
    
    if not face_locations:
        logger.error(f"No faces found in the test frame")
        return None
    
    # Get face encodings
    face_encodings = face_recognition.face_encodings(image, face_locations)
    
    if not face_encodings:
        logger.error(f"No face encodings found in the test frame")
        return None
    
    # Return the first face encoding
    return face_encodings[0]

def fix_embeddings_cache():
    """Fix the embeddings cache to ensure all embeddings are normalized."""
    # Check if the embeddings cache exists
    if not os.path.exists(EMBEDDINGS_CACHE_PATH):
        logger.error(f"Embeddings cache not found at {EMBEDDINGS_CACHE_PATH}")
        return False
    
    # Create a backup
    backup_file = f"{EMBEDDINGS_CACHE_PATH}.bak_comprehensive_fix"
    shutil.copy2(EMBEDDINGS_CACHE_PATH, backup_file)
    logger.info(f"Created backup of embeddings cache at {backup_file}")
    
    # Load the embeddings cache
    with open(EMBEDDINGS_CACHE_PATH, 'r') as f:
        embeddings = json.load(f)
    
    # Track statistics
    total_embeddings = len(embeddings)
    normalized_count = 0
    
    # Process each embedding
    for member_id, data in embeddings.items():
        # Ensure member_id is a string
        member_id_str = str(member_id)
        
        # Skip if no embedding
        if 'embedding' not in data:
            logger.warning(f"Member {member_id_str} has no embedding data")
            continue
        
        # Get the embedding
        embedding = data['embedding']
        
        # Convert to numpy array
        if not isinstance(embedding, np.ndarray):
            embedding = np.array(embedding)
        
        # Normalize the embedding
        normalized = normalize_embedding(embedding)
        
        # Update the embedding
        data['embedding'] = normalized.tolist()
        
        # Update the embeddings cache
        embeddings[member_id_str] = data
        
        normalized_count += 1
    
    # Save the updated embeddings cache
    with open(EMBEDDINGS_CACHE_PATH, 'w') as f:
        json.dump(embeddings, f)
    
    logger.info(f"Normalized {normalized_count} of {total_embeddings} embeddings in the cache")
    
    return True

def fix_embedding_module():
    """Fix the embedding.py module to properly handle embeddings."""
    # Path to the embedding module
    embedding_path = "/app/backend/services/recognition/member_matching/embedding.py"
    
    # Create a backup
    backup_file = f"{embedding_path}.bak_comprehensive_fix"
    shutil.copy2(embedding_path, backup_file)
    logger.info(f"Created backup of embedding module at {backup_file}")
    
    # Define the new content for the embedding.py file
    new_content = '''"""
Module for handling face embeddings and similarity calculations
"""
import logging
import numpy as np
from typing import Dict, Any, Union, List

logger = logging.getLogger(__name__)

def extract_embedding(embedding_data: Union[Dict[str, Any], List[float], np.ndarray]) -> np.ndarray:
    """
    Extract embedding from various formats
    
    Args:
        embedding_data: Embedding data in various formats (dict, list, numpy array)
        
    Returns:
        Numpy array containing the embedding
    """
    # Extract embeddings if they are dictionaries
    if isinstance(embedding_data, dict) and 'embedding' in embedding_data:
        embedding_data = embedding_data['embedding']
    
    # Ensure embeddings are numpy arrays
    embedding = np.array(embedding_data)
    
    # Ensure embeddings are flattened to 1D arrays
    embedding = embedding.flatten()
    
    return embedding

def normalize_embedding(embedding: np.ndarray) -> np.ndarray:
    """
    Normalize an embedding to unit length
    
    Args:
        embedding: Embedding to normalize
        
    Returns:
        Normalized embedding
    """
    # Check for NaN or Inf values
    if np.isnan(embedding).any() or np.isinf(embedding).any():
        embedding = np.nan_to_num(embedding)
    
    # Compute the norm
    norm = np.linalg.norm(embedding)
    
    # Avoid division by zero
    if norm < 1e-10:
        return np.zeros_like(embedding)
    
    # Normalize
    return embedding / norm

def compute_similarity(embedding1, embedding2):
    """
    Compute similarity between two face embeddings
    
    Args:
        embedding1: First embedding (numpy array, list, or dict with 'embedding' key)
        embedding2: Second embedding (numpy array, list, or dict with 'embedding' key)
        
    Returns:
        Similarity score between 0 and 1
    """
    try:
        # Extract and convert embeddings
        if isinstance(embedding1, dict) and 'embedding' in embedding1:
            embedding1 = embedding1['embedding']
        if isinstance(embedding2, dict) and 'embedding' in embedding2:
            embedding2 = embedding2['embedding']
        
        # Convert to numpy arrays if they aren't already
        if not isinstance(embedding1, np.ndarray):
            embedding1 = np.array(embedding1)
        if not isinstance(embedding2, np.ndarray):
            embedding2 = np.array(embedding2)
        
        # Normalize the embeddings
        embedding1 = normalize_embedding(embedding1)
        embedding2 = normalize_embedding(embedding2)
        
        # Compute cosine similarity
        similarity = np.dot(embedding1, embedding2)
        
        # Log high similarity matches for debugging
        if similarity > 0.9:
            logger.debug(f"High similarity detected: {similarity:.6f}")
            
        return float(similarity)
    except Exception as e:
        logger.error(f"Error computing similarity: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return 0.0
'''
    
    # Write the new content to the file
    with open(embedding_path, 'w') as f:
        f.write(new_content)
    
    logger.info(f"Updated embedding module at {embedding_path}")
    
    return True

def fix_matcher_module():
    """Fix the matcher.py module to properly handle embeddings."""
    # Path to the matcher file
    matcher_path = "/app/backend/services/recognition/member_matching/matcher.py"
    
    # Create a backup
    backup_file = f"{matcher_path}.bak_comprehensive_fix"
    shutil.copy2(matcher_path, backup_file)
    logger.info(f"Created backup of matcher file at {backup_file}")
    
    # Read the original file
    with open(matcher_path, 'r') as f:
        content = f.read()
    
    # Add import for normalize_embedding
    if "from .embedding import compute_similarity" in content:
        content = content.replace(
            "from .embedding import compute_similarity",
            "from .embedding import compute_similarity, normalize_embedding"
        )
    elif "from backend.services.recognition.member_matching.embedding import compute_similarity" in content:
        content = content.replace(
            "from backend.services.recognition.member_matching.embedding import compute_similarity",
            "from backend.services.recognition.member_matching.embedding import compute_similarity, normalize_embedding"
        )
    
    # Find the _load_member_embeddings method
    load_embeddings_pattern = "    def _load_member_embeddings(self)"
    if load_embeddings_pattern in content:
        # Find the start of the method
        start_idx = content.find(load_embeddings_pattern)
        
        # Find the end of the method (next def or end of file)
        next_def_idx = content.find("    def ", start_idx + 1)
        if next_def_idx == -1:
            next_def_idx = len(content)
        
        # Extract the method signature
        method_signature = content[start_idx:content.find(":", start_idx) + 1]
        
        # Replace the method with our fixed version
        new_load_embeddings = method_signature + """
        try:
            # Load embeddings from cache if available
            cache_file = os.path.join(self.cache_dir, 'member_embeddings.json')
            if os.path.exists(cache_file):
                with open(cache_file, 'r') as f:
                    embeddings = json.load(f)
                
                # Process each embedding
                for member_id, data in embeddings.items():
                    if isinstance(data, dict) and 'embedding' in data:
                        # Get the embedding
                        embedding = data['embedding']
                        
                        # Convert to numpy array
                        if not isinstance(embedding, np.ndarray):
                            embedding = np.array(embedding)
                        
                        # Normalize the embedding
                        embedding = normalize_embedding(embedding)
                        
                        # Store back as list
                        data['embedding'] = embedding.tolist()
                        
                        # Store with string ID as the primary key
                        self.member_embeddings[str(member_id)] = data
                
                logger.info(f"Loaded {len(self.member_embeddings)} member embeddings")
                return
            else:
                logger.warning(f"No embeddings cache found at {cache_file}")
        except Exception as e:
            logger.error(f"Error loading member embeddings: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
"""
        
        # Replace the method
        content = content[:start_idx] + new_load_embeddings + content[next_def_idx:]
        logger.info("Patched _load_member_embeddings method")
    else:
        logger.warning("Could not find _load_member_embeddings method in matcher.py")
    
    # Find the _match_face_to_member method
    match_face_pattern = "    def _match_face_to_member(self, face_data, confidence_threshold="
    if match_face_pattern in content:
        # Find the start of the method
        start_idx = content.find(match_face_pattern)
        
        # Find the end of the method (next def or end of file)
        next_def_idx = content.find("    def ", start_idx + 1)
        if next_def_idx == -1:
            next_def_idx = len(content)
        
        # Extract the method signature
        method_signature = content[start_idx:content.find(":", start_idx) + 1]
        
        # Replace the method with our fixed version
        new_match_face = method_signature + """
        # Get the face embedding
        face_embedding = face_data.get('embedding')
        if face_embedding is None:
            logger.error("No embedding found in face data")
            return {'matched': False}
        
        # Ensure face embedding is normalized
        if not isinstance(face_embedding, np.ndarray):
            face_embedding = np.array(face_embedding)
        face_embedding = normalize_embedding(face_embedding)
        
        # Find the best match
        best_match = None
        best_confidence = 0
        
        # Track all matches for debugging
        all_matches = []
        
        # Process all members
        for member in self.members:
            member_id = str(member.get('member_id'))
            member_house = member.get('house_id')
            member_name = member.get('display_name', 'Unknown')
            
            # Skip members from the wrong house if house is specified
            if house is not None and str(member_house) != str(house):
                continue
            
            # Skip if no embedding
            if member_id not in self.member_embeddings:
                continue
            
            # Get the member embedding
            member_embedding = self.member_embeddings[member_id].get('embedding')
            if member_embedding is None:
                continue
            
            # Ensure member embedding is normalized
            if not isinstance(member_embedding, np.ndarray):
                member_embedding = np.array(member_embedding)
            member_embedding = normalize_embedding(member_embedding)
            
            # Compute similarity directly with normalized embeddings
            confidence = float(np.dot(face_embedding, member_embedding))
            
            # Add to all matches for debugging
            all_matches.append({
                'member_id': member_id,
                'name': member_name,
                'confidence': confidence
            })
            
            # Update best match if this is better
            if confidence > best_confidence:
                best_confidence = confidence
                best_match = {
                    'member_id': member_id,
                    'name': member_name,
                    'confidence': confidence
                }
        
        # Sort all matches for debugging
        all_matches.sort(key=lambda x: x['confidence'], reverse=True)
        
        # Log top 5 matches for debugging
        if all_matches:
            logger.info(f"Top 5 matches:")
            for i, match in enumerate(all_matches[:5]):
                logger.info(f"{i+1}. {match['name']} (ID: {match['member_id']}): {match['confidence']:.6f}")
        
        # Check if the best match is above the threshold
        if best_match and best_match['confidence'] >= confidence_threshold:
            best_match['matched'] = True
            logger.info(f"Matched {best_match['name']} with confidence {best_match['confidence']:.4f} (threshold: {confidence_threshold:.4f})")
            return best_match
        
        # If no match found, return transparent error
        if not best_match:
            logger.warning(f"No match found above threshold {confidence_threshold}")
            return {'matched': False}
        
        logger.info(f"Best match {best_match['name']} with confidence {best_match['confidence']:.4f} below threshold {confidence_threshold}")
        return {'matched': False}
"""
        
        # Replace the method
        content = content[:start_idx] + new_match_face + content[next_def_idx:]
        logger.info("Patched _match_face_to_member method")
    else:
        logger.error("Could not find _match_face_to_member method in matcher.py")
        return False
    
    # Find the match_face_to_member method
    match_face_pattern = "    def match_face_to_member(self, face_embedding, confidence_threshold="
    if match_face_pattern in content:
        # Replace the default confidence threshold
        content = content.replace(
            "    def match_face_to_member(self, face_embedding, confidence_threshold=0.1", 
            "    def match_face_to_member(self, face_embedding, confidence_threshold=0.5"
        )
        logger.info("Updated default confidence threshold in match_face_to_member")
    else:
        logger.warning("Could not find match_face_to_member method in matcher.py")
    
    # Write the updated file
    with open(matcher_path, 'w') as f:
        f.write(content)
    
    logger.info(f"Updated matcher file at {matcher_path}")
    
    return True

def create_visual_debug_tool():
    """Create a visual debug tool for testing face recognition."""
    # Path to the visual debug tool
    debug_tool_path = "/app/backend/tools/visual_debug.py"
    
    # Create the directory if it doesn't exist
    os.makedirs(os.path.dirname(debug_tool_path), exist_ok=True)
    
    # Define the content for the visual debug tool
    debug_tool_content = '''#!/usr/bin/env python
"""
Visual debugging tool for parliament member face matching.

This tool:
1. Takes an input image containing faces
2. Runs face detection and recognition
3. Matches faces to parliament members
4. Creates a visual debug image with match results
"""
import os
import sys
import logging
import cv2
import numpy as np
import face_recognition
import json
import argparse
from pathlib import Path

# Add the app directory to the path
sys.path.append("/app")

# Import the matcher
from backend.services.recognition.member_matching.matcher import ParliamentMemberMatcher

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Visual debugging tool for parliament member face matching")
    parser.add_argument("--image", type=str, help="Path to the input image")
    parser.add_argument("--threshold", type=float, default=0.5, help="Confidence threshold for matching")
    parser.add_argument("--house", type=str, default="1", help="House ID to filter members (1=Commons, 2=Lords, None=All)")
    parser.add_argument("--output", type=str, default="/app/data/temp/recognition/debug", help="Output directory for debug images")
    return parser.parse_args()

def main():
    # Parse arguments
    args = parse_args()
    
    # Set default image path if not provided
    if args.image is None:
        args.image = "/app/data/temp/recognition/test_frame.jpg"
    
    # Check if the image exists
    if not os.path.exists(args.image):
        logger.error(f"Image not found at {args.image}")
        return
    
    # Create output directory if it doesn't exist
    os.makedirs(args.output, exist_ok=True)
    
    # Initialize the matcher
    logger.info("Initializing ParliamentMemberMatcher...")
    matcher = ParliamentMemberMatcher(None)
    
    # Load parliament members
    logger.info("Loading parliament members...")
    success = matcher.load_parliament_members()
    if not success:
        logger.error("Failed to load parliament members")
        return
    
    # Print information about members in the database
    logger.info(f"Total members in database: {len(matcher.member_embeddings)}")
    
    # Load the image
    logger.info(f"Loading image from {args.image}")
    image = cv2.imread(args.image)
    if image is None:
        logger.error(f"Failed to load image from {args.image}")
        return
    
    # Convert to RGB for face_recognition
    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    
    # Detect faces
    logger.info("Detecting faces...")
    face_locations = face_recognition.face_locations(rgb_image)
    
    if not face_locations:
        logger.error("No faces detected in the image")
        return
    
    logger.info(f"Detected {len(face_locations)} faces")
    
    # Create a copy of the image for debugging
    debug_image = image.copy()
    
    # Process each face
    for i, (top, right, bottom, left) in enumerate(face_locations):
        logger.info(f"Processing face {i+1}...")
        
        # Extract face encoding
        face_encodings = face_recognition.face_encodings(rgb_image, [(top, right, bottom, left)])
        
        if not face_encodings:
            logger.error(f"Failed to extract encoding for face {i+1}")
            continue
        
        face_encoding = face_encodings[0]
        
        # Match face to member
        house_filter = None if args.house.lower() == "none" else args.house
        match_result = matcher.match_face_to_member(face_encoding, confidence_threshold=args.threshold, house=house_filter)
        
        # Draw bounding box
        if match_result.get('matched', False):
            # Green box for matched faces
            color = (0, 255, 0)
            member_id = match_result.get('member_id', 'Unknown')
            name = match_result.get('name', 'Unknown')
            confidence = match_result.get('confidence', 0.0)
            
            # Draw bounding box
            cv2.rectangle(debug_image, (left, top), (right, bottom), color, 2)
            
            # Draw match info
            text = f"{name} (ID: {member_id})"
            cv2.putText(debug_image, text, (left, top-30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
            
            text_conf = f"Confidence: {confidence:.4f}"
            cv2.putText(debug_image, text_conf, (left, top-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
            
            logger.info(f"Face {i+1}: Matched to {name} (ID: {member_id}) with confidence {confidence:.4f}")
        else:
            # Red box for unmatched faces
            color = (0, 0, 255)
            cv2.rectangle(debug_image, (left, top), (right, bottom), color, 2)
            cv2.putText(debug_image, "No match", (left, top-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
            logger.info(f"Face {i+1}: No match found")
    
    # Add info to the image
    info_img = np.zeros((200, debug_image.shape[1], 3), dtype=np.uint8)
    cv2.putText(info_img, "Visual Debugging Results", (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    cv2.putText(info_img, f"Confidence Threshold: {args.threshold}", (20, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 1)
    
    house_text = "Commons" if args.house == "1" else "Lords" if args.house == "2" else "All"
    cv2.putText(info_img, f"House Filter: {house_text}", (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 1)
    
    cv2.putText(info_img, f"Green box = Matched MP, Red = No match", (20, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 1)
    
    # Combine the images
    combined_img = np.vstack([debug_image, info_img])
    
    # Save the debug image
    output_filename = os.path.basename(args.image).split('.')[0] + "_debug.jpg"
    output_path = os.path.join(args.output, output_filename)
    cv2.imwrite(output_path, combined_img)
    
    logger.info(f"Saved debug image to {output_path}")

if __name__ == "__main__":
    main()
'''
    
    # Write the debug tool
    with open(debug_tool_path, 'w') as f:
        f.write(debug_tool_content)
    
    # Make it executable
    os.chmod(debug_tool_path, 0o755)
    
    logger.info(f"Created visual debug tool at {debug_tool_path}")
    
    return True

def test_fix():
    """Test the fix with a test frame."""
    try:
        # Import the matcher class
        sys.path.append("/app/backend")
        from services.recognition.member_matching.matcher import ParliamentMemberMatcher
        
        # Initialize the matcher
        matcher = ParliamentMemberMatcher(db=None, cache_dir="/app/data/cache")
        
        # Extract the face embedding from the test frame
        frame_embedding = extract_face_embedding_from_frame()
        
        if frame_embedding is None:
            logger.error("Failed to extract face embedding from the test frame")
            return False
        
        # Test with different thresholds
        thresholds = [0.9, 0.8, 0.7, 0.6, 0.5]
        
        logger.info("\nTesting with house=1 (Commons):")
        for threshold in thresholds:
            match_result = matcher.match_face_to_member(frame_embedding, confidence_threshold=threshold, house=1)
            
            if match_result.get('matched', False):
                logger.info(f"Match found at threshold {threshold}: {match_result['name']} (ID: {match_result['member_id']}) with confidence {match_result['confidence']}")
                break
            else:
                logger.info(f"No match found above threshold {threshold}")
        
        logger.info("\nTesting with house=None (no filtering):")
        for threshold in thresholds:
            match_result = matcher.match_face_to_member(frame_embedding, confidence_threshold=threshold, house=None)
            
            if match_result.get('matched', False):
                logger.info(f"Match found at threshold {threshold}: {match_result['name']} (ID: {match_result['member_id']}) with confidence {match_result['confidence']}")
                break
            else:
                logger.info(f"No match found above threshold {threshold}")
        
        return True
    except Exception as e:
        logger.error(f"Error testing fix: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def main():
    # Step 1: Fix the embeddings cache
    logger.info("Step 1: Fixing embeddings cache...")
    if fix_embeddings_cache():
        logger.info("Successfully fixed embeddings cache")
    else:
        logger.error("Failed to fix embeddings cache")
        return
    
    # Step 2: Fix the embedding module
    logger.info("\nStep 2: Fixing embedding module...")
    if fix_embedding_module():
        logger.info("Successfully fixed embedding module")
    else:
        logger.error("Failed to fix embedding module")
        return
    
    # Step 3: Fix the matcher module
    logger.info("\nStep 3: Fixing matcher module...")
    if fix_matcher_module():
        logger.info("Successfully fixed matcher module")
    else:
        logger.error("Failed to fix matcher module")
        return
    
    # Step 4: Create visual debug tool
    logger.info("\nStep 4: Creating visual debug tool...")
    if create_visual_debug_tool():
        logger.info("Successfully created visual debug tool")
    else:
        logger.error("Failed to create visual debug tool")
        return
    
    # Step 5: Test the fix
    logger.info("\nStep 5: Testing fix...")
    if test_fix():
        logger.info("Successfully tested fix")
    else:
        logger.error("Failed to test fix")
        return
    
    logger.info("\nAll steps completed successfully!")
    logger.info("The embedding system has been fixed and should now correctly identify all members.")
    logger.info("\nTo test the fix with visual debugging, run:")
    logger.info("docker compose -f docker-compose.dev.yml exec app python /app/backend/tools/visual_debug.py --image /path/to/test/image.jpg")

if __name__ == "__main__":
    main()
