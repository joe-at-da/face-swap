#!/usr/bin/env python3
"""
Parliament TV Video Server

A simple HTTP server that serves Parliament TV videos from the data directory.
This allows you to view the videos directly in your browser.

Usage:
  python video_server.py

Then open your browser to http://localhost:8765
"""

import os
import glob
import json
from datetime import datetime
import http.server
import socketserver
import urllib.parse
import mimetypes

# Define the data directory where videos are stored
DATA_DIR = "/app/data/temp"
PORT = 8765

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

def get_videos():
    """Get all Parliament TV videos in the data directory"""
    # Create patterns to match Parliament TV video files
    patterns = [
        os.path.join(DATA_DIR, "parliament_stream_*.mp4"),
        os.path.join(DATA_DIR, "capture_*.mp4")
    ]
    
    videos = []
    for pattern in patterns:
        matching_files = glob.glob(pattern)
        for file_path in matching_files:
            try:
                file_name = os.path.basename(file_path)
                file_size = os.path.getsize(file_path)
                modified_time = os.path.getmtime(file_path)
                
                videos.append({
                    "file_name": file_name,
                    "file_path": file_path,
                    "file_size": file_size,
                    "modified_time": modified_time,
                    "size_formatted": format_size(file_size),
                    "modified_formatted": format_timestamp(modified_time)
                })
            except Exception as e:
                print(f"Error processing file {file_path}: {str(e)}")
    
    # Sort videos by modified time (newest first)
    videos.sort(key=lambda x: x["modified_time"], reverse=True)
    return videos

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
            
            videos = get_videos()
            
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
                    <p><strong>Note:</strong> Click on a video filename to view it directly in your browser.</p>
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
            
            for i, video in enumerate(videos, 1):
                html += f"""
                        <tr>
                            <td>{i}</td>
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
            file_path = os.path.join(DATA_DIR, file_name)
            
            if os.path.exists(file_path) and os.path.isfile(file_path):
                self.send_response(200)
                self.send_header("Content-type", "video/mp4")
                self.send_header("Content-Length", str(os.path.getsize(file_path)))
                self.end_headers()
                
                with open(file_path, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.send_error(404, "File not found")
            return
        
        # Redirect /play/ to the index with the video loaded
        elif path.startswith("/play/"):
            self.send_response(302)
            self.send_header("Location", "/")
            self.end_headers()
            return
        
        # Serve other files from the current directory
        else:
            super().do_GET()

def main():
    """Start the HTTP server"""
    handler = VideoHandler
    
    with socketserver.TCPServer(("0.0.0.0", PORT), handler) as httpd:
        print(f"Serving Parliament TV videos at http://localhost:{PORT}")
        print("Press Ctrl+C to stop the server")
        httpd.serve_forever()

if __name__ == "__main__":
    main()
