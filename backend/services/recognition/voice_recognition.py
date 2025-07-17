"""
Voice Recognition Service for Parliament TV Audios

This service provides voice recognition capabilities for Parliament TV audio files,
integrating with the existing scripts for speaker identification based on voice.
"""

import os
import sys
import json
import logging
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from backend.core.config import settings
from backend.services.utils import make_json_serializable

# Set up logging
logger = logging.getLogger(__name__)

class VoiceRecognitionService:
    """Service for voice recognition in Parliament TV audio files."""
    
    def __init__(self):
        """Initialize the voice recognition service."""
        self.base_dir = Path(os.environ.get('DATA_DIR', '/app/data'))
        self.voice_profiles_dir = self.base_dir / "voice_profiles"
        self.scripts_dir = Path("/app/scripts")
        
        # Create directories if they don't exist
        self.voice_profiles_dir.mkdir(parents=True, exist_ok=True)
        
    def transcribe_audio(self, audio_path: str, output_file: Optional[str] = None) -> Dict:
        """
        Transcribe audio file using Whisper.
        
        Args:
            audio_path: Path to the audio file
            output_file: Optional path to save the output transcript
            
        Returns:
            Dict with transcription results
        """
        logger.info(f"Transcribing audio: {audio_path}")
        
        # Check if audio file exists
        if not os.path.exists(audio_path):
            error_msg = f"Audio file not found: {audio_path}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "output_file": None,
                "message": "Audio file not found. Please check the audio extraction process.",
                "transcript": "No audio file available for transcription."
            }
        
        # Check if the audio file has content (size > 0)
        audio_size = os.path.getsize(audio_path)
        logger.info(f"Audio file size: {audio_size} bytes")
        if audio_size == 0:
            error_msg = f"Audio file is empty (0 bytes): {audio_path}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "output_file": None,
                "message": "Audio file is empty. Please check the audio extraction process.",
                "transcript": "Empty audio file cannot be transcribed."
            }
        
        # Validate audio file with ffprobe to ensure it's a valid audio file
        try:
            ffprobe_cmd = [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "json",
                audio_path
            ]
            result = subprocess.run(ffprobe_cmd, capture_output=True, text=True, check=True)
            audio_info = json.loads(result.stdout)
            duration = float(audio_info.get('format', {}).get('duration', 0))
            logger.info(f"Audio duration: {duration} seconds")
            
            if duration <= 0:
                error_msg = f"Audio file has invalid duration: {duration} seconds"
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "output_file": None,
                    "message": "Audio file has invalid duration. Please check the audio extraction process.",
                    "transcript": "Invalid audio file cannot be transcribed."
                }
                
            # Check if this is a long audio file (over the threshold)
            # For long files, use the chunked transcription approach to avoid memory issues
            # Get threshold from environment variable or use default (30 minutes)
            long_audio_threshold = int(os.environ.get('LONG_AUDIO_THRESHOLD_SECONDS', 1800))  # Default: 30 minutes
            logger.info(f"Long audio threshold set to {long_audio_threshold} seconds")
            
            if duration > long_audio_threshold:
                logger.info(f"Long audio file detected ({duration} seconds). Using chunked transcription approach.")
                return self._transcribe_long_audio(audio_path, output_file, duration)
                
        except (subprocess.CalledProcessError, json.JSONDecodeError, ValueError) as e:
            error_msg = f"Failed to validate audio file: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "output_file": None,
                "message": "Failed to validate audio file. Please check the audio extraction process.",
                "transcript": "Invalid audio file cannot be transcribed."
            }
        
        # For regular-length audio files, use the standard approach
        return self._transcribe_standard_audio(audio_path, output_file)
    
    def _transcribe_long_audio(self, audio_path: str, output_file: Optional[str] = None, duration: float = 0) -> Dict:
        """
        Transcribe a long audio file using the chunked transcription approach.
        
        Args:
            audio_path: Path to the audio file
            output_file: Optional path to save the output transcript
            duration: Duration of the audio file in seconds
            
        Returns:
            Dict with transcription results
        """
        logger.info(f"Using chunked transcription for long audio file: {audio_path} ({duration} seconds)")
        
        # Import the chunked transcriber here to avoid circular imports
        sys.path.append(str(Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))))  # Add project root
        from scripts.chunked_transcription import ChunkedTranscriber
        
        try:
            # Initialize the chunked transcriber with appropriate settings
            # Use a smaller model size for better memory efficiency
            # Get chunk size from environment variable or use default (10 minutes)
            chunk_size = int(os.environ.get('AUDIO_CHUNK_SIZE_SECONDS', 600))  # Default: 10 minutes
            logger.info(f"Using audio chunk size of {chunk_size} seconds")
            
            # Check if we should include chunk markers in the transcript
            include_markers = os.environ.get('INCLUDE_CHUNK_MARKERS', '').lower() in ('true', '1', 'yes')
            logger.info(f"Including chunk markers in transcript: {include_markers}")
            
            transcriber = ChunkedTranscriber(model_size="tiny", chunk_size=chunk_size)
            
            # Transcribe the audio file
            result = transcriber.transcribe(audio_path, output_file, include_markers=include_markers)
            
            # Log the result
            if result["success"]:
                logger.info(f"Chunked transcription completed successfully")
                if "chunks" in result:
                    logger.info(f"Processed {len(result['chunks'])} chunks")
            else:
                logger.error(f"Chunked transcription failed: {result.get('error', 'Unknown error')}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in chunked transcription: {str(e)}")
            return {
                "success": False,
                "error": f"Error in chunked transcription: {str(e)}",
                "output_file": None,
                "message": "Transcription failed due to an error in the chunked transcription process.",
                "transcript": "[Transcription failed due to an unexpected error]"
            }
    
    def _transcribe_standard_audio(self, audio_path: str, output_file: Optional[str] = None) -> Dict:
        """
        Transcribe a standard-length audio file using the direct approach.
        
        Args:
            audio_path: Path to the audio file
            output_file: Optional path to save the output transcript
            
        Returns:
            Dict with transcription results
        """
        # Prepare the command
        script_path = self.scripts_dir / "parliament_transcription.py"
        
        # Check if script exists
        if not os.path.exists(script_path):
            error_msg = f"Transcription script not found: {script_path}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "output_file": None
            }
        
        # Ensure the output directory exists
        if output_file:
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        cmd = [
            "python",
            str(script_path),
            audio_path,
            "--input-type", "audio",
            "--format", "txt",  # Explicitly specify format
            "--language", "en"  # Explicitly specify English language
        ]
        
        if output_file:
            cmd.extend(["--output", output_file])
        
        logger.info(f"Running transcription command: {' '.join(cmd)}")
        
        try:
            # Execute the command with a timeout
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            try:
                stdout, stderr = process.communicate(timeout=1200)  # 20 minute timeout
                logger.info(f"Transcription process stdout: {stdout}")
                if stderr:
                    logger.warning(f"Transcription process stderr: {stderr}")
            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate()
                logger.error("Transcription process timed out after 20 minutes")
                return {
                    "success": False,
                    "error": "Transcription process timed out after 20 minutes",
                    "output_file": None,
                    "message": "Transcription failed due to timeout. The audio file may be too large or complex.",
                    "transcript": "[Transcription failed: Process timed out after 20 minutes]"
                }
            
            # Check if the process was successful
            if process.returncode != 0:
                # Check for specific error messages
                error_msg = stderr.strip()
                logger.error(f"Transcription process returned error code {process.returncode}")
                logger.error(f"STDERR: {error_msg}")
                logger.error(f"STDOUT: {stdout.strip()}")
                
                if "Loading Whisper model" in stderr:
                    error_msg = "Failed to load Whisper model. The model may be corrupted or unavailable."
                    logger.error(f"Transcription failed: {error_msg}")
                    # This is a critical error that needs to be fixed
                    return {
                        "success": False,
                        "error": error_msg,
                        "output_file": None,
                        "message": "Transcription failed due to Whisper model loading issues. Please check the model installation.",
                        "transcript": "[Transcription failed: Unable to load Whisper model]"
                    }
                
                logger.error(f"Transcription failed: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg,
                    "output_file": None,
                    "message": "Transcription failed due to an error. Please check the logs for details.",
                    "transcript": "[Transcription failed: " + error_msg + "]"
                }
            
            # Parse the output to get the output file path
            output_path = None
            for line in stdout.splitlines():
                if "Transcript saved to:" in line:
                    output_path = line.split("Transcript saved to:", 1)[1].strip()
                    logger.info(f"Found transcript path in output: {output_path}")
                    break
            
            # If no output path was found in stdout, check if output_file was provided
            if not output_path and output_file:
                output_path = output_file
                logger.info(f"Using provided output file path: {output_path}")
            
            # Load the transcript file if it exists
            transcript = ""
            if output_path and os.path.exists(output_path):
                try:
                    with open(output_path, 'r') as f:
                        transcript = f.read()
                    logger.info(f"Successfully loaded transcript from {output_path}, length: {len(transcript)} characters")
                except Exception as e:
                    logger.error(f"Error loading transcript file: {str(e)}")
            elif not output_path:
                logger.warning("No transcript output path found in command output")
            elif not os.path.exists(output_path):
                logger.warning(f"Transcript file not found at expected path: {output_path}")
            
            # If we have no transcript but the process completed successfully, this is suspicious
            if not transcript and process.returncode == 0:
                logger.warning("Process completed successfully but no transcript was generated")
                
                # Check if there are any .txt files in the output directory that might be our transcript
                if output_path:
                    output_dir = os.path.dirname(output_path)
                    txt_files = [f for f in os.listdir(output_dir) if f.endswith('.txt') and os.path.getsize(os.path.join(output_dir, f)) > 0]
                    
                    if txt_files:
                        # Use the most recently modified file
                        newest_file = max(txt_files, key=lambda f: os.path.getmtime(os.path.join(output_dir, f)))
                        newest_path = os.path.join(output_dir, newest_file)
                        logger.info(f"Found potential transcript file: {newest_path}")
                        
                        try:
                            with open(newest_path, 'r') as f:
                                transcript = f.read()
                            logger.info(f"Loaded transcript from alternative file, length: {len(transcript)} characters")
                            output_path = newest_path
                        except Exception as e:
                            logger.error(f"Error loading alternative transcript file: {str(e)}")
                
                if not transcript:
                    return {
                        "success": False,
                        "error": "Transcription process completed but no transcript was generated",
                        "output_file": output_path,
                        "transcript": ""
                    }
            
            return {
                "success": True,
                "output_file": output_path,
                "transcript": transcript,
                "message": "Transcription completed successfully"
            }
            
        except Exception as e:
            logger.error(f"Error in transcription: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "output_file": None,
                "transcript": "[Transcription failed due to an unexpected error]"
            }
            
        except Exception as e:
            logger.error(f"Error in transcription: {str(e)}")
            return {
                "output_file": None
            }
    
    def identify_speakers_in_audio(self, audio_path: str, output_file: Optional[str] = None, model_size: str = "base") -> Dict:
        """
        Identify speakers in an audio file using voice recognition and diarization.
        
        Args:
            audio_path: Path to the audio file
            output_file: Optional path to save the output with speaker identification
            model_size: Size of the model to use (tiny, base, small, medium, large)
            
        Returns:
            Dict with identification results
        """
        logger.info(f"Identifying speakers in audio: {audio_path} with model size: {model_size}")
        
        # Prepare the command
        script_path = self.scripts_dir / "speaker_diarization.py"
        
        # Check if the script exists
        if not os.path.exists(script_path):
            error_msg = f"Speaker diarization script not found: {script_path}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "output_file": None,
                "results_file": None
            }
        
        # Build the command
        cmd = [
            "python",
            str(script_path),
            audio_path,
            "--model", model_size
        ]
        
        if output_file:
            cmd.extend(["--output", output_file])
        
        logger.info(f"Running command: {' '.join(cmd)}")
        
        try:
            # Execute the command
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            stdout, stderr = process.communicate()
            
            # Check if the process was successful
            if process.returncode != 0:
                logger.error(f"Speaker identification failed: {stderr}")
                return {
                    "success": False,
                    "error": stderr,
                    "output_file": None,
                    "results_file": None
                }
            
            # Parse the output to get the output file path and results file path
            output_path = None
            results_path = None
            
            for line in stdout.splitlines():
                if "Results saved to:" in line:
                    results_path = line.split(":", 1)[1].strip()
                    logger.info(f"Found results path: {results_path}")
                elif "Processed audio saved to:" in line:
                    output_path = line.split(":", 1)[1].strip()
                    logger.info(f"Found output path: {output_path}")
            
            # Load the results file if it exists
            results = {}
            if results_path and os.path.exists(results_path):
                try:
                    with open(results_path, 'r') as f:
                        results = json.load(f)
                    logger.info(f"Loaded diarization results: {len(results.get('segments', []))} segments, {len(results.get('speakers', {}))} speakers")
                    
                    # Check if we have any speakers
                    if 'speakers' in results and len(results['speakers']) == 0:
                        logger.warning("No speakers detected in the audio")
                except Exception as e:
                    logger.error(f"Error loading results file: {str(e)}")
            else:
                logger.warning(f"Results file not found or path is None: {results_path}")
            
            # Enhance the results with additional information
            enhanced_results = results.copy() if results else {}
            
            # Add summary information if not already present
            if "summary" not in enhanced_results:
                total_speakers = len(enhanced_results.get("speakers", {}))
                total_segments = len(enhanced_results.get("segments", []))
                total_duration = enhanced_results.get("processing_info", {}).get("total_duration", 0)
                
                enhanced_results["summary"] = {
                    "total_speakers": total_speakers,
                    "total_segments": total_segments,
                    "total_duration": total_duration,
                    "speakers_identified": any(s.get("matched", False) for s in enhanced_results.get("speakers", {}).values()),
                    "processed_at": datetime.now().isoformat()
                }
            
            return {
                "success": True,
                "output_file": output_path,
                "results_file": results_path,
                "results": make_json_serializable(enhanced_results),
                "message": "Speaker identification completed successfully"
            }
            
        except Exception as e:
            logger.error(f"Error in speaker identification: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def combine_transcription_with_speakers(self, transcription_path: Optional[str], speaker_results_path: str, output_file: Optional[str] = None) -> Dict:
        """
        Combine transcription data with speaker identification results.
        
        Args:
            transcription_path: Path to the transcription file (can be None)
            speaker_results_path: Path to the speaker identification results
            output_file: Optional path to save the combined output
            
        Returns:
            Dict with combined results
        """
        logger.info(f"Combining transcription with speaker identification: {transcription_path} + {speaker_results_path}")
        
        # Initialize transcription with empty structure
        transcription = {
            "text": "",
            "segments": []
        }
        
        # Load the transcription if path is provided
        if transcription_path:
            try:
                with open(transcription_path, 'r') as f:
                    try:
                        # First try to load as JSON
                        transcription = json.load(f)
                    except json.JSONDecodeError:
                        # If that fails, try to handle as text format
                        f.seek(0)  # Reset file pointer to beginning
                        text_content = f.read()
                        
                        # Create a simple JSON structure from the text
                        transcription = {
                            "text": text_content,
                            "segments": [{
                                "start": 0,
                                "end": 0,  # We don't have timing info in plain text
                                "text": text_content
                            }]
                        }
                        logger.info("Loaded transcription as plain text format")
            except Exception as e:
                logger.error(f"Error loading transcription: {str(e)}")
                # Continue with empty transcription instead of failing
                logger.warning("Continuing with empty transcription structure")
        else:
            logger.warning("No transcription path provided, using empty transcription structure")
            
        # Load the speaker identification results if provided
        speaker_results = {"segments": []}
        if speaker_results_path:
            try:
                with open(speaker_results_path, 'r') as f:
                    speaker_results = json.load(f)
            except Exception as e:
                logger.error(f"Error loading speaker identification results: {str(e)}")
                # Continue with empty speaker results instead of failing
                logger.warning("Continuing with empty speaker results")
        else:
            logger.warning("No speaker results path provided, using empty speaker segments")
        
        # Combine the results
        try:
            # Create a mapping of time ranges to speakers
            speaker_segments = speaker_results.get("segments", [])
            time_to_speaker = {}
            
            for segment in speaker_segments:
                start_time = segment.get("start_time", 0)
                end_time = segment.get("end_time", 0)
                speaker = segment.get("speaker", "")
                speaker_name = segment.get("speaker_name", speaker)
                
                # Add to the mapping
                time_to_speaker[(start_time, end_time)] = {
                    "speaker": speaker,
                    "name": speaker_name
                }
            
            # Add speaker information to each segment in the transcription
            segments = transcription.get("segments", [])
            
            for segment in segments:
                start = segment.get("start", 0)
                end = segment.get("end", 0)
                
                # Find the speaker for this segment
                speaker_found = False
                
                for (speaker_start, speaker_end), speaker_info in time_to_speaker.items():
                    # Check if there's an overlap
                    if max(start, speaker_start) <= min(end, speaker_end):
                        segment["speaker"] = speaker_info["speaker"]
                        segment["speaker_name"] = speaker_info["name"]
                        speaker_found = True
                        break
                
                if not speaker_found:
                    segment["speaker"] = "unknown"
                    segment["speaker_name"] = "Unknown"
            
            # Create the combined results
            combined_results = {
                "text": transcription.get("text", ""),
                "segments": segments,
                "speakers": speaker_results.get("speakers", {}),
                "language": transcription.get("language", "en"),
                "combined_at": datetime.now().isoformat()
            }
            
            # Save to output file if provided
            if output_file:
                with open(output_file, 'w') as f:
                    json.dump(combined_results, f, indent=2, default=str)
                logger.info(f"Combined results saved to: {output_file}")
            
            return {
                "success": True,
                "combined_results": combined_results,
                "output_file": output_file
            }
            
        except Exception as e:
            logger.error(f"Error combining transcription with speaker identification: {str(e)}")
            return {
                "success": False,
                "error": f"Error combining results: {str(e)}"
            }
    
    def combine_recognition_results(self, audio_path: str, video_path: str, transcription_path: Optional[str] = None, output_file: Optional[str] = None) -> Dict:
        """
        Combine audio-based speaker diarization with video-based facial recognition.
        
        Args:
            audio_path: Path to the audio file
            video_path: Path to the video file
            transcription_path: Optional path to the transcription file
            output_file: Optional path to save the combined output
            
        Returns:
            Dict with combined recognition results
        """
        logger.info(f"Combining audio and video recognition for: {audio_path} and {video_path}")
        
        try:
            # Step 1: Get audio-based speaker identification
            audio_results = self.identify_speakers_in_audio(audio_path)
            
            if not audio_results.get("success", False):
                logger.error(f"Failed to identify speakers in audio: {audio_results.get('error', 'Unknown error')}")
                return {
                    "success": False,
                    "error": f"Failed to identify speakers in audio: {audio_results.get('error', 'Unknown error')}"
                }
            
            # Step 2: Get video-based face recognition
            try:
                from backend.services.recognition.facial_recognition import FacialRecognitionService
                facial_service = FacialRecognitionService()
                video_results = facial_service.identify_speakers_in_video(video_path)
                
                if not video_results.get("success", False):
                    logger.warning(f"Failed to identify faces in video: {video_results.get('error', 'Unknown error')}")
                    logger.warning("Proceeding with audio-only results")
                    video_results = {"speakers": {}, "frames": []}
                
            except Exception as e:
                logger.warning(f"Error in facial recognition: {str(e)}")
                logger.warning("Proceeding with audio-only results")
                video_results = {"speakers": {}, "frames": []}
            
            # Step 3: Align and combine results
            combined_results = self._align_recognition_results(audio_results.get("results", {}), video_results)
            
            # Step 4: If transcription exists, add speaker information
            if transcription_path and os.path.exists(transcription_path):
                combined_transcription = self.combine_transcription_with_speakers(
                    transcription_path, 
                    audio_results.get("results_file", ""),
                    output_file=output_file
                )
                
                if combined_transcription.get("success", False):
                    combined_results["transcription"] = combined_transcription.get("combined_results", {})
                    logger.info("Successfully added transcription to combined results")
            
            # Save combined results if output file is provided
            if output_file:
                output_dir = os.path.dirname(output_file)
                if output_dir and not os.path.exists(output_dir):
                    os.makedirs(output_dir)
                
                with open(output_file, 'w') as f:
                    json.dump(combined_results, f, indent=2, default=str)
                logger.info(f"Combined recognition results saved to: {output_file}")
            
            return {
                "success": True,
                "combined_results": combined_results,
                "output_file": output_file
            }
            
        except Exception as e:
            logger.error(f"Error combining recognition results: {str(e)}")
            return {
                "success": False,
                "error": f"Error combining recognition results: {str(e)}"
            }
    
    def _align_recognition_results(self, audio_results: Dict, video_results: Dict) -> Dict:
        """
        Align and combine audio-based speaker diarization with video-based facial recognition.
        
        Args:
            audio_results: Results from audio-based speaker diarization
            video_results: Results from video-based facial recognition
            
        Returns:
            Dict with aligned and combined results
        """
        try:
            # Extract speakers from both results
            audio_speakers = audio_results.get("speakers", {})
            video_speakers = video_results.get("speakers", {})
            
            # Create a mapping of speaker IDs to names from video recognition
            video_id_to_name = {}
            for speaker_id, speaker_info in video_speakers.items():
                if speaker_info.get("name", "") != "Unknown":
                    video_id_to_name[speaker_id] = speaker_info.get("name")
            
            # Update audio speakers with video recognition information
            for speaker_id, speaker_info in audio_speakers.items():
                # If the speaker is already matched, skip
                if speaker_info.get("matched", False) and speaker_info.get("confidence", 0) > 0.7:
                    continue
                
                # Try to match with video speakers based on name
                speaker_name = speaker_info.get("name", "")
                for video_id, video_name in video_id_to_name.items():
                    if speaker_name == video_name:
                        # Update with video recognition info
                        speaker_info["matched_with_video"] = True
                        speaker_info["video_speaker_id"] = video_id
                        speaker_info["confidence"] = max(speaker_info.get("confidence", 0), 0.8)  # Boost confidence
                        break
            
            # Update audio segments with improved speaker information
            audio_segments = audio_results.get("segments", [])
            for segment in audio_segments:
                speaker_id = segment.get("speaker", "")
                if speaker_id in audio_speakers:
                    segment["speaker_name"] = audio_speakers[speaker_id].get("name", speaker_id)
                    segment["speaker_confidence"] = audio_speakers[speaker_id].get("confidence", 0.0)
                    segment["matched_with_video"] = audio_speakers[speaker_id].get("matched_with_video", False)
            
            # Create combined results
            combined_results = {
                "speakers": audio_speakers,
                "segments": audio_segments,
                "video_speakers": video_speakers,
                "video_frames": video_results.get("frames", []),
                "processing_info": {
                    "combined_at": datetime.now().isoformat(),
                    "audio_processing": audio_results.get("processing_info", {}),
                    "video_processing": video_results.get("processing_info", {})
                }
            }
            
            return combined_results
            
        except Exception as e:
            logger.error(f"Error aligning recognition results: {str(e)}")
            # Return a basic structure with the original results
            return {
                "audio_results": audio_results,
                "video_results": video_results,
                "error": str(e)
            }
