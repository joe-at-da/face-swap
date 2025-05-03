import os
import logging
import json
import subprocess
import glob
from datetime import datetime, timedelta
from pathlib import Path
import ffmpeg

from backend.core.config import settings
from backend.db import models

logger = logging.getLogger(__name__)

class VideoProcessor:
    def __init__(self):
        self.output_dir = Path(settings.MEDIA_STORAGE_PATH)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def create_clip(
        self,
        source_file: str,
        start_time: datetime,
        end_time: datetime,
        output_format: str = 'mp4'
    ) -> str:
        """
        Create a clip from a source video file between start_time and end_time.
        Returns the path to the created clip.
        """
        # Calculate duration in seconds
        duration = (end_time - start_time).total_seconds()
        if duration <= 0:
            raise ValueError("End time must be after start time")
            
        # Create output filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = self.output_dir / f"clip_{timestamp}.{output_format}"
        
        try:
            # Convert datetime to timedelta from start of video
            start_offset = timedelta(
                hours=start_time.hour,
                minutes=start_time.minute,
                seconds=start_time.second
            )
            
            stream = ffmpeg.input(source_file, ss=str(start_offset.total_seconds()))
            stream = ffmpeg.output(
                stream,
                str(output_file),
                t=str(duration),
                acodec='aac',
                vcodec='h264',
                preset='fast'
            )
            
            ffmpeg.run(stream, overwrite_output=True)
            logger.info(f"Created clip: {output_file}")
            return str(output_file)
            
        except ffmpeg.Error as e:
            logger.error(f"Failed to create clip: {e.stderr.decode() if e.stderr else str(e)}")
            raise
    
    def get_video_info(self, file_path: str) -> dict:
        """Get video metadata using ffprobe."""
        try:
            probe = ffmpeg.probe(file_path)
            video_info = next(s for s in probe['streams'] if s['codec_type'] == 'video')
            return {
                'duration': float(probe['format']['duration']),
                'width': int(video_info['width']),
                'height': int(video_info['height']),
                'codec': video_info['codec_name'],
                'bitrate': int(probe['format']['bit_rate'])
            }
        except ffmpeg.Error as e:
            logger.error(f"Failed to get video info: {e.stderr.decode() if e.stderr else str(e)}")
            raise
            
    def combine_audio_video(self, video_file: str, audio_file: str, output_format: str = 'mp4') -> str:
        """Combine separate audio and video files into a single output file.
        
        Args:
            video_file: Path to the video file
            audio_file: Path to the audio file
            output_format: Output format (default: mp4)
        """
        try:
            # Check if the video file exists
            if not os.path.exists(video_file):
                raise FileNotFoundError(f"Video file not found: {video_file}")
            
            # Check if the audio file exists
            if not os.path.exists(audio_file):
                raise FileNotFoundError(f"Audio file not found: {audio_file}")
            
            # Generate output filename
            output_file = f"{os.path.splitext(os.path.basename(video_file))[0]}_combined.{output_format}"
            output_path = os.path.join(os.path.dirname(video_file), output_file)
            
            # Log the files we're working with
            logging.info(f"Video file: {video_file}")
            logging.info(f"Audio file: {audio_file}")
            logging.info(f"Output file: {output_path}")
            
            # Get stream information for both files
            video_streams_cmd = [
                'ffprobe', 
                '-v', 'error', 
                '-show_entries', 'stream=index,codec_type,codec_name', 
                '-of', 'json', 
                video_file
            ]
            
            audio_streams_cmd = [
                'ffprobe', 
                '-v', 'error', 
                '-show_entries', 'stream=index,codec_type,codec_name', 
                '-of', 'json', 
                audio_file
            ]
            
            video_streams_result = subprocess.run(video_streams_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            audio_streams_result = subprocess.run(audio_streams_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            # Parse the stream information
            video_streams = json.loads(video_streams_result.stdout) if video_streams_result.returncode == 0 else {"streams": []}
            audio_streams = json.loads(audio_streams_result.stdout) if audio_streams_result.returncode == 0 else {"streams": []}
            
            logging.info(f"Video file streams: {json.dumps(video_streams, indent=2)}")
            logging.info(f"Audio file streams: {json.dumps(audio_streams, indent=2)}")
            
            # More detailed logging for audio debugging
            logging.info(f"Video file stderr: {video_streams_result.stderr}")
            logging.info(f"Audio file stderr: {audio_streams_result.stderr}")
            
            # Check if there are any audio streams in either file
            video_has_audio = any(stream.get("codec_type") == "audio" for stream in video_streams.get("streams", []))
            audio_has_audio = any(stream.get("codec_type") == "audio" for stream in audio_streams.get("streams", []))
            logging.info(f"Video file has audio: {video_has_audio}")
            logging.info(f"Audio file has audio: {audio_has_audio}")
            
            # Find video stream in video file
            video_stream_index = None
            for i, stream in enumerate(video_streams.get("streams", [])):
                if stream.get("codec_type") == "video":
                    video_stream_index = stream.get("index")
                    logging.info(f"Found video stream at index {video_stream_index} in {video_file}")
                    break
            
            # Find audio stream in audio file
            audio_stream_index = None
            for i, stream in enumerate(audio_streams.get("streams", [])):
                if stream.get("codec_type") == "audio":
                    audio_stream_index = stream.get("index")
                    logging.info(f"Found audio stream at index {audio_stream_index} in {audio_file}")
                    break
            
            # If no video stream found in video file, check if there's one in the audio file
            if video_stream_index is None:
                for i, stream in enumerate(audio_streams.get("streams", [])):
                    if stream.get("codec_type") == "video":
                        logging.info(f"Found video stream in audio file at index {stream.get('index')}")
                        # Swap the files since the video stream is in the audio file
                        video_file, audio_file = audio_file, video_file
                        video_stream_index = stream.get("index")
                        
                        # Re-check for audio stream in the new audio file
                        for j, astream in enumerate(video_streams.get("streams", [])):
                            if astream.get("codec_type") == "audio":
                                audio_stream_index = astream.get("index")
                                logging.info(f"Found audio stream at index {audio_stream_index} in swapped audio file")
                                break
                        break
            
            # If still no video stream, raise an error
            if video_stream_index is None:
                raise Exception(f"No video stream found in either file")
            
            # If no audio stream found, check if there's one in the video file
            if audio_stream_index is None:
                for i, stream in enumerate(video_streams.get("streams", [])):
                    if stream.get("codec_type") == "audio":
                        logging.info(f"Found audio stream in video file at index {stream.get('index')}")
                        audio_stream_index = stream.get("index")
                        # Use the same file for both video and audio
                        audio_file = video_file
                        break
            
            # If still no audio stream, try to find a Parliament TV capture with audio
            if audio_stream_index is None:
                logging.warning("No audio stream found in either file. Searching for Parliament TV captures with audio...")
                
                # Get the data directory
                data_dir = os.getenv("DATA_DIR", "/app/data")
                temp_dir = os.path.join(data_dir, "temp")
                
                # Look for Parliament TV captures that might have audio
                parliament_files = glob.glob(os.path.join(temp_dir, "parliament_*.mp4"))
                
                if parliament_files:
                    logging.info(f"Found {len(parliament_files)} Parliament TV captures to check for audio")
                    
                    # Try each file to find one with audio
                    for parl_file in parliament_files:
                        logging.info(f"Checking for audio in: {parl_file}")
                        
                        # Check if this file has audio
                        audio_check_cmd = [
                            'ffprobe', 
                            '-v', 'error', 
                            '-select_streams', 'a', 
                            '-show_entries', 'stream=index,codec_type,codec_name', 
                            '-of', 'json', 
                            parl_file
                        ]
                        
                        audio_check_result = subprocess.run(audio_check_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                        
                        if audio_check_result.returncode == 0:
                            audio_info = json.loads(audio_check_result.stdout)
                            if audio_info.get("streams") and len(audio_info.get("streams")) > 0:
                                logging.info(f"Found file with audio: {parl_file}")
                                audio_file = parl_file
                                audio_stream_index = audio_info["streams"][0]["index"]
                                break
                
                # If still no audio found, fall back to creating a silent track
                if audio_stream_index is None:
                    logging.warning("No Parliament TV captures with audio found. Creating a silent audio track.")
                    # Get video duration
                    duration_cmd = [
                        'ffprobe', 
                        '-v', 'error', 
                        '-show_entries', 'format=duration', 
                        '-of', 'csv=p=0', 
                        video_file
                    ]
                    
                    duration_result = subprocess.run(duration_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    if duration_result.returncode == 0:
                        duration = float(duration_result.stdout.strip())
                        logging.info(f"Video duration: {duration} seconds")
                        
                        # Create silent audio file
                        silent_audio = os.path.join(os.path.dirname(output_path), "temp_silent.aac")
                        silent_cmd = [
                            'ffmpeg',
                            '-f', 'lavfi',
                            '-i', 'anullsrc=r=44100:cl=stereo',
                            '-t', str(duration),
                            '-c:a', 'aac',
                            '-y',
                            silent_audio
                        ]
                        
                        silent_result = subprocess.run(silent_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                        if silent_result.returncode == 0:
                            logging.info(f"Created silent audio track: {silent_audio}")
                            audio_file = silent_audio
                            audio_stream_index = 0
                        else:
                            logging.error(f"Failed to create silent audio: {silent_result.stderr}")
                    else:
                        logging.error(f"Failed to get video duration: {duration_result.stderr}")
            
            # Build the ffmpeg command for combining
            cmd = [
                'ffmpeg',
                '-i', video_file,
                '-i', audio_file
            ]
            
            # If the files are the same, we need a different mapping strategy
            if video_file == audio_file:
                cmd.extend([
                    '-c:v', 'copy',
                    '-c:a', 'aac',
                    '-map', f'0:{video_stream_index}',  # Map video stream
                    '-map', f'0:{audio_stream_index}',  # Map audio stream from same file
                    '-shortest',
                    '-y',
                    output_path
                ])
            else:
                cmd.extend([
                    '-c:v', 'copy',
                    '-c:a', 'aac',
                    '-map', f'0:{video_stream_index}',  # Map video stream from first file
                    '-map', f'1:{audio_stream_index}',  # Map audio stream from second file
                    '-shortest',
                    '-y',
                    output_path
                ])
            
            logging.info(f"Running ffmpeg command: {' '.join(cmd)}")
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            logging.info(f"FFmpeg stdout: {result.stdout}")
            logging.info(f"FFmpeg stderr: {result.stderr}")
            
            if result.returncode != 0:
                error_msg = f"Error combining audio and video: {result.stderr}"
                logging.error(error_msg)
                raise Exception(error_msg)
            
            # Clean up temporary files if created
            if audio_file.endswith("temp_silent.aac") and os.path.exists(audio_file):
                os.remove(audio_file)
                logging.info(f"Removed temporary silent audio file: {audio_file}")
            
            logging.info(f"Successfully combined audio and video to: {output_path}")
            return output_path
        except Exception as e:
            logging.error(f"Error in combine_audio_video: {str(e)}")
            raise
