# Facial Recognition System Documentation

This document provides a comprehensive overview of the facial recognition system implemented in the Parliament Video Clip Manager.

## Overview

The facial recognition system is designed to identify Members of Parliament (MPs) in video footage from Parliament TV. It uses computer vision and machine learning techniques to detect faces, extract facial features, and match them against a database of known MP faces.

## System Components

### 1. Face Detection and Recognition

The system uses the following libraries for face detection and recognition:
- **OpenCV**: For video processing and basic face detection
- **face_recognition**: A Python library built on dlib for facial recognition
- **NumPy**: For numerical operations on face encodings

### 2. MP Database

The system maintains a database of MP face encodings in:
- **`mp_encodings.json`**: Contains face encodings for known MPs

### 3. Key Scripts

The facial recognition functionality is implemented through several Python scripts:

#### a. `identify_speakers.py`
- **Purpose**: Identifies speakers in videos using facial recognition
- **Functionality**:
  - Processes video frames at a specified sample rate
  - Detects faces in each frame
  - Compares detected faces with known MP encodings
  - Generates a report of identified speakers with timestamps

#### b. `detect_unique_faces.py`
- **Purpose**: Detects unique faces in videos without identifying them
- **Functionality**:
  - Processes video frames at a specified sample rate
  - Detects faces in each frame
  - Clusters similar faces to identify unique individuals
  - Saves face images and data for later identification

#### c. `process_video_faces.py`
- **Purpose**: Processes videos to detect faces and create face profiles
- **Functionality**:
  - Detects unique faces in videos
  - Creates face profiles in the database
  - Links face samples to profiles
  - Updates the MP encodings database

#### d. `generate_mp_encodings.py`
- **Purpose**: Generates sample MP profiles with realistic face encodings
- **Functionality**:
  - Creates sample MP data with names and parliament IDs
  - Generates realistic face encodings
  - Saves the data to `mp_encodings.json`

#### e. `setup_facial_recognition.py`
- **Purpose**: Sets up the facial recognition system
- **Functionality**:
  - Creates necessary directories
  - Downloads sample MP photos (if needed)
  - Initializes the facial recognition system

### 4. Backend Services

The facial recognition system is integrated with the backend through:

#### a. `FacialRecognitionService` (`backend/services/recognition/facial_recognition.py`)
- **Purpose**: Provides facial recognition capabilities as a service
- **Key Methods**:
  - `detect_faces_in_video()`: Detects faces in a video file
  - `identify_speakers()`: Identifies speakers in a video file
  - `load_mp_database()`: Loads the MP database with face encodings
  - `update_mp_database()`: Updates the MP database with the latest data

#### b. `FaceProfileService` (`backend/services/recognition/face_profile_service.py`)
- **Purpose**: Manages face profiles and samples
- **Key Methods**:
  - `create_face_profile()`: Creates a new face profile
  - `add_face_sample()`: Adds a face sample to a profile
  - `link_face_profile_to_voice_profile()`: Links face and voice profiles

## Data Flow

1. **Video Capture**:
   - Video is captured from Parliament TV or uploaded by users
   - Video is saved to the file system

2. **Face Detection**:
   - The system processes the video frame by frame
   - Faces are detected in each frame using OpenCV and face_recognition

3. **Face Recognition**:
   - Detected faces are compared with known MP encodings
   - The system calculates a confidence score for each match
   - Matches above a threshold are considered positive identifications

4. **Result Storage**:
   - Recognition results are saved to the database
   - Results include identified speakers, timestamps, and confidence scores

5. **UI Display**:
   - Recognition results are displayed in the frontend UI
   - Users can view identified speakers and their timestamps

## Technical Details

### Face Encoding Process

1. **Face Detection**:
   - The system uses HOG (Histogram of Oriented Gradients) for face detection
   - Detected faces are aligned using facial landmarks

2. **Feature Extraction**:
   - The system extracts 128-dimensional face encodings using a pre-trained neural network
   - These encodings represent the unique facial features of each person

3. **Face Matching**:
   - Face encodings are compared using Euclidean distance
   - A distance below a threshold (typically 0.6) indicates a match

### Performance Considerations

- **Sample Rate**: The system processes every Nth frame (default: 5) to balance accuracy and performance
- **Face Size**: Small faces (below 40x40 pixels) are ignored to reduce false positives
- **Confidence Threshold**: Only matches with confidence above a threshold are reported

### NumPy Compatibility

The facial recognition system requires NumPy 1.24.3 for compatibility with OpenCV. The system includes a fix script (`backend/fix_numpy.sh`) to ensure the correct NumPy version is installed.

## Setup and Configuration

### Prerequisites

- Python 3.11+
- OpenCV
- face_recognition
- NumPy 1.24.3 (specific version required)

### Installation

1. **Docker Setup**:
   - Use the provided Docker setup to ensure all dependencies are correctly installed
   - Run the NumPy fix script to ensure compatibility: `docker exec the-mp-app-1 bash /app/backend/fix_numpy.sh`

2. **Manual Setup**:
   - Install required Python packages: `pip install -r requirements.txt`
   - Install the correct NumPy version: `pip install numpy==1.24.3`
   - Install OpenCV: `pip install opencv-python-headless==4.8.1.78`

### Configuration

The facial recognition system can be configured through:

1. **Environment Variables**:
   - `DATA_DIR`: Path to the data directory (default: `/app/data`)

2. **Constants in Scripts**:
   - `FACE_SIMILARITY_THRESHOLD`: Threshold for considering faces as the same person (default: 0.6)
   - `DEFAULT_SAMPLE_RATE`: Process every Nth frame (default: 5)
   - `MIN_FACE_SIZE`: Minimum face size in pixels (default: 40)

## Usage Examples

### Identifying Speakers in a Video

```python
from backend.services.recognition.facial_recognition import FacialRecognitionService

# Initialize the service
facial_recognition_service = FacialRecognitionService()

# Load the MP database
facial_recognition_service.load_mp_database()

# Identify speakers in a video
result = facial_recognition_service.identify_speakers(
    video_path="/app/data/temp/parliament_video.mp4",
    output_file="/app/data/temp/output_video.mp4"
)

# Process the results
if result["success"]:
    speakers = result["results"]["speakers"]
    for speaker in speakers:
        print(f"Speaker: {speaker['name']}")
        print(f"Confidence: {speaker['confidence']:.2f}")
        print(f"Duration: {speaker['duration']:.2f} seconds")
        print(f"Timestamps: {speaker['start_time']} - {speaker['end_time']}")
        print("---")
```

### Creating a Face Profile

```python
from backend.db.session import SessionLocal
from backend.services.recognition.face_profile_service import FaceProfileService

# Initialize the service
face_profile_service = FaceProfileService()

# Create a database session
db = SessionLocal()

try:
    # Create a face profile
    profile = face_profile_service.create_face_profile(
        db=db,
        name="John Smith",
        role="MP",
        party="Conservative"
    )
    
    # Add a face sample
    face_profile_service.add_face_sample(
        db=db,
        face_profile_id=profile.id,
        image_path="/app/data/mp_photos/john_smith.jpg",
        encoding=[0.1, 0.2, ...],  # 128-dimensional face encoding
        confidence_score=1.0
    )
    
    db.commit()
    print(f"Created face profile with ID: {profile.id}")
finally:
    db.close()
```

## Troubleshooting

### Common Issues

1. **NumPy Compatibility Errors**:
   - Error: `ImportError: numpy.core.multiarray failed to import`
   - Solution: Run the NumPy fix script: `bash /app/backend/fix_numpy.sh`

2. **No Faces Detected**:
   - Check video quality and lighting
   - Ensure faces are large enough (at least 40x40 pixels)
   - Try reducing the sample rate to process more frames

3. **Poor Recognition Accuracy**:
   - Ensure MP encodings are of good quality
   - Check lighting conditions in the video
   - Adjust the face similarity threshold

4. **Missing MP Encodings File**:
   - Run the setup script: `python /app/scripts/setup_facial_recognition.py`
   - Generate sample encodings: `python /app/scripts/generate_mp_encodings.py`

### Debugging

For debugging issues with facial recognition:

1. **Enable Verbose Logging**:
   - Set logging level to DEBUG in the relevant scripts

2. **Generate Debug Output**:
   - Set `output_file` parameter when calling `identify_speakers()` to generate a video with face boxes

3. **Check Intermediate Results**:
   - Examine face detection results to ensure faces are being detected correctly
   - Check face encodings to ensure they are being generated correctly

## Future Improvements

1. **Performance Optimization**:
   - Implement GPU acceleration for face detection and recognition
   - Optimize video processing for large files

2. **Accuracy Improvements**:
   - Use multiple face samples per MP for better recognition
   - Implement face tracking to maintain identity across frames

3. **Feature Enhancements**:
   - Add support for recognizing MPs in different poses and lighting conditions
   - Implement age and gender estimation for better filtering

4. **Integration Enhancements**:
   - Integrate with external MP databases for automatic updates
   - Implement real-time recognition for live streams

## Conclusion

The facial recognition system provides a powerful tool for identifying MPs in Parliament TV footage. By following the setup and configuration guidelines in this document, you can ensure optimal performance and accuracy of the system.
