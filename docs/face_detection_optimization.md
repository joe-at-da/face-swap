# Face Detection Performance Optimization

## Current Performance Issues

The current face detection pipeline for Parliament TV videos is taking approximately **2+ hours** to process a one-hour video. This document outlines optimization strategies to significantly reduce processing time while maintaining detection quality.

## Optimization Strategies

### 1. Region of Interest (ROI) Restriction

**Implementation Priority: HIGH**

Parliament TV footage typically features speakers in the center of the frame. By restricting face detection to only the central portion of each frame, we can dramatically reduce processing time.

```python
# Example implementation
def detect_faces_in_roi(frame, roi_scale=0.6):
    """Only detect faces in the central region of the frame"""
    height, width = frame.shape[:2]
    
    # Calculate ROI dimensions (e.g., center 60% of the frame)
    roi_width = int(width * roi_scale)
    roi_height = int(height * roi_scale)
    
    # Calculate ROI coordinates
    x_start = (width - roi_width) // 2
    y_start = (height - roi_height) // 2
    
    # Extract ROI
    roi = frame[y_start:y_start+roi_height, x_start:x_start+roi_width]
    
    # Detect faces in ROI
    face_locations = face_recognition.face_locations(roi, model="hog")
    
    # Adjust face coordinates back to original frame
    adjusted_locations = []
    for top, right, bottom, left in face_locations:
        adjusted_locations.append(
            (top + y_start, right + x_start, bottom + y_start, left + x_start)
        )
    
    return adjusted_locations
```

**Expected Speedup**: 2-3x (processing only ~36% of the original frame area)

### 2. Aggressive Frame Skipping

**Implementation Priority: HIGH**

Currently, the system processes 1 frame per second (or every 30 frames at 30fps). For parliamentary footage where speaker changes are relatively infrequent, we can increase this to process only 1 frame every 3-5 seconds.

```python
# Update in face_profile_service.py
def extract_faces_from_video(self, video_path: str, output_dir: Optional[str] = None, 
                       interval: float = 3.0,  # Increase from 1.0 to 3.0 seconds
                       min_confidence: float = 0.6,
                       prioritize_center: bool = True,
                       select_best_frames: bool = True,
                       min_face_size: int = 200, 
                       min_face_area: int = 40000) -> Dict[str, Any]:
```

**Expected Speedup**: 3-5x (processing 1/3 to 1/5 of the current frames)

### 3. Downscaling Frames

**Implementation Priority: MEDIUM**

HOG-based face detection can run much faster on smaller images with minimal accuracy loss for larger faces.

```python
# Example implementation
def detect_faces_with_downscaling(frame, scale_factor=0.5):
    """Downscale the frame before face detection"""
    height, width = frame.shape[:2]
    
    # Downscale the image
    small_frame = cv2.resize(frame, (0, 0), fx=scale_factor, fy=scale_factor)
    
    # Convert to RGB (face_recognition uses RGB)
    rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
    
    # Find face locations in the small frame
    face_locations = face_recognition.face_locations(rgb_small_frame, model="hog")
    
    # Scale back the locations to the original frame size
    original_locations = []
    for top, right, bottom, left in face_locations:
        original_locations.append(
            (int(top/scale_factor), int(right/scale_factor),
             int(bottom/scale_factor), int(left/scale_factor))
        )
    
    return original_locations
```

**Expected Speedup**: 2-4x (processing 1/4 of the pixels with 0.5x scaling)

### 4. Early Termination

**Implementation Priority: MEDIUM**

For parliamentary videos, we're typically interested in the main speaker. We can modify the code to stop processing after finding a sufficiently large, centered face.

```python
# Example implementation
def find_main_speaker_face(frame, min_face_size=200, center_threshold=0.3):
    """Find only the main speaker face in the frame"""
    height, width = frame.shape[:2]
    frame_center_x = width / 2
    frame_center_y = height / 2
    
    # Convert to RGB
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    # Find all faces
    face_locations = face_recognition.face_locations(rgb_frame, model="hog")
    
    # Find the most centered, sufficiently large face
    best_face = None
    best_score = float('inf')
    
    for face_location in face_locations:
        top, right, bottom, left = face_location
        face_width = right - left
        face_height = bottom - top
        
        # Skip small faces
        if face_width < min_face_size or face_height < min_face_size:
            continue
        
        # Calculate face center
        face_center_x = (left + right) / 2
        face_center_y = (top + bottom) / 2
        
        # Calculate distance from frame center (normalized)
        distance_x = abs(face_center_x - frame_center_x) / (width / 2)
        distance_y = abs(face_center_y - frame_center_y) / (height / 2)
        distance = np.sqrt(distance_x**2 + distance_y**2)
        
        # If we find a face that's centered enough, return it immediately
        if distance < center_threshold:
            return [face_location]
        
        # Otherwise, keep track of the most centered face
        if distance < best_score:
            best_score = distance
            best_face = face_location
    
    # If we found any face, return the most centered one
    return [best_face] if best_face else []
```

**Expected Speedup**: 1.5-2x (by avoiding processing multiple faces in complex frames)

### 5. Reducing HOG Upsampling

**Implementation Priority: HIGH**

The face_recognition library's HOG detector uses upsampling to find smaller faces. Setting this to 0 will significantly speed up detection but may miss smaller faces.

```python
# Example implementation
face_locations = face_recognition.face_locations(
    rgb_frame, 
    model="hog",
    number_of_times_to_upsample=0  # Default is 1, 0 is much faster
)
```

**Expected Speedup**: 2x (by eliminating the upsampling step)

### 6. Scene Change Detection

**Implementation Priority: HIGH**

For parliamentary videos, camera shots typically remain fixed for extended periods. By detecting scene changes (camera switches), we can trigger face detection only when the scene changes significantly.

```python
def detect_scene_change(current_frame, previous_frame, threshold=0.2):
    """Detect if there's been a major scene change"""
    if previous_frame is None:
        return True
        
    # Convert to grayscale and calculate histograms
    gray_current = cv2.cvtColor(current_frame, cv2.COLOR_BGR2GRAY)
    gray_previous = cv2.cvtColor(previous_frame, cv2.COLOR_BGR2GRAY)
    
    # Compare histograms
    hist_current = cv2.calcHist([gray_current], [0], None, [64], [0, 256])
    hist_previous = cv2.calcHist([gray_previous], [0], None, [64], [0, 256])
    
    # Normalize and compare
    cv2.normalize(hist_current, hist_current, 0, 1.0, cv2.NORM_MINMAX)
    cv2.normalize(hist_previous, hist_previous, 0, 1.0, cv2.NORM_MINMAX)
    
    difference = cv2.compareHist(hist_current, hist_previous, cv2.HISTCMP_BHATTACHARYYA)
    
    return difference > threshold
```

**Expected Speedup**: 3-5x (by avoiding redundant processing of similar frames)

### 7. Face Tracking Instead of Re-Detection

**Implementation Priority: HIGH**

Once a face is detected, use lightweight tracking algorithms (like KCF or CSRT trackers in OpenCV) instead of repeatedly running face detection on every frame.

```python
def track_faces_in_video(video_path, detection_interval=150):
    """Use tracking instead of detection for most frames"""
    cap = cv2.VideoCapture(video_path)
    trackers = []
    frame_count = 0
    previous_frame = None
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        # Detect scene change
        scene_changed = detect_scene_change(frame, previous_frame)
        previous_frame = frame.copy()
        
        # On first frame, scene change, or at intervals, do full detection
        if frame_count == 0 or scene_changed or frame_count % detection_interval == 0:
            # Clear existing trackers
            trackers = []
            
            # Do face detection
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            face_locations = face_recognition.face_locations(rgb_frame, model="hog")
            
            # Initialize trackers for each face
            for face_loc in face_locations:
                top, right, bottom, left = face_loc
                tracker = cv2.TrackerKCF_create()
                tracker.init(frame, (left, top, right-left, bottom-top))
                trackers.append({
                    "tracker": tracker,
                    "face_loc": face_loc,
                    "last_detection_frame": frame_count
                })
        else:
            # Update trackers
            for tracker_info in trackers:
                success, box = tracker_info["tracker"].update(frame)
                if success:
                    x, y, w, h = [int(v) for v in box]
                    tracker_info["face_loc"] = (y, x+w, y+h, x)
        
        # Process detected/tracked faces
        for tracker_info in trackers:
            # Process face using tracker_info["face_loc"]
            pass
            
        frame_count += 1
    
    cap.release()
```

**Expected Speedup**: 5-10x (tracking is much faster than detection)

### 8. Temporal Clustering for Duplicate Reduction

**Implementation Priority: MEDIUM**

For parliamentary videos where speakers remain in place for extended periods, we can group faces by time segments and select only the best quality face from each segment.

```python
def select_best_faces_by_segment(face_detections, segment_duration=30):
    """Group faces by time segments and select the best from each segment"""
    # Group by speaker and time segment
    segments = {}
    
    for detection in face_detections:
        timestamp = detection["timestamp"]
        speaker_id = detection["speaker_id"]
        quality = detection["quality_score"]
        
        # Calculate segment key
        segment_key = (speaker_id, int(timestamp / segment_duration))
        
        if segment_key not in segments or quality > segments[segment_key]["quality"]:
            segments[segment_key] = {
                "detection": detection,
                "quality": quality
            }
    
    # Return only the best face from each segment
    return [segment["detection"] for segment in segments.values()]
```

**Expected Speedup**: Not a direct speedup, but reduces storage requirements and post-processing time by 80-90%

## Combined Optimization Impact

By implementing all of the above optimizations, we can expect a combined speedup of **15-30x**, potentially reducing the processing time from 2+ hours to 4-8 minutes for a one-hour parliamentary video.

### Implementation Priority Order

1. Scene Change Detection (highest impact for parliamentary videos)
2. Face Tracking Instead of Re-Detection (highest impact, moderate complexity)
3. Region of Interest Restriction (high impact, easy to implement)
4. Reducing HOG Upsampling (high impact, trivial to implement)
5. Aggressive Frame Skipping (high impact, trivial to implement)
6. Downscaling Frames (medium impact, easy to implement)
7. Temporal Clustering (storage/post-processing optimization)
8. Early Termination (medium impact, moderate complexity)

## Monitoring and Validation

After implementing these optimizations, we should:

1. Compare face detection results before and after optimization to ensure we're not missing important faces
2. Measure and document the actual performance improvements
3. Fine-tune parameters based on real-world testing with parliamentary footage

## Next Steps

1. Implement the high-priority optimizations first
2. Test with a sample video to measure performance improvement
3. Adjust parameters as needed to balance speed and accuracy
4. Document the final configuration and performance metrics
