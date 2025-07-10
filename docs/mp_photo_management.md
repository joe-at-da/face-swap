# MP Photo Management Guide

## Overview

This document outlines the process for managing Member of Parliament (MP) photos in the Parliament TV application. Proper photo management is critical for accurate facial recognition and speaker identification.

## Directory Structure

All MP photos must be stored in the Docker container path:

```
/app/data/mp_photos/
```

This ensures consistent access across all services and maintains compatibility with the Docker environment.

## Photo Naming Convention

Photos are named according to the MP's unique identifier:

```
{member_id}.jpg
```

Where `member_id` is the integer identifier of the parliament member as stored in the database.

## Photo Acquisition Process

### 1. Source Priority

Photos are acquired in the following priority order:

1. Local cache (`/app/data/mp_photos/`)
2. Supabase storage (if available)
3. External URLs (parliament websites, official sources)
4. Default placeholder for unidentified speakers

### 2. Download and Caching

The `ParliamentMemberMatcher._process_member_image` method handles:

- Downloading photos from URLs
- Saving to the local cache directory
- Processing images for face detection
- Extracting face embeddings

```python
def _process_member_image(self, member_id: str, image_url: str) -> None:
    # Check if image already exists locally
    image_path = f"/app/data/mp_photos/{member_id}.jpg"
    
    if os.path.exists(image_path):
        # Use existing cached image
        pass
    elif image_url.startswith('http'):
        # Download from URL
        try:
            response = requests.get(image_url, stream=True)
            if response.status_code == 200:
                os.makedirs(os.path.dirname(image_path), exist_ok=True)
                with open(image_path, 'wb') as f:
                    for chunk in response.iter_content(1024):
                        f.write(chunk)
        except Exception as e:
            logger.error(f"Error downloading image: {str(e)}")
```

### 3. Face Embedding Extraction

After downloading, face embeddings are extracted:

```python
# Extract face embedding
face_locations = face_recognition.face_locations(image)
if face_locations:
    face_encodings = face_recognition.face_encodings(image, face_locations)
    if face_encodings:
        face_embedding = face_encodings[0]
        # Store embedding in database or cache
```

## Integration with Recognition Services

### ParliamentMemberMatcher

The `ParliamentMemberMatcher` class:

1. Loads parliament member data including photo URLs
2. Downloads and processes photos if not already cached
3. Extracts and stores face embeddings
4. Uses embeddings for face matching

### MultimodalRecognitionService

The `MultimodalRecognitionService` integrates with `ParliamentMemberMatcher`:

1. Initializes `ParliamentMemberMatcher` with database session
2. Ensures MP photos directory exists
3. Uses `ParliamentMemberMatcher` for speaker identification in frames

## Maintenance and Updates

### Regular Updates

MP photos should be updated:

1. When new MPs join parliament
2. When existing MPs change appearance significantly
3. If better quality photos become available

### Batch Processing

For bulk updates of MP photos:

1. Place new photos in `/app/data/mp_photos/` with correct naming
2. Run the face embedding extraction process
3. Update the database with new embeddings

## Troubleshooting

### Common Issues

1. **Missing Photos**:
   - Check network connectivity for downloads
   - Verify Supabase storage access
   - Ensure proper permissions on the photos directory

2. **Poor Recognition Quality**:
   - Ensure photos show clear frontal faces
   - Check for multiple faces in a single photo
   - Verify correct member_id to photo mapping

3. **Storage Issues**:
   - Monitor disk space in the Docker container
   - Implement cleanup for temporary processing files
   - Consider compression for large photo collections

## Best Practices

1. **Image Quality**:
   - Use high-resolution photos (minimum 300x300 pixels)
   - Prefer frontal face shots with good lighting
   - Avoid photos with multiple people

2. **Privacy and Compliance**:
   - Only use publicly available official photos
   - Follow applicable data protection regulations
   - Document the source of each photo

3. **Performance**:
   - Resize large images to reasonable dimensions
   - Optimize storage format (JPEG with appropriate compression)
   - Consider face cropping to focus on relevant features

## Future Improvements

1. **Enhanced Photo Management**:
   - Web UI for photo management
   - Automatic quality assessment
   - Multiple photos per MP for better recognition

2. **Advanced Recognition**:
   - Age-invariant face recognition
   - Recognition under different lighting conditions
   - Handling occlusions (glasses, masks, etc.)

3. **Integration**:
   - Automatic updates from official sources
   - Synchronization with Supabase storage
   - Versioning of MP photos

## Conclusion

Proper MP photo management is essential for accurate speaker identification in the Parliament TV application. By following these guidelines, we ensure consistent and reliable facial recognition across the entire system.
