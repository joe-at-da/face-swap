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
        
        try:
            # Input video and audio streams
            video_stream = ffmpeg.input(video_file)
            audio_stream = ffmpeg.input(audio_file)
            
            # Combine streams
            stream = ffmpeg.output(
                video_stream,
                audio_stream,
                str(output_file),
                vcodec='copy',  # Copy video codec to avoid re-encoding
                acodec='aac',   # Use AAC for audio
                strict='experimental'
            )
            
            ffmpeg.run(stream, overwrite_output=True)
            logger.info(f"Created combined audio/video file: {output_file}")
            return str(output_file)
            
        except ffmpeg.Error as e:
            logger.error(f"Failed to combine audio and video: {e.stderr.decode() if e.stderr else str(e)}")
            raise
