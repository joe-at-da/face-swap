#!/usr/bin/env python3
"""
Parliament TV Video Server (Host Version)

A simple HTTP server that serves Parliament TV videos from the Docker container's data directory.
This allows you to view the videos directly in your browser.

Usage:
  python host_video_server.py

Then open your browser to http://localhost:8765
"""

import os
import glob
import json
import subprocess
from datetime import datetime
import http.server
import socketserver
import urllib.parse
import mimetypes
import tempfile
import shutil

# Port for the HTTP server
PORT = 8765

# Temporary directory to store videos
TEMP_DIR = os.path.join(tempfile.gettempdir(), "parliament_videos")
os.makedirs(TEMP_DIR, exist_ok=True)

def format_size(size_bytes):
    """Format file size in bytes to human-readable format"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"

def format_timestamp(timestamp):
    """Format timestamp to human-readable format"""
    try:
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return "Unknown"

def get_videos_from_container():
    """Get list of videos from the Docker container"""
    try:
        # Run the list command in the container
        result = subprocess.run(
            ["docker", "exec", "the-mp-app-1", "python", "/app/scripts/play_parliament_videos.py", "list"],
            capture_output=True,
            text=True
        )
        
        # Parse the output to extract video information
        videos = []
        lines = result.stdout.split("\n")
        
        # Find the table header line
        header_index = -1
        for i, line in enumerate(lines):
            if line.strip().startswith("#   Filename"):
                header_index = i
                break
        
        if header_index == -1:
            print("Error: Could not find video list in output")
            return []
        
        # Skip the header and separator lines
        for line in lines[header_index + 2:]:
            if not line.strip() or "To play a video" in line:
                break
                
            parts = line.strip().split()
            if len(parts) < 4:
                continue
                
            # Extract information from the line
            index = parts[0]
            filename = parts[1]
            size = parts[2] + " " + parts[3]
            modified = " ".join(parts[4:])
            
            videos.append({
                "file_name": filename,
                "size_formatted": size,
                "modified_formatted": modified,
                "index": index
            })
        
        return videos
    except Exception as e:
        print(f"Error getting videos from container: {str(e)}")
        return []

def copy_video_from_container(filename):
    """Copy a video from the container to the temporary directory"""
    local_path = os.path.join(TEMP_DIR, filename)
    
    # Check if the file already exists
    if os.path.exists(local_path):
        return local_path
    
    try:
        # Copy the file from the container
        subprocess.run(
            ["docker", "cp", f"the-mp-app-1:/app/data/temp/{filename}", local_path],
            check=True
        )
        print(f"Copied {filename} to {local_path}")
        return local_path
    except Exception as e:
        print(f"Error copying video from container: {str(e)}")
        return None

class VideoHandler(http.server.SimpleHTTPRequestHandler):
    """Custom HTTP request handler for serving video files"""
    
    def do_GET(self):
        """Handle GET requests"""
        # Parse the URL
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        
        # Serve the index page
        if path == "/" or path == "/index.html":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            
            videos = get_videos_from_container()
            
            # Generate HTML
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Parliament TV Videos</title>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        max-width: 1200px;
                        margin: 0 auto;
                        padding: 20px;
                        background-color: #f5f5f5;
                    }}
                    h1 {{
                        color: #333;
                        border-bottom: 2px solid #ddd;
                        padding-bottom: 10px;
                    }}
                    table {{
                        width: 100%;
                        border-collapse: collapse;
                        margin-top: 20px;
                        background-color: white;
                        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                    }}
                    th, td {{
                        padding: 12px 15px;
                        text-align: left;
                        border-bottom: 1px solid #ddd;
                    }}
                    th {{
                        background-color: #f8f8f8;
                        font-weight: bold;
                    }}
                    tr:hover {{
                        background-color: #f1f1f1;
                    }}
                    .video-link {{
                        color: #0066cc;
                        text-decoration: none;
                        font-weight: bold;
                    }}
                    .video-link:hover {{
                        text-decoration: underline;
                    }}
                    .video-container {{
                        margin-top: 30px;
                        background-color: white;
                        padding: 20px;
                        border-radius: 5px;
                        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                    }}
                    video {{
                        width: 100%;
                        max-height: 600px;
                        background-color: black;
                    }}
                    .note {{
                        background-color: #fffde7;
                        padding: 10px;
                        border-left: 4px solid #ffd600;
                        margin: 20px 0;
                    }}
                </style>
            </head>
            <body>
                <h1>Parliament TV Videos</h1>
                
                <div class="note">
                    <p><strong>Note:</strong> Click on a video filename to view it directly in your browser. The first time you access a video, it will be copied from the Docker container to your local machine.</p>
                </div>
                
                <table>
                    <thead>
                        <tr>
                            <th>#</th>
                            <th>Filename</th>
                            <th>Size</th>
                            <th>Modified</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
            """
            
            for video in videos:
                html += f"""
                        <tr>
                            <td>{video['index']}</td>
                            <td><a href="/play/{video['file_name']}" class="video-link">{video['file_name']}</a></td>
                            <td>{video['size_formatted']}</td>
                            <td>{video['modified_formatted']}</td>
                            <td>
                                <a href="/video/{video['file_name']}" target="_blank">Download</a>
                            </td>
                        </tr>
                """
            
            html += """
                    </tbody>
                </table>
                
                <div id="player" style="display: none;" class="video-container">
                    <h2 id="video-title"></h2>
                    <video controls autoplay></video>
                </div>
                
                <script>
                    // JavaScript to handle video playback
                    document.addEventListener('DOMContentLoaded', function() {
                        const videoLinks = document.querySelectorAll('.video-link');
                        const player = document.getElementById('player');
                        const videoElement = document.querySelector('#player video');
                        const videoTitle = document.getElementById('video-title');
                        
                        videoLinks.forEach(link => {
                            link.addEventListener('click', function(e) {
                                e.preventDefault();
                                const videoUrl = this.href.replace('/play/', '/video/');
                                const filename = this.textContent;
                                
                                videoElement.src = videoUrl;
                                videoTitle.textContent = filename;
                                player.style.display = 'block';
                                
                                // Scroll to player
                                player.scrollIntoView({ behavior: 'smooth' });
                            });
                        });
                        
                        // Check if there's a hash in the URL
                        const hash = window.location.hash.substring(1);
                        if (hash) {
                            const link = document.querySelector(`.video-link[href="/play/${hash}"]`);
                            if (link) {
                                link.click();
                            }
                        }
                    });
                </script>
            </body>
            </html>
            """
            
            self.wfile.write(html.encode())
            return
        
        # Serve video files
        elif path.startswith("/video/"):
            file_name = os.path.basename(path)
            
            # Copy the video from the container if needed
            local_path = copy_video_from_container(file_name)
            
            if local_path and os.path.exists(local_path):
                self.send_response(200)
                self.send_header("Content-type", "video/mp4")
                self.send_header("Content-Length", str(os.path.getsize(local_path)))
                self.end_headers()
                
                with open(local_path, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.send_error(404, "File not found or could not be copied from container")
            return
        
        # Redirect /play/ to the index with the video loaded
        elif path.startswith("/play/"):
            file_name = os.path.basename(path)
            self.send_response(302)
            self.send_header("Location", f"/#{file_name}")
            self.end_headers()
            return
        
        # Serve other files from the current directory
        else:
            super().do_GET()

def main():
    """Start the HTTP server"""
    handler = VideoHandler
    
    with socketserver.TCPServer(("", PORT), handler) as httpd:
        print(f"Serving Parliament TV videos at http://localhost:{PORT}")
        print(f"Videos will be temporarily stored in {TEMP_DIR}")
        print("Press Ctrl+C to stop the server")
        httpd.serve_forever()

if __name__ == "__main__":
    main()
