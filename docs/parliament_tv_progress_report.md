# Parliament TV Capture - Progress Report

## Completed Tasks

1. **Stream URL Extraction**
   - ✅ Created `extract_direct_stream.py` using yt-dlp for reliable stream URL extraction
   - ✅ Successfully extracted working direct stream URLs from Parliament TV pages
   - ✅ Implemented time marker support to start capturing at specific timestamps

2. **Video Capture**
   - ✅ Implemented `parliament_capture_direct.py` for downloading and processing streams
   - ✅ Added support for ffmpeg-based video capture
   - ✅ Created testing tools for verifying stream URLs

3. **Facial Recognition**
   - ✅ Implemented facial recognition to detect when the speaker is no longer present
   - ✅ Fixed NumPy compatibility issues with OpenCV
   - ✅ Successfully tested with sample videos and real Parliament TV streams

4. **Code Organization**
   - ✅ Archived older extraction scripts for reference
   - ✅ Updated `extract_parliament_stream_v4.py` as a wrapper for backward compatibility
   - ✅ Created comprehensive documentation

## Next Steps

### 1. UI Integration (Frontend)

- [ ] Create a new component for Parliament TV capture in the frontend:

```javascript
// src/components/ParliamentTVCapture.vue
<template>
  <div class="parliament-tv-capture">
    <h2>Parliament TV Capture</h2>
    <form @submit.prevent="startCapture">
      <div class="form-group">
        <label for="parliamentUrl">Parliament TV URL</label>
        <input 
          type="text" 
          class="form-control" 
          id="parliamentUrl" 
          v-model="parliamentUrl" 
          placeholder="https://parliamentlive.tv/event/index/EVENT_ID?in=HH:MM:SS"
          required
        >
      </div>
      <div class="form-group">
        <label for="duration">Duration (seconds)</label>
        <input 
          type="number" 
          class="form-control" 
          id="duration" 
          v-model="duration" 
          min="10" 
          max="3600"
          required
        >
      </div>
      <div class="form-group">
        <label for="enableFacialRecognition">
          <input 
            type="checkbox" 
            id="enableFacialRecognition" 
            v-model="enableFacialRecognition"
          >
          Enable Facial Recognition
        </label>
      </div>
      <button 
        type="submit" 
        class="btn btn-primary" 
        :disabled="isCapturing"
      >
        {{ isCapturing ? 'Capturing...' : 'Start Capture' }}
      </button>
    </form>
    
    <div v-if="captureStatus" class="capture-status">
      <h3>Capture Status</h3>
      <div class="alert" :class="statusClass">
        {{ captureStatus.message }}
      </div>
      <div v-if="captureStatus.output_file" class="output-file">
        <p>Output File: {{ captureStatus.output_file }}</p>
        <button @click="viewCapture" class="btn btn-secondary">View Capture</button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      parliamentUrl: '',
      duration: 60,
      enableFacialRecognition: true,
      isCapturing: false,
      captureStatus: null
    }
  },
  computed: {
    statusClass() {
      if (!this.captureStatus) return '';
      return this.captureStatus.success ? 'alert-success' : 'alert-danger';
    }
  },
  methods: {
    async startCapture() {
      this.isCapturing = true;
      this.captureStatus = null;
      
      try {
        const response = await this.$http.post('/api/capture/parliament', {
          url: this.parliamentUrl,
          duration: this.duration,
          enable_facial_recognition: this.enableFacialRecognition
        });
        
        this.captureStatus = {
          success: response.data.success,
          message: response.data.success ? 'Capture completed successfully!' : 'Capture failed.',
          output_file: response.data.output_file
        };
      } catch (error) {
        this.captureStatus = {
          success: false,
          message: `Error: ${error.message}`
        };
      } finally {
        this.isCapturing = false;
      }
    },
    viewCapture() {
      if (this.captureStatus && this.captureStatus.output_file) {
        // Navigate to video player or open in new window
        window.open(`/media/${this.captureStatus.output_file}`, '_blank');
      }
    }
  }
}
</script>

<style scoped>
.parliament-tv-capture {
  max-width: 600px;
  margin: 0 auto;
  padding: 20px;
}
.form-group {
  margin-bottom: 15px;
}
.capture-status {
  margin-top: 30px;
  padding: 15px;
  border: 1px solid #ddd;
  border-radius: 4px;
}
.output-file {
  margin-top: 15px;
  padding: 10px;
  background-color: #f5f5f5;
  border-radius: 4px;
}
</style>
```

- [ ] Add the component to the main navigation/routing

### 2. API Integration (Backend)

- [ ] Create a new API endpoint for Parliament TV capture:

```python
# backend/api/capture.py
from flask import Blueprint, request, jsonify
import subprocess
import json
import os
import sys

capture_bp = Blueprint('capture', __name__)

@capture_bp.route('/api/capture/parliament', methods=['POST'])
def capture_parliament():
    data = request.json
    url = data.get('url')
    duration = data.get('duration', 300)  # Default to 5 minutes
    enable_facial_recognition = data.get('enable_facial_recognition', True)
    
    if not url:
        return jsonify({"success": False, "error": "URL is required"}), 400
    
    # Build the command
    cmd = [
        sys.executable,
        "scripts/parliament_capture_direct.py",
        url,
        "--duration", str(duration)
    ]
    
    # Run the capture script
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        # Parse the JSON output
        try:
            output = json.loads(result.stdout)
            return jsonify(output)
        except json.JSONDecodeError:
            return jsonify({
                "success": False,
                "error": "Failed to parse output",
                "stdout": result.stdout,
                "stderr": result.stderr
            }), 500
    except subprocess.CalledProcessError as e:
        return jsonify({
            "success": False,
            "error": f"Capture process failed with exit code {e.returncode}",
            "stdout": e.stdout,
            "stderr": e.stderr
        }), 500
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
```

- [ ] Register the blueprint in the main app:

```python
# backend/app.py
from api.capture import capture_bp

# ... existing code ...

app.register_blueprint(capture_bp)
```

### 3. Media Serving

- [ ] Configure the server to serve captured media files:

```python
# backend/app.py
from flask import send_from_directory
import os

# ... existing code ...

@app.route('/media/<path:filename>')
def serve_media(filename):
    media_dir = os.path.join(os.getcwd(), 'data', 'media', 'parliament_captures')
    return send_from_directory(media_dir, filename)
```

### 4. Testing and Optimization

- [ ] Create end-to-end tests for the Parliament TV capture functionality
- [ ] Optimize facial recognition parameters for better accuracy
- [ ] Implement error handling and retry mechanisms
- [ ] Add progress reporting during long-running captures

### 5. Documentation Updates

- [ ] Update the main README with information about the Parliament TV capture feature
- [ ] Create user documentation with examples and screenshots
- [ ] Document the API endpoints for developers

## Timeline

| Task | Estimated Time | Priority |
|------|----------------|----------|
| UI Integration | 2 days | High |
| API Integration | 1 day | High |
| Media Serving | 0.5 day | Medium |
| Testing and Optimization | 3 days | Medium |
| Documentation Updates | 1 day | Low |

## Conclusion

The Parliament TV capture solution is now functional and ready for integration with the main application. The next steps focus on creating a user-friendly interface and ensuring robust error handling for a production-ready feature.
