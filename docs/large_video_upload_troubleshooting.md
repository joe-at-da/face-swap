# Large Video Upload Troubleshooting Guide

This document provides guidance on troubleshooting and resolving issues with large video file uploads to Supabase storage.

## Current Implementation

The current implementation uses a memory-efficient streaming upload approach with:
- Extended timeout (3600 seconds / 1 hour)
- Memory-efficient streaming using `requests_toolbelt.MultipartEncoderMonitor`
- Progress reporting during upload (every 5% or 30 seconds)
- Retry logic with exponential backoff
- Detailed logging for transparency
- Error reporting that shows actual errors rather than masking them

## Diagnosing Upload Failures

### Identifying the Actual Error

When a large upload fails, we need to determine the exact cause. Exit code 137 in Docker typically indicates that the process was killed due to exceeding memory limits, but we should verify this by:

1. **Checking Docker Logs**:
   ```bash
   docker-compose -f docker-compose.dev.yml logs app | grep "OutOfMemory" -A 10 -B 10
   ```

2. **Monitoring Resource Usage**:
   ```bash
   docker stats $(docker-compose -f docker-compose.dev.yml ps -q app)
   ```

3. **Checking Supabase Logs**:
   ```bash
   docker-compose -f docker-compose.dev.yml logs supabase | grep "error" -A 5 -B 5
   ```

4. **Examining Network Issues**:
   - Check if there are network timeouts or connection resets
   - Look for any firewall or proxy issues between your server and Supabase

## Implemented Solution

We successfully implemented a combination of two approaches to solve the large video upload issue:

### 1. Increased Docker Container Memory

We increased the memory allocation for the Docker container to 6GB:

```yaml
# In docker-compose.dev.yml
services:
  app:
    # other configuration...
    deploy:
      resources:
        limits:
          memory: 6G  # Increased from default (usually 2G)
```

### 2. Memory-Efficient Streaming Upload Implementation

The key to our solution was implementing a memory-efficient streaming upload approach using the `requests_toolbelt` library. This approach:

- Streams the file in chunks without loading the entire file into memory
- Provides real-time progress reporting during upload
- Maintains a single file in Supabase storage (no chunking)
- Preserves all the benefits of our direct upload approach (extended timeout, retry logic)

```python
# Key implementation details
from requests_toolbelt import MultipartEncoder, MultipartEncoderMonitor

# Create a callback function to monitor upload progress
def create_callback(encoder):
    last_report_time = time.time()
    last_report_percent = 0
    
    def callback(monitor):
        nonlocal last_report_time, last_report_percent
        current_time = time.time()
        current_percent = int((monitor.bytes_read / monitor.len) * 100)
        
        # Report progress every 5% or 30 seconds
        if (current_percent >= last_report_percent + 5) or \
           (current_time - last_report_time >= 30):
            logger.info(f"Upload progress: {current_percent}% ({monitor.bytes_read / (1024*1024):.2f} MB of {monitor.len / (1024*1024):.2f} MB)")
            last_report_time = current_time
            last_report_percent = current_percent
    
    return callback

# Open the file directly for the encoder
with open(file_path, 'rb') as file_data:
    # Create the multipart encoder with the file
    encoder = MultipartEncoder(
        fields={
            **file_options,
            'file': (os.path.basename(file_path), file_data, content_type or 'application/octet-stream')
        }
    )
    
    # Create a monitor for the encoder with progress callback
    monitor = MultipartEncoderMonitor(encoder, create_callback(encoder))
    
    # Update headers with the content type from the encoder
    headers['Content-Type'] = monitor.content_type
    
    # Use the session to upload the file with streaming
    response = session.post(
        url,
        data=monitor,
        headers=headers,
        timeout=extended_timeout
    )
```

### Results

With this implementation, we successfully uploaded a 2.75GB video file in 66.46 seconds with an average speed of 41.39 MB/s, without encountering any memory issues.

## Alternative Approaches

If you encounter issues with the current implementation, consider these alternatives:

### 1. Direct Client-to-Supabase Uploads

For extremely large files or high-volume scenarios, consider implementing direct uploads from the client to Supabase:

1. Your server generates a signed URL or token
2. The client uploads directly to Supabase
3. Your server processes the file after upload completes

This approach bypasses your server for the actual file transfer, reducing server load and memory usage.

## Production Considerations

1. **Monitoring**: Set up monitoring for upload processes to catch failures early
2. **Logging**: Ensure detailed logging is enabled to diagnose issues
3. **Timeouts**: Adjust timeouts based on real-world upload speeds and file sizes
4. **Retries**: Configure retry parameters based on network reliability

## Testing Methodology

When testing large uploads:

1. Start with smaller files (10-100MB) to verify basic functionality
2. Gradually increase file size to identify thresholds where issues occur
3. Monitor resource usage during uploads
4. Test with realistic network conditions

## Next Steps for Implementation

1. Experiment with increased memory allocation
2. If memory issues persist, implement streaming optimizations
3. Consider direct client-to-Supabase uploads for the largest files
4. Document findings and successful approaches
