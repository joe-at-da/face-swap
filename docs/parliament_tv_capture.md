# Parliament TV Capture with Facial Recognition

This document provides a comprehensive guide to the Parliament TV capture solution with facial recognition.

## Overview

The Parliament TV capture solution allows you to:

1. Extract stream URLs from Parliament TV event pages
2. Download and process video streams
3. Use facial recognition to automatically stop recording when the speaker is no longer present
4. Handle time markers to start capturing at specific timestamps

## Setup

### Prerequisites

- Python 3.8 or higher
- ffmpeg
- yt-dlp
- Docker (optional, for containerized execution)

### Installation

1. Install the required system dependencies:

```bash
# macOS
brew install ffmpeg yt-dlp

# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y ffmpeg python3-pip
pip install yt-dlp
```

2. Install the Python dependencies:

```bash
pip install requests opencv-python numpy
```

3. If using Docker, ensure the Docker container has the necessary dependencies:

```bash
docker exec the-mp-app-1 apt-get update
docker exec the-mp-app-1 apt-get install -y python3-opencv libopencv-dev
docker exec the-mp-app-1 pip install "numpy<2.0.0"
```

## Usage

### Direct Capture from Parliament TV

To capture a Parliament TV stream with facial recognition:

```bash
./scripts/parliament_capture_direct.py "https://parliamentlive.tv/event/index/EVENT_ID?in=HH:MM:SS" --duration SECONDS
```

Example:

```bash
./scripts/parliament_capture_direct.py "https://parliamentlive.tv/event/index/263b4186-393c-49ce-aa55-68b9accd7a4e?in=13:25:38" --duration 120
```

This will:
1. Extract the direct stream URL from the Parliament TV event page
2. Download the stream for the specified duration
3. Process it with facial recognition
4. Output the captured video to `data/media/parliament_captures/`

### Testing the Stream URL

To test if a Parliament TV stream URL is valid:

```bash
./scripts/test_stream_url.sh "STREAM_URL"
```

Example:

```bash
./scripts/test_stream_url.sh "https://2F0F8Fc-az-westeurope-fsly.cdn.redbee.live/ukparliament/parliamentlive/assets/263b4186-393c-49ce-aa55-68b9accd7a4e_0D62A9b/materials/AG41LtGPSo_0D62A9b/vod-idx.ism/vod-idx-video=3000000.m3u8"
```

### Testing Facial Recognition

To test facial recognition with a sample video:

```bash
./scripts/test_facial_recognition.sh
```

## Integration with Backend API

To integrate the Parliament TV capture solution with the backend API:

1. Use the `parliament_capture_wrapper.py` script as a bridge between the API and the capture solution:

```python
# Example API endpoint
@app.route('/api/capture/parliament', methods=['POST'])
def capture_parliament():
    data = request.json
    url = data.get('url')
    duration = data.get('duration', 90)  # Default to 90 seconds
    
    # Call the wrapper script
    result = subprocess.run([
        sys.executable,
        "scripts/parliament_capture_wrapper.py",
        url,
        "--duration", str(duration)
    ], capture_output=True, text=True)
    
    # Parse the output
    try:
        output = json.loads(result.stdout)
        return jsonify(output)
    except json.JSONDecodeError:
        return jsonify({"success": False, "error": "Failed to parse output"})
```

2. Update the frontend to include a form for Parliament TV capture:

```html
<form @submit.prevent="captureParliament">
  <div class="form-group">
    <label for="parliamentUrl">Parliament TV URL</label>
    <input type="text" class="form-control" id="parliamentUrl" v-model="parliamentUrl" 
           placeholder="https://parliamentlive.tv/event/index/EVENT_ID?in=HH:MM:SS">
  </div>
  <div class="form-group">
    <label for="duration">Duration (seconds)</label>
    <input type="number" class="form-control" id="duration" v-model="duration" min="10" max="3600">
  </div>
  <button type="submit" class="btn btn-primary">Start Capture</button>
</form>
```

## Debugging

### Common Issues

1. **DNS Resolution Issues**

If you encounter DNS resolution issues with the Parliament TV stream URLs:

```
Failed to resolve hostname p7of6fc-a2-westeurope-fay.cdn.redbee.live: nodename nor servname provided, or not known
```

Solution: Use the `extract_direct_stream.py` script to get a working direct stream URL:

```bash
./scripts/extract_direct_stream.py "https://parliamentlive.tv/event/index/EVENT_ID?in=HH:MM:SS"
```

2. **NumPy Compatibility Issues with OpenCV**

If you encounter NumPy compatibility issues with OpenCV:

```
ImportError: numpy.core.multiarray failed to import
```

Solution: Downgrade NumPy to a compatible version:

```bash
pip uninstall -y numpy && pip install "numpy<2.0.0"
```

3. **ffmpeg or yt-dlp Not Found**

If you encounter errors related to ffmpeg or yt-dlp not being found:

```
FileNotFoundError: [Errno 2] No such file or directory: 'ffmpeg'
```

Solution: Install the missing tools:

```bash
brew install ffmpeg yt-dlp  # macOS
sudo apt-get install -y ffmpeg  # Ubuntu/Debian
pip install yt-dlp
```

### Logging

All scripts include detailed logging. Check the log files in the project directory for troubleshooting:

```
parliament_capture_*.log
```

## Script Reference

### extract_direct_stream.py

Extracts the direct stream URL from a Parliament TV event page.

```bash
./scripts/extract_direct_stream.py <parliament_tv_url> [--output OUTPUT_FILE]
```

### parliament_capture_direct.py

Captures a Parliament TV stream with facial recognition.

```bash
./scripts/parliament_capture_direct.py <parliament_tv_url> [--duration SECONDS] [--output OUTPUT_FILE]
```

### facial_recognition_capture.py

Processes a video file with facial recognition.

```bash
./scripts/facial_recognition_capture.py <video_file> [--duration SECONDS] [--output OUTPUT_FILE] [--interval SECONDS]
```

### test_stream_url.sh

Tests if a stream URL is valid by downloading a small segment.

```bash
./scripts/test_stream_url.sh <stream_url> [--play]
```

### test_facial_recognition.sh

Tests facial recognition with a sample video.

```bash
./scripts/test_facial_recognition.sh
```

## Architecture

The Parliament TV capture solution consists of the following components:

1. **URL Extraction**: Extracts the direct stream URL from a Parliament TV event page
2. **Stream Download**: Downloads the stream using ffmpeg or yt-dlp
3. **Facial Recognition**: Processes the video with OpenCV to detect faces
4. **Integration Layer**: Connects the capture solution to the backend API

## Future Improvements

1. **Speaker-Specific Face Recognition**: Train the facial recognition model to recognize specific speakers
2. **Improved Time Marker Handling**: Better handling of time markers for more precise capture start times
3. **Automatic Transcription**: Add automatic transcription of the captured video
4. **Real-Time Processing**: Process the stream in real-time instead of downloading it first
5. **Better Error Handling**: Improve error handling and recovery mechanisms
