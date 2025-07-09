# Parliament TV Face Recognition Improvements

This document outlines the improvements made to the Parliament TV face recognition system to ensure accurate member identification in real Parliament TV streams.

## Key Improvements

1. **Face Detection Enhancements**
   - Lowered the face detector score threshold from 0.9 to 0.3 for better detection
   - Fixed input size in `detect_faces` to use original image dimensions before resizing
   - These changes dramatically improve face detection accuracy on real Parliament TV frames

2. **Member Embedding Updates**
   - Created a systematic approach to update member embeddings using real Parliament TV frames
   - Ensures better matching between detected faces and member records
   - Addresses the root cause of member identification issues

## Using the Member Embedding Update Tool

The `update_member_embeddings.py` script provides a systematic way to identify and update member embeddings with poor matches.

### Usage

```bash
# Process a single frame
python update_member_embeddings.py --frame_path /path/to/frame.jpg --threshold 0.7 --update

# Process all frames in a directory
python update_member_embeddings.py --frames_dir /path/to/frames/ --threshold 0.7 --update

# Process frames from a video
python update_member_embeddings.py --video_path /path/to/video.mp4 --threshold 0.7 --update
```

### Parameters

- `--frame_path`: Path to a single Parliament TV frame
- `--frames_dir`: Path to a directory containing Parliament TV frames
- `--video_path`: Path to a Parliament TV video file
- `--threshold`: Similarity threshold below which to update embeddings (default: 0.7)
- `--update`: If provided, updates embeddings; otherwise, just reports issues

## Workflow for Improving Member Recognition

1. **Extract frames** from real Parliament TV streams
2. **Run the update tool** to identify members with poor matching scores
3. **Update embeddings** for these members using real frames
4. **Test the pipeline** with real Parliament TV streams to verify improvements

## Implementation Details

The face recognition improvements are implemented in:

- `backend/services/recognition/face_recognition.py`: Face detection parameter tuning
- `update_member_embeddings.py`: Systematic embedding update tool

## Best Practices

1. Always use real Parliament TV frames for embedding updates
2. Set an appropriate threshold (0.7 recommended) to identify poor matches
3. Regularly update embeddings as new members appear in Parliament TV
4. Verify improvements with real Parliament TV streams

## Troubleshooting

If member identification issues persist:

1. Check if the member has an embedding in the database
2. Verify the quality of the frame used for embedding extraction
3. Try updating the embedding with a clearer frame
4. Ensure the face detector is correctly configured
