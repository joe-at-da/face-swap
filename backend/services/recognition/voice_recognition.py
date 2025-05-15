"""
Voice Recognition Service for Parliament TV Audios

This service provides voice recognition capabilities for Parliament TV audio files,
integrating with the existing scripts for speaker identification based on voice.
"""

import os
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
            "--format", "txt"  # Explicitly specify format
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
                stdout, stderr = process.communicate(timeout=600)  # 10 minute timeout (increased from 5)
                logger.info(f"Transcription process stdout: {stdout}")
                if stderr:
                    logger.warning(f"Transcription process stderr: {stderr}")
            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate()
                logger.error("Transcription process timed out after 10 minutes")
                return {
                    "success": False,
                    "error": "Transcription process timed out after 10 minutes",
                    "output_file": None,
                    "message": "Transcription failed due to timeout. The audio file may be too large or complex.",
                    "transcript": "[Transcription failed: Process timed out after 10 minutes]"
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
                "error": str(e),
                "output_file": None,
                "results_file": None
            }
    
    def combine_transcription_with_speakers(self, transcription_path: str, speaker_results_path: str, output_file: Optional[str] = None) -> Dict:
        """
        Combine transcription with speaker identification results.
        
{{ ... }}
            transcription_path: Path to the transcription file
            speaker_results_path: Path to the speaker identification results file
            output_file: Optional path to save the combined output
            
        Returns:
            Dict with combined results
        """
        logger.info(f"Combining transcription with speaker identification")
        
        try:
            # Load the transcription file
            if not os.path.exists(transcription_path):
                return {
                    "success": False,
                    "error": f"Transcription file not found: {transcription_path}"
                }
            
            # Load the speaker identification results file
            if not os.path.exists(speaker_results_path):
                return {
                    "success": False,
                    "error": f"Speaker identification results file not found: {speaker_results_path}"
                }
            
            # Load the transcription
            with open(transcription_path, 'r') as f:
                transcription = f.read()
            
            # Load the speaker identification results
            with open(speaker_results_path, 'r') as f:
                speaker_results = json.load(f)
            
            # Process and combine the results
            # This is a placeholder for the actual implementation
            # The actual implementation would depend on the format of the transcription and speaker results
            combined_results = {
                "transcription": transcription,
                "speakers": speaker_results
            }
            
            # Save the combined results if output_file is provided
            if output_file:
                os.makedirs(os.path.dirname(output_file), exist_ok=True)
                with open(output_file, 'w') as f:
                    json.dump(combined_results, f, indent=2)
            
            return {
                "success": True,
                "output_file": output_file,
                "results": make_json_serializable(combined_results),
                "message": "Transcription combined with speaker identification successfully"
            }
            
        except Exception as e:
            logger.error(f"Error combining transcription with speaker identification: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "output_file": None
            }
