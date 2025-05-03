import os
import logging
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
            
        Returns:
            Path to the combined output file
        """
        # Create output filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = self.output_dir / f"combined_{timestamp}.{output_format}"
        output_path = str(output_file)
        
        try:
            # Check if files exist
            if not os.path.exists(video_file):
                raise FileNotFoundError(f"Video file not found: {video_file}")
            if not os.path.exists(audio_file):
                raise FileNotFoundError(f"Audio file not found: {audio_file}")
                
            # Log the file paths
            logger.info(f"Combining video: {video_file} with audio: {audio_file}")
            
            # Use direct ffmpeg command execution instead of the Python wrapper
            import subprocess
            
            # First, check if the audio file has an audio stream
            probe_cmd = [
                'ffprobe', 
                '-v', 'error',
                '-select_streams', 'a:0',
                '-show_entries', 'stream=codec_type',
                '-of', 'csv=p=0',
                audio_file
            ]
            
            probe_process = subprocess.run(
                probe_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            
            has_video = video_probe.stdout.strip() == 'video'
            if not has_video:
                raise Exception(f"No video stream found in the video file: {video_file}")
            
            # Check if the audio file has an audio stream
            audio_probe = subprocess.run(
                ['ffprobe', '-v', 'error', '-select_streams', 'a', '-show_entries', 'stream=codec_type', '-of', 'csv=p=0', audio_file],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            has_audio = audio_probe.stdout.strip() == 'audio'
            if not has_audio:
                raise Exception(f"No audio stream found in the audio file: {audio_file}")
            
            logging.info(f"Combining video file: {video_file} with audio file: {audio_file}")
            
            # Combine video and audio using ffmpeg
            cmd = [
                'ffmpeg',
                '-i', video_file,  # Input video file
                '-i', audio_file,  # Input audio file
                '-c:v', 'copy',    # Copy video codec
                '-c:a', 'aac',     # Use AAC for audio
                '-map', '0:v:0',   # Map video from first input
                '-map', '1:a:0',   # Map audio from second input
                '-shortest',       # End when shortest input ends
                output_path
            ]
            
            logging.info(f"Running ffmpeg command: {' '.join(cmd)}")
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            if result.returncode != 0:
                error_msg = f"Error combining audio and video: {result.stderr}"
                logging.error(error_msg)
                raise Exception(error_msg)
            
            logging.info(f"Successfully combined audio and video to: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error combining audio and video: {str(e)}")
            raise
