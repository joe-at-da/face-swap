# Parliament TV Video Server Tools

This directory contains utility scripts for debugging and accessing Parliament TV videos captured by the application.

## Available Tools

### 1. Host Video Server (`host_video_server.py`)

A web server that runs on your host machine and provides access to Parliament TV videos stored in the Docker container.

#### Usage

```bash
python /Users/joebradley/Veedoo/Development/the-mp/scripts/host_video_server.py
```

Then open your browser to: http://localhost:8765

#### Features

- Lists all available Parliament TV videos
- Copies videos from Docker container to your local machine when requested
- Streams videos directly in your browser
- Provides download links for offline viewing
- Shows file details (size, creation date, etc.)

#### How It Works

1. The server runs on your host machine
2. When you request a video, it copies it from the Docker container to a temporary directory on your host
3. It then serves the video directly from your host machine
4. Temporary files are cleaned up when the server is stopped

### 2. Docker Container Video Server (`video_server.py`)

A web server that runs inside the Docker container and serves videos directly.

#### Usage

```bash
# From inside the Docker container
python /app/scripts/video_server.py

# Or from the host
docker exec -it the-mp-app-1 python /app/scripts/video_server.py
```

Then open your browser to: http://localhost:8765

**Note:** This server may not be accessible from your host machine due to Docker networking limitations. The host version is recommended for most debugging scenarios.

### 3. Video Listing and Playback (`play_parliament_videos.py`)

A utility script to list and play Parliament TV videos directly from the Docker container.

#### Usage

```bash
# From inside the Docker container
python /app/scripts/play_parliament_videos.py

# Or from the host
docker exec -it the-mp-app-1 python /app/scripts/play_parliament_videos.py
```

## When to Use Each Tool

1. **Host Video Server**: Use this when you need to view videos in your browser or download them to your host machine. This is the most user-friendly option.

2. **Docker Container Video Server**: Use this when you're working directly inside the Docker container or for debugging server-side issues.

3. **Video Listing and Playback**: Use this for a quick command-line listing of available videos or to play them directly inside the Docker container.

## Troubleshooting

### Common Issues

1. **Cannot access the video server**
   - Make sure the server is running
   - Check that you're using the correct port (8765)
   - If using the Docker container server, try the host version instead

2. **Videos not showing up**
   - Check that captures have completed successfully
   - Verify that video files exist in the data directory
   - Look at the server logs for any file access errors

3. **Video playback issues**
   - Try downloading the video instead of streaming it
   - Check browser console for any errors
   - Verify that the video format is supported by your browser

### Getting Help

For more detailed information about the Parliament TV integration, refer to the main documentation at:
`/Users/joebradley/Veedoo/Development/the-mp/docs/parliament_tv_integration.md`
