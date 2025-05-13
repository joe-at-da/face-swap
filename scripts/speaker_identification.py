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
FRAME_SAMPLE_RATE = 3  # Process every Nth frame (more frequent sampling)
MIN_FACE_SIZE = (40, 40)  # Smaller minimum face size to detect more faces
RECOGNITION_THRESHOLD = 0.7  # Higher threshold to be more lenient in matching

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
        # Try multiple scales to improve face detection
        face_locations = []
        
        # Try with different scales
        scales = [0.5, 0.25, 0.75]  # Try different scales for better detection
        
        for scale in scales:
            # Resize frame for processing
            small_frame = cv2.resize(frame, (0, 0), fx=scale, fy=scale)
            
            # Convert from BGR to RGB (face_recognition uses RGB)
            rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
            
            # Find all face locations using HOG model (faster) first
            current_locations = face_recognition.face_locations(rgb_small_frame, model="hog")
            
            # If no faces found with HOG, try CNN model (more accurate but slower)
            if not current_locations and scale == 0.25:  # Only try CNN at medium scale for performance
                try:
                    current_locations = face_recognition.face_locations(rgb_small_frame, model="cnn")
                    print(f"CNN model detected {len(current_locations)} faces at scale {scale}")
                except Exception as e:
                    print(f"CNN model error: {e}")
            
            # Adjust face locations to account for scaling
            scaled_locations = []
            for top, right, bottom, left in current_locations:
                scaled_top = int(top / scale)
                scaled_right = int(right / scale)
                scaled_bottom = int(bottom / scale)
                scaled_left = int(left / scale)
                scaled_locations.append((scaled_top, scaled_right, scaled_bottom, scaled_left))
            
            if scaled_locations:
                face_locations = scaled_locations
                print(f"Found {len(face_locations)} faces at scale {scale}")
                break  # Stop if we found faces
        
        # If no faces found after trying all scales, return None
        if not face_locations:
            print("No faces detected in frame after trying multiple scales")
            return None
        
        # Find the largest face (assuming it's the speaker)
        largest_face_idx = self._find_largest_face(face_locations)
        largest_face = face_locations[largest_face_idx]
        
        # Convert the frame to RGB for face_recognition
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Get the encoding for the largest face - use the original frame for better quality
        try:
            # Try with more liberal parameters for better recognition
            face_encodings = face_recognition.face_encodings(rgb_frame, [largest_face], num_jitters=3, model="large")
            print(f"Generated face encoding with advanced parameters")
        except Exception as e:
            print(f"Error with advanced encoding parameters: {e}")
            # Fall back to default parameters
            face_encodings = face_recognition.face_encodings(rgb_frame, [largest_face])
            print(f"Generated face encoding with default parameters")
        
        if not face_encodings:
            print("Failed to generate face encoding")
            return None
        
        face_encoding = face_encodings[0]
        print(f"Successfully generated face encoding")
        
        # Debug info
        print(f"Face location: {largest_face}")
        face_size = (largest_face[2] - largest_face[0]) * (largest_face[1] - largest_face[3])
        print(f"Face size: {face_size} pixels")
        
        # Compare with known faces
        if not self.known_face_encodings:
            print("No known face encodings available for comparison")
            return {'unknown': True, 'reason': 'No known faces in database'}
        
        print(f"Comparing against {len(self.known_face_encodings)} known faces")
        
        # Calculate face distances
        face_distances = face_recognition.face_distance(self.known_face_encodings, face_encoding)
        
        # Find the top 3 matches for better debugging
        top_indices = np.argsort(face_distances)[:3]
        top_distances = face_distances[top_indices]
        top_names = [self.known_face_names[i] for i in top_indices]
        
        print(f"Top 3 matches:")
        for i, (name, distance) in enumerate(zip(top_names, top_distances)):
            confidence = 1.0 - distance
            print(f"  {i+1}. {name}: distance={distance:.4f}, confidence={confidence:.2%}")
        
        # Find the best match
        best_match_idx = top_indices[0]
        best_match_distance = top_distances[0]
        
        # Get the face location
        top, right, bottom, left = largest_face
        
        # If the best match is close enough, return the MP info
        if best_match_distance < RECOGNITION_THRESHOLD:
            mp_name = self.known_face_names[best_match_idx]
            mp_metadata = self.known_face_metadata[best_match_idx]
            confidence = 1.0 - best_match_distance
            
            print(f"Match found: {mp_name} with {confidence:.2%} confidence")
            
            return {
                'name': mp_name,
                'confidence': confidence,
                'face_location': (top, right, bottom, left),
                'metadata': mp_metadata,
                'bbox': [left, top, right, bottom]  # Format expected by frontend
            }
        else:
            # Unknown speaker but with debugging info
            print(f"No match found: best match {top_names[0]} with distance {best_match_distance:.4f} > threshold {RECOGNITION_THRESHOLD}")
            return {
                'name': 'Unknown',
                'confidence': 0.0,
                'face_location': (top, right, bottom, left),
                'bbox': [left, top, right, bottom],  # Format expected by frontend
                'unknown': True,
                'best_match': top_names[0],
                'best_match_distance': float(best_match_distance)
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
    """Main function to run the speaker identification."""
    parser = argparse.ArgumentParser(description="Speaker Identification for Parliament TV Videos")
    parser.add_argument("video_path", nargs="?", help="Path to the video file to process")
    parser.add_argument("--output", "-o", help="Path to save the output video")
    parser.add_argument("--update-db", action="store_true", help="Update the MP database")
    parser.add_argument("--threshold", "-t", type=float, default=RECOGNITION_THRESHOLD, 
                        help=f"Recognition threshold (default: {RECOGNITION_THRESHOLD})")
    parser.add_argument("--debug", "-d", action="store_true", help="Enable debug mode with extra logging")
    args = parser.parse_args()
    
    try:
        # Check dependencies
        if not check_dependencies():
            if not install_dependencies():
                logger.error("Required dependencies could not be installed.")
                return 1
        
        # Set up logging based on debug flag
        if args.debug:
            logging.basicConfig(level=logging.DEBUG)
            print("Debug mode enabled - verbose logging will be shown")
        
        # Create the speaker identifier
        identifier = SpeakerIdentifier()
        
        # Update the database if requested
        if args.update_db:
            result = identifier.update_mp_database()
            print(f"MP database update result: {result}")
            return
        
        # Set the recognition threshold
        if args.threshold is not None:
            global RECOGNITION_THRESHOLD
            RECOGNITION_THRESHOLD = args.threshold
            print(f"Setting recognition threshold to: {RECOGNITION_THRESHOLD}")
        
        # Process the video
        if args.video_path:
            video_path = Path(args.video_path)
            output_path = Path(args.output) if args.output else None
            
            print(f"Processing video: {video_path}")
            print(f"Using recognition threshold: {RECOGNITION_THRESHOLD}")
            
            # Check if the file exists
            if not video_path.exists():
                print(f"ERROR: Video file not found: {video_path}")
                return
                
            # Check if the file is a video
            try:
                cap = cv2.VideoCapture(str(video_path))
                if not cap.isOpened():
                    print(f"ERROR: Could not open video file: {video_path}")
                    return
                    
                # Get video properties for debugging
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                fps = cap.get(cv2.CAP_PROP_FPS)
                frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                
                print(f"Video properties: {width}x{height} @ {fps} fps, {frame_count} frames")
                cap.release()
            except Exception as e:
                print(f"ERROR checking video file: {e}")
            
            result = identifier.process_video(video_path, output_path)
            
            # Save the results to a JSON file
            results_file = video_path.with_suffix('.json')
            with open(results_file, 'w') as f:
                json.dump(result, f, indent=2)
            
            print(f"Results saved to: {results_file}")
            print(f"Processed video saved to: {result['output_file']}")
            print(f"Total frames: {result['frame_count']}")
            print(f"Processed frames: {result['processed_frames']}")
            print(f"Detected speakers: {len(result['speakers'])}")
            
            # Print detailed speaker information
            if 'speakers' in result and result['speakers']:
                print("\nDetected speakers:")
                for name, info in result['speakers'].items():
                    print(f"  - {name}: {info['frames']} appearances, confidence: {info['average_confidence']:.2f}")
            else:
                print("\nNo speakers detected in the video")
        else:
            parser.print_help()
    
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
