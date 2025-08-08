import os
import json
import logging
from datetime import datetime
from pathlib import Path
import subprocess
from typing import Dict, List, Optional, Tuple

from backend.core.config import settings

logger = logging.getLogger(__name__)

class TranscriptionService:
    """Service for transcribing video content using speech recognition."""
    
    def __init__(self, model_size: str = "base"):
        """
        Initialize the transcription service.
        
        Args:
            model_size: Size of the Whisper model to use ('tiny', 'base', 'small', 'medium', 'large')
        """
        self.model_size = model_size
        self.output_dir = Path(settings.MEDIA_STORAGE_PATH) / "transcriptions"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir = Path(settings.TEMP_STORAGE_PATH) / "transcriptions"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Check if whisper is installed
        self._check_whisper()
    
    def _check_whisper(self) -> bool:
        """Check if whisper is installed and available."""
        try:
            import whisper
            logger.info(f"Whisper is available: {whisper.__version__ if hasattr(whisper, '__version__') else 'unknown version'}")
            return True
        except ImportError:
            logger.error("Whisper is not installed. Transcription will not work.")
            logger.error("Install with: pip install openai-whisper")
            return False
        
    def transcribe_video(self, video_path: str, language: str = "en", speaker_data: Optional[Dict] = None) -> Dict:
        """
        Transcribe a video file using Whisper speech recognition.
        
        Args:
            video_path: Path to the video file
            language: Language code (default: 'en' for English)
            speaker_data: Optional speaker identification data for diarization
            
        Returns:
            Dictionary containing transcription data with timestamps
        """
        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")
            
        # Create output filename based on input video
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = self.output_dir / f"{video_path.stem}_transcription_{timestamp}.json"
        
        try:
            # Run Whisper for transcription
            logger.info(f"Starting transcription for {video_path} with language {language}")
            result = self._run_whisper(str(video_path), language)
            
            # Process segments and add speaker information if available
            processed_segments = self._process_segments(result["segments"], speaker_data)
            
            # Create final result
            final_result = {
                "text": result["text"],
                "segments": processed_segments,
                "language": language,
                "duration": processed_segments[-1]["end"] if processed_segments else 0,
                "model": self.model_size,
                "source_file": str(video_path),
                "timestamp": timestamp,
                "has_speaker_data": speaker_data is not None
            }
            
            # Save transcription to file
            with open(output_file, 'w') as f:
                json.dump(final_result, f, indent=2)
                
            logger.info(f"Transcription saved to {output_file}")
            return final_result
            
        except Exception as e:
            logger.error(f"Transcription failed: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            raise
    
    def _run_whisper(self, video_path: str, language: str) -> Dict:
        """
        Run Whisper speech recognition on a video file with GPU acceleration and OOM prevention.
        
        Args:
            video_path: Path to the video file
            language: Language code
            
        Returns:
            Dictionary with transcription data
        """
        try:
            # Verify the audio file exists and has content
            import os
            import subprocess
            import json
            import torch
            
            if not os.path.exists(video_path):
                error_msg = f"Audio file not found: {video_path}"
                logger.error(error_msg)
                raise FileNotFoundError(error_msg)
            
            # Check file size
            file_size = os.path.getsize(video_path)
            logger.info(f"Audio file size: {file_size} bytes")
            if file_size == 0:
                error_msg = f"Audio file is empty (0 bytes): {video_path}"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            # Validate audio file with ffprobe
            try:
                ffprobe_cmd = [
                    "ffprobe",
                    "-v", "error",
                    "-show_entries", "format=duration,bit_rate",
                    "-show_streams",
                    "-of", "json",
                    video_path
                ]
                result = subprocess.run(ffprobe_cmd, capture_output=True, text=True, check=True)
                audio_info = json.loads(result.stdout)
                logger.info(f"Audio file info: {audio_info}")
                
                # Check if the file has audio streams
                has_audio = False
                for stream in audio_info.get('streams', []):
                    if stream.get('codec_type') == 'audio':
                        has_audio = True
                        logger.info(f"Found audio stream: {stream}")
                        break
                
                if not has_audio:
                    logger.warning(f"No audio streams found in file: {video_path}")
                    # Continue anyway, as the file might still be processable
                
                # Check duration
                duration = float(audio_info.get('format', {}).get('duration', 0))
                logger.info(f"Audio duration: {duration} seconds")
                if duration <= 0:
                    error_msg = f"Audio file has invalid duration: {duration} seconds"
                    logger.error(error_msg)
                    raise ValueError(error_msg)
                    
            except (subprocess.CalledProcessError, json.JSONDecodeError, ValueError) as e:
                logger.error(f"Failed to validate audio file: {str(e)}")
                # Continue anyway, as Whisper might still be able to process it
            
            # Import whisper here to avoid import errors if not installed
            import whisper
            
            # Detect GPU availability and configure device
            device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(f"🔧 Using device: {device}")
            
            if device == "cuda":
                gpu_info = torch.cuda.get_device_name(0)
                gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1024**3
                logger.info(f"🚀 GPU detected: {gpu_info} ({gpu_memory:.1f}GB VRAM)")
                logger.info(f"🔥 CUDA version: {torch.version.cuda}")
            else:
                logger.info("⚠️  No GPU detected, using CPU (will be slower)")
            
            # Load the model with device specification
            logger.info(f"📥 Loading Whisper model: {self.model_size} on {device}")
            model = whisper.load_model(self.model_size, device=device)
            
            # Check file duration for chunking strategy
            duration = float(audio_info.get('format', {}).get('duration', 0))
            logger.info(f"⏱️  Audio duration: {duration:.1f} seconds ({duration/3600:.1f} hours)")
            
            # Use optimized settings for large files
            transcribe_options = {
                "language": language,
                "verbose": True,
                "task": "transcribe",
                "initial_prompt": "This is a Parliament TV recording with speakers discussing various topics.",
                "temperature": 0.0,  # Deterministic output
                "beam_size": 5,      # Better accuracy
                "patience": 1.0,     # Faster processing
                "length_penalty": 1.0,
                "suppress_tokens": "-1",  # Don't suppress any tokens
                "condition_on_previous_text": True,  # Better context
            }
            
            # Optimize for GPU vs CPU
            if device == "cuda":
                transcribe_options["fp16"] = True  # Use fp16 on GPU for memory efficiency
            else:
                transcribe_options["fp16"] = False  # Use fp32 on CPU for stability
            
            # For very large files (>4 hours), implement chunking to prevent OOM
            if duration > 14400:  # 4 hours
                logger.info(f"🔄 Large file detected ({duration/3600:.1f}h), using chunked processing")
                result = self._transcribe_chunked(model, video_path, transcribe_options, duration)
            else:
                # Transcribe the video with optimized options
                logger.info(f"🎤 Transcribing audio: {video_path}")
                result = model.transcribe(video_path, **transcribe_options)
            
            # Check if the result contains any text
            if not result.get("text", "").strip():
                logger.warning(f"⚠️  Whisper returned empty transcription for {video_path}")
                
                # If no text was found, try with a smaller model as fallback
                if self.model_size != "base":
                    logger.info(f"🔄 Trying with 'base' model as fallback")
                    fallback_model = whisper.load_model("base", device=device)
                    fallback_options = transcribe_options.copy()
                    result = fallback_model.transcribe(video_path, **fallback_options)
            
            # Log the result summary with enhanced metrics
            segments_count = len(result.get('segments', []))
            text_length = len(result.get('text', ''))
            words_count = len(result.get('text', '').split())
            
            logger.info(f"✅ Transcription completed successfully!")
            logger.info(f"📊 Results: {segments_count} segments, {text_length} characters, ~{words_count} words")
            if duration > 0:
                wpm = (words_count / duration) * 60
                logger.info(f"📈 Speech rate: {wpm:.1f} words per minute")
            
            return result
            
        except ImportError as e:
            logger.error(f"Whisper is not installed or has dependency issues: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error during Whisper transcription: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise
    
    def _transcribe_chunked(self, model, video_path: str, transcribe_options: dict, total_duration: float) -> dict:
        """
        Transcribe large audio files in chunks to prevent OOM errors.
        
        Args:
            model: Loaded Whisper model
            video_path: Path to the audio file
            transcribe_options: Transcription options
            total_duration: Total duration of the audio file in seconds
            
        Returns:
            Combined transcription result
        """
        import subprocess
        import tempfile
        import os
        
        chunk_duration = 1800  # 30 minutes per chunk
        chunks_count = int(total_duration / chunk_duration) + 1
        
        logger.info(f"🔄 Processing {chunks_count} chunks of {chunk_duration/60:.1f} minutes each")
        
        all_segments = []
        full_text = ""
        
        for i in range(chunks_count):
            start_time = i * chunk_duration
            end_time = min((i + 1) * chunk_duration, total_duration)
            
            if start_time >= total_duration:
                break
                
            logger.info(f"📝 Processing chunk {i+1}/{chunks_count}: {start_time/60:.1f}-{end_time/60:.1f} minutes")
            
            # Create temporary chunk file
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
                temp_chunk_path = temp_file.name
            
            try:
                # Extract chunk using ffmpeg
                ffmpeg_cmd = [
                    "ffmpeg", "-y",
                    "-i", video_path,
                    "-ss", str(start_time),
                    "-t", str(end_time - start_time),
                    "-c", "copy",
                    temp_chunk_path
                ]
                
                subprocess.run(ffmpeg_cmd, capture_output=True, check=True)
                
                # Transcribe chunk
                chunk_options = transcribe_options.copy()
                chunk_result = model.transcribe(temp_chunk_path, **chunk_options)
                
                # Adjust timestamps to global time
                for segment in chunk_result.get("segments", []):
                    segment["start"] += start_time
                    segment["end"] += start_time
                    all_segments.append(segment)
                
                # Append text
                chunk_text = chunk_result.get("text", "").strip()
                if chunk_text:
                    if full_text:
                        full_text += " " + chunk_text
                    else:
                        full_text = chunk_text
                
                logger.info(f"✅ Chunk {i+1} completed: {len(chunk_result.get('segments', []))} segments")
                
            except subprocess.CalledProcessError as e:
                logger.error(f"❌ Failed to extract chunk {i+1}: {e}")
                continue
            except Exception as e:
                logger.error(f"❌ Failed to transcribe chunk {i+1}: {e}")
                continue
            finally:
                # Clean up temporary file
                if os.path.exists(temp_chunk_path):
                    os.unlink(temp_chunk_path)
        
        # Combine results
        combined_result = {
            "text": full_text,
            "segments": all_segments,
            "language": transcribe_options.get("language", "en")
        }
        
        logger.info(f"🎉 Chunked transcription completed: {len(all_segments)} total segments")
        return combined_result
    
    def _process_segments(self, segments: List[Dict], speaker_data: Optional[Dict] = None) -> List[Dict]:
        """
        Process transcription segments and add speaker information if available.
        
        Args:
            segments: List of transcription segments from Whisper
            speaker_data: Optional speaker identification data
            
        Returns:
            Processed segments with additional information
        """
        processed_segments = []
        
        for i, segment in enumerate(segments):
            # Extract basic segment data
            start = segment["start"]
            end = segment["end"]
            text = segment["text"].strip()
            
            # Find speaker if speaker data is available
            speaker = None
            confidence = 1.0
            if speaker_data and "timeline" in speaker_data:
                speaker_info = self._find_speaker_at_time(speaker_data["timeline"], start)
                if speaker_info:
                    speaker = speaker_info.get("name")
                    confidence = speaker_info.get("confidence", 1.0)
            
            # Create processed segment
            processed_segment = {
                "id": i,
                "start": start,
                "end": end,
                "text": text,
                "duration": end - start,
                "speaker": speaker,
                "confidence": confidence
            }
            
            processed_segments.append(processed_segment)
        
        return processed_segments
    
    def _find_speaker_at_time(self, timeline: List[Dict], timestamp: float) -> Optional[Dict]:
        """
        Find the speaker at a specific timestamp in the timeline.
        
        Args:
            timeline: List of speaker appearances with timestamps
            timestamp: Time to find speaker for
            
        Returns:
            Speaker information or None if not found
        """
        for entry in timeline:
            if entry.get("start_time") <= timestamp <= entry.get("end_time"):
                return {
                    "name": entry.get("speaker_name"),
                    "confidence": entry.get("confidence", 1.0)
                }
        return None
    
    def search_transcription(self, transcription: Dict, query: str) -> List[Dict]:
        """
        Search a transcription for specific text.
        
        Args:
            transcription: Transcription dictionary
            query: Search query
            
        Returns:
            List of matching segments with timestamps
        """
        query = query.lower()
        matches = []
        
        for segment in transcription.get("segments", []):
            if query in segment.get("text", "").lower():
                matches.append(segment)
                
        return matches
    
    def get_transcription_file(self, video_path: str) -> Optional[Path]:
        """
        Get the path to a transcription file for a video if it exists.
        
        Args:
            video_path: Path to the video file
            
        Returns:
            Path to the transcription file or None if not found
        """
        video_path = Path(video_path)
        transcription_file = self.output_dir / f"{video_path.stem}_transcription.json"
        
        if transcription_file.exists():
            return transcription_file
            
        return None
    
    def load_transcription(self, transcription_path: str) -> Dict:
        """
        Load a transcription from a file.
        
        Args:
            transcription_path: Path to the transcription file
            
        Returns:
            Transcription dictionary
        """
        with open(transcription_path, 'r') as f:
            return json.load(f)
