#!/usr/bin/env python3
"""
Speaker Identification for Parliament TV Videos

This script identifies speakers in Parliament TV videos using facial recognition
and a database of known MPs. It can:
1. Process existing Parliament TV videos to identify speakers
2. Generate a database of known MP faces from official Parliament photos
3. Tag videos with speaker information for better searchability

Usage:
    python speaker_identification.py <video_file> [--output OUTPUT_FILE] [--update-db]

Example:
    python speaker_identification.py /app/data/temp/parliament_stream_20250501_123045.mp4 --output /app/data/media/identified_video.mp4
"""

import os
import sys
import json
import time
import argparse
import logging
import cv2
import numpy as np
import face_recognition
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("speaker_identification")

# Constants
MP_PHOTOS_DIR = Path("/app/data/mp_photos")
MP_ENCODINGS_FILE = Path("/app/data/mp_encodings.json")
FRAME_SAMPLE_RATE = 5  # Process every Nth frame
MIN_FACE_SIZE = (60, 60)  # Minimum face size to detect
RECOGNITION_THRESHOLD = 0.6  # Lower is more strict matching

class SpeakerIdentifier:
    """Class to handle speaker identification in videos."""
    
    def __init__(self, mp_encodings_file: Path = MP_ENCODINGS_FILE):
        """Initialize the speaker identifier."""
        self.mp_encodings_file = mp_encodings_file
        self.known_face_encodings = []
        self.known_face_names = []
        self.known_face_metadata = []
        self.load_mp_database()
    
    def load_mp_database(self) -> bool:
        """Load the MP face encodings database."""
        if not self.mp_encodings_file.exists():
            logger.warning(f"MP encodings file not found: {self.mp_encodings_file}")
            return False
        
        try:
            with open(self.mp_encodings_file, 'r') as f:
                data = json.load(f)
                
            self.known_face_encodings = [np.array(enc) for enc in data['encodings']]
            self.known_face_names = data['names']
            self.known_face_metadata = data.get('metadata', [{}] * len(self.known_face_names))
            
            logger.info(f"Loaded {len(self.known_face_encodings)} MP face encodings")
            return True
            
        except Exception as e:
            logger.error(f"Error loading MP database: {e}")
            return False
    
    def update_mp_database(self) -> bool:
        """Update the MP face encodings database from official photos."""
        logger.info("Updating MP database from official photos...")
        
        # Create the MP photos directory if it doesn't exist
        MP_PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
        
        # Download MP data from Parliament API
        try:
            # This is a placeholder - in a real implementation, we would use the actual Parliament API
            # For now, we'll just use a sample list of MPs
            mp_data = self._get_mp_data()
            
            # Process each MP
            new_encodings = []
            new_names = []
            new_metadata = []
            
            for mp in mp_data:
                mp_id = mp['id']
                mp_name = mp['name']
                photo_url = mp.get('photo_url')
                
                if not photo_url:
                    logger.warning(f"No photo URL for MP {mp_name}, skipping")
                    continue
                
                # Download the photo if needed
                photo_path = MP_PHOTOS_DIR / f"{mp_id}.jpg"
                if not photo_path.exists():
                    self._download_mp_photo(photo_url, photo_path)
                
                # Generate face encoding
                if photo_path.exists():
                    encoding = self._generate_face_encoding(photo_path)
                    if encoding is not None:
                        new_encodings.append(encoding.tolist())
                        new_names.append(mp_name)
                        new_metadata.append({
                            'id': mp_id,
                            'name': mp_name,
                            'party': mp.get('party', ''),
                            'constituency': mp.get('constituency', '')
                        })
                        logger.info(f"Added encoding for MP: {mp_name}")
                    else:
                        logger.warning(f"Could not generate encoding for MP: {mp_name}")
            
            # Save the updated database
            with open(self.mp_encodings_file, 'w') as f:
                json.dump({
                    'encodings': new_encodings,
                    'names': new_names,
                    'metadata': new_metadata,
                    'updated_at': datetime.now().isoformat()
                }, f, indent=2)
            
            # Reload the database
            return self.load_mp_database()
            
        except Exception as e:
            logger.error(f"Error updating MP database: {e}")
            return False
    
    def _get_mp_data(self) -> List[Dict]:
        """Get MP data from Parliament API or use sample data for testing."""
        # In a real implementation, we would use the Parliament API
        # For now, return sample data
        return [
            {
                'id': '1',
                'name': 'Keir Starmer',
                'party': 'Labour',
                'constituency': 'Holborn and St Pancras',
                'photo_url': 'https://members-api.parliament.uk/api/Members/4514/Portrait?cropType=ThreeFour'
            },
            {
                'id': '2',
                'name': 'Rishi Sunak',
                'party': 'Conservative',
                'constituency': 'Richmond (Yorks)',
                'photo_url': 'https://members-api.parliament.uk/api/Members/4463/Portrait?cropType=ThreeFour'
            }
        ]
    
    def _download_mp_photo(self, url: str, output_path: Path) -> bool:
        """Download an MP photo from a URL."""
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            logger.info(f"Downloaded photo to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error downloading photo from {url}: {e}")
            return False
    
    def _generate_face_encoding(self, image_path: Path) -> Optional[np.ndarray]:
        """Generate a face encoding from an image file."""
        try:
            # Load the image
            image = face_recognition.load_image_file(str(image_path))
            
            # Find all faces in the image
            face_locations = face_recognition.face_locations(image)
            
            # If no faces found, return None
            if not face_locations:
                logger.warning(f"No faces found in {image_path}")
                return None
            
            # Use the first face found (assuming it's the MP)
            face_encoding = face_recognition.face_encodings(image, face_locations)[0]
            return face_encoding
            
        except Exception as e:
            logger.error(f"Error generating face encoding for {image_path}: {e}")
            return None
    
    def identify_speaker(self, frame: np.ndarray) -> Optional[Dict]:
        """
        Identify the speaker in a video frame.
        
        Args:
            frame: The video frame to analyze
            
        Returns:
            Dict with speaker information or None if no speaker identified
        """
        # Resize frame for faster processing
        small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
        
        # Convert from BGR to RGB (face_recognition uses RGB)
        rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
        
        # Find all face locations and encodings
        face_locations = face_recognition.face_locations(rgb_small_frame)
        
        # If no faces found, return None
        if not face_locations:
            return None
        
        # Find the largest face (assuming it's the speaker)
        largest_face_idx = self._find_largest_face(face_locations)
        largest_face = face_locations[largest_face_idx]
        
        # Get the encoding for the largest face
        face_encodings = face_recognition.face_encodings(rgb_small_frame, [largest_face])
        
        if not face_encodings:
            return None
        
        face_encoding = face_encodings[0]
        
        # Compare with known faces
        if not self.known_face_encodings:
            return {'unknown': True}
        
        # Calculate face distances
        face_distances = face_recognition.face_distance(self.known_face_encodings, face_encoding)
        
        # Find the best match
        best_match_idx = np.argmin(face_distances)
        best_match_distance = face_distances[best_match_idx]
        
        # Scale back the face location to original size
        top, right, bottom, left = largest_face
        scaled_location = (
            top * 4, right * 4, bottom * 4, left * 4
        )
        
        # If the best match is close enough, return the MP info
        if best_match_distance < RECOGNITION_THRESHOLD:
            mp_name = self.known_face_names[best_match_idx]
            mp_metadata = self.known_face_metadata[best_match_idx]
            
            return {
                'name': mp_name,
                'confidence': 1.0 - best_match_distance,
                'face_location': scaled_location,
                'metadata': mp_metadata
            }
        else:
            # Unknown speaker
            return {
                'name': 'Unknown',
                'confidence': 0.0,
                'face_location': scaled_location,
                'unknown': True
            }
    
    def _find_largest_face(self, face_locations: List[Tuple[int, int, int, int]]) -> int:
        """Find the index of the largest face in the list of face locations."""
        if not face_locations:
            return -1
        
        # Calculate the area of each face
        areas = []
        for top, right, bottom, left in face_locations:
            area = (bottom - top) * (right - left)
            areas.append(area)
        
        # Return the index of the largest face
        return np.argmax(areas)
    
    def process_video(self, video_path: Path, output_path: Optional[Path] = None) -> Dict:
        """
        Process a video to identify speakers.
        
        Args:
            video_path: Path to the input video
            output_path: Path to save the output video (optional)
            
        Returns:
            Dict with speaker identification results
        """
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        # If no output path provided, create one
        if output_path is None:
            output_dir = video_path.parent / "identified"
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / f"identified_{video_path.name}"
        
        # Open the video
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise RuntimeError(f"Could not open video: {video_path}")
        
        # Get video properties
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        logger.info(f"Processing video: {video_path}")
        logger.info(f"Video properties: {width}x{height} @ {fps} fps, {total_frames} frames")
        
        # Create a video writer for the output
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
        
        # Initialize results
        results = {
            'input_file': str(video_path),
            'output_file': str(output_path),
            'speakers': {},
            'timeline': [],
            'frame_count': 0,
            'processed_frames': 0
        }
        
        # Process the video
        frame_idx = 0
        current_speaker = None
        speaker_start_time = 0
        
        try:
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                
                frame_idx += 1
                results['frame_count'] = frame_idx
                
                # Process every Nth frame for efficiency
                if frame_idx % FRAME_SAMPLE_RATE == 0:
                    results['processed_frames'] += 1
                    
                    # Identify the speaker
                    speaker_info = self.identify_speaker(frame)
                    
                    # If a speaker was identified, add a label to the frame
                    if speaker_info:
                        # Draw a rectangle around the face
                        if 'face_location' in speaker_info:
                            top, right, bottom, left = speaker_info['face_location']
                            cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
                        
                        # Add the speaker name and confidence
                        name = speaker_info.get('name', 'Unknown')
                        confidence = speaker_info.get('confidence', 0.0)
                        label = f"{name} ({confidence:.2f})"
                        
                        # Draw the label
                        if 'face_location' in speaker_info:
                            top, right, bottom, left = speaker_info['face_location']
                            cv2.putText(frame, label, (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                        
                        # Update speaker timeline
                        current_time = frame_idx / fps
                        
                        # If the speaker changed, add the previous segment to the timeline
                        if current_speaker is None or current_speaker != name:
                            if current_speaker is not None:
                                results['timeline'].append({
                                    'speaker': current_speaker,
                                    'start_time': speaker_start_time,
                                    'end_time': current_time,
                                    'duration': current_time - speaker_start_time
                                })
                            
                            # Start a new segment
                            current_speaker = name
                            speaker_start_time = current_time
                        
                        # Update speaker statistics
                        if name not in results['speakers']:
                            results['speakers'][name] = {
                                'frames': 0,
                                'total_confidence': 0.0,
                                'metadata': speaker_info.get('metadata', {})
                            }
                        
                        results['speakers'][name]['frames'] += 1
                        results['speakers'][name]['total_confidence'] += confidence
                
                # Write the frame to the output video
                out.write(frame)
                
                # Log progress
                if frame_idx % 100 == 0:
                    progress = (frame_idx / total_frames) * 100
                    logger.info(f"Processing progress: {progress:.1f}% ({frame_idx}/{total_frames})")
        
        except Exception as e:
            logger.error(f"Error processing video: {e}")
            raise
        
        finally:
            # Release resources
            cap.release()
            out.release()
            
            # Add the final speaker segment to the timeline
            if current_speaker is not None:
                current_time = frame_idx / fps
                results['timeline'].append({
                    'speaker': current_speaker,
                    'start_time': speaker_start_time,
                    'end_time': current_time,
                    'duration': current_time - speaker_start_time
                })
            
            # Calculate average confidence for each speaker
            for name, info in results['speakers'].items():
                if info['frames'] > 0:
                    info['average_confidence'] = info['total_confidence'] / info['frames']
                    # Remove the total confidence from the results
                    del info['total_confidence']
            
            # Sort speakers by number of frames (most prominent first)
            results['primary_speaker'] = max(
                results['speakers'].items(),
                key=lambda x: x[1]['frames'],
                default=(None, {})
            )[0]
            
            # Add processing metadata
            results['processing_info'] = {
                'processed_at': datetime.now().isoformat(),
                'frame_sample_rate': FRAME_SAMPLE_RATE,
                'recognition_threshold': RECOGNITION_THRESHOLD,
                'total_duration': frame_idx / fps
            }
            
            logger.info(f"Video processing completed: {output_path}")
            logger.info(f"Processed {results['processed_frames']} frames, identified {len(results['speakers'])} speakers")
            
            # Save the results to a JSON file
            results_file = output_path.with_suffix('.json')
            with open(results_file, 'w') as f:
                json.dump(results, f, indent=2)
            
            logger.info(f"Results saved to: {results_file}")
            
            return results

def check_dependencies():
    """Check if required dependencies are installed."""
    try:
        import cv2
        import numpy as np
        import face_recognition
        import requests
        return True
    except ImportError as e:
        logger.error(f"Missing dependency: {e}")
        return False

def install_dependencies():
    """Install required dependencies."""
    logger.info("Installing dependencies...")
    try:
        # Use apt-get in Docker environment to install OpenCV dependencies
        if os.path.exists('/.dockerenv'):
            subprocess.run(['apt-get', 'update'], check=True)
            subprocess.run(['apt-get', 'install', '-y', 'python3-opencv', 'libopencv-dev', 'cmake', 'build-essential'], check=True)
        
        # Use pip to install Python packages
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'opencv-python', 'numpy', 'face_recognition', 'requests'], check=True)
        
        logger.info("Dependencies installed successfully.")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to install dependencies: {e}")
        return False

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description='Speaker Identification for Parliament TV Videos')
    parser.add_argument('video_file', help='Path to the video file to process')
    parser.add_argument('--output', '-o', help='Path to save the output video')
    parser.add_argument('--update-db', action='store_true', help='Update the MP database before processing')
    parser.add_argument('--threshold', '-t', type=float, default=RECOGNITION_THRESHOLD, help='Recognition threshold (lower is stricter)')
    args = parser.parse_args()
    
    try:
        # Check dependencies
        if not check_dependencies():
            if not install_dependencies():
                logger.error("Required dependencies could not be installed.")
                return 1
        
        # Initialize the speaker identifier
        identifier = SpeakerIdentifier()
        
        # Update the MP database if requested
        if args.update_db:
            if not identifier.update_mp_database():
                logger.warning("Failed to update MP database. Continuing with existing database.")
        
        # Set the recognition threshold
        global RECOGNITION_THRESHOLD
        RECOGNITION_THRESHOLD = args.threshold
        
        # Process the video
        video_path = Path(args.video_file)
        output_path = Path(args.output) if args.output else None
        
        results = identifier.process_video(video_path, output_path)
        
        # Print a summary of the results
        print("\nSpeaker Identification Results:")
        print(f"Primary speaker: {results.get('primary_speaker', 'Unknown')}")
        print("\nSpeakers detected:")
        for name, info in results.get('speakers', {}).items():
            print(f"  - {name}: {info.get('frames', 0)} frames, {info.get('average_confidence', 0.0):.2f} confidence")
        
        print(f"\nResults saved to: {output_path.with_suffix('.json')}")
        print(f"Processed video saved to: {output_path}")
        
        return 0
    
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
