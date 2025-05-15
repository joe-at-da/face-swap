#!/usr/bin/env python3
"""
Voice Profile Manager for Parliament TV Audio

This script manages voice profiles for known speakers (MPs) to enable
speaker recognition in Parliament TV audio files.

Usage:
    python voice_profile_manager.py [--update] [--sample SAMPLE_FILE --speaker SPEAKER_NAME]

Example:
    python voice_profile_manager.py --update
    python voice_profile_manager.py --sample /app/data/samples/mp_john_smith.mp3 --speaker "John Smith"
"""

import os
import sys
import json
import logging
import argparse
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("voice_profile_manager")

# Constants
VOICE_PROFILES_DIR = Path("/app/data/voice_profiles")
VOICE_ENCODINGS_FILE = Path("/app/data/voice_encodings.json")
VOICE_SAMPLES_DIR = Path("/app/data/voice_samples")

class VoiceProfileManager:
    """Class to manage voice profiles for speaker recognition."""
    
    def __init__(self, voice_encodings_file: Path = VOICE_ENCODINGS_FILE):
        """Initialize the voice profile manager."""
        self.voice_encodings_file = voice_encodings_file
        self.voice_profiles_dir = VOICE_PROFILES_DIR
        self.voice_samples_dir = VOICE_SAMPLES_DIR
        
        # Create directories if they don't exist
        self.voice_profiles_dir.mkdir(parents=True, exist_ok=True)
        self.voice_samples_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize voice embeddings
        self.known_voice_encodings = []
        self.known_voice_names = []
        self.known_voice_metadata = []
        
        # Load existing voice profiles
        self.load_voice_database()
    
    def load_voice_database(self) -> bool:
        """Load the voice encodings database."""
        if not self.voice_encodings_file.exists():
            logger.warning(f"Voice encodings file not found: {self.voice_encodings_file}")
            return False
        
        try:
            with open(self.voice_encodings_file, 'r') as f:
                data = json.load(f)
                
            self.known_voice_encodings = [np.array(enc) for enc in data.get('encodings', [])]
            self.known_voice_names = data.get('names', [])
            self.known_voice_metadata = data.get('metadata', [{}] * len(self.known_voice_names))
            
            logger.info(f"Loaded {len(self.known_voice_encodings)} voice encodings")
            return True
            
        except Exception as e:
            logger.error(f"Error loading voice database: {e}")
            return False
    
    def save_voice_database(self) -> bool:
        """Save the voice encodings database."""
        try:
            # Convert numpy arrays to lists for JSON serialization
            encodings_list = [enc.tolist() if isinstance(enc, np.ndarray) else enc 
                             for enc in self.known_voice_encodings]
            
            voice_data = {
                "encodings": encodings_list,
                "names": self.known_voice_names,
                "metadata": self.known_voice_metadata,
                "updated_at": datetime.now().isoformat()
            }
            
            # Save the database
            with open(self.voice_encodings_file, 'w') as f:
                json.dump(voice_data, f, indent=2)
            
            logger.info(f"Voice database saved with {len(self.known_voice_encodings)} encodings")
            return True
            
        except Exception as e:
            logger.error(f"Error saving voice database: {e}")
            return False
    
    def add_voice_profile(self, audio_path: Path, speaker_name: str, metadata: Dict = None) -> bool:
        """
        Add a voice profile for a speaker from an audio sample.
        
        Args:
            audio_path: Path to the audio sample
            speaker_name: Name of the speaker
            metadata: Additional metadata for the speaker
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not audio_path.exists():
            logger.error(f"Audio sample not found: {audio_path}")
            return False
        
        try:
            # Generate voice embedding
            embedding = self.extract_voice_embedding(audio_path)
            if embedding is None:
                logger.error(f"Failed to extract voice embedding from {audio_path}")
                return False
            
            # Add to database
            self.known_voice_encodings.append(embedding)
            self.known_voice_names.append(speaker_name)
            self.known_voice_metadata.append(metadata or {})
            
            # Save a copy of the sample to the voice samples directory
            sample_path = self.voice_samples_dir / f"{speaker_name.replace(' ', '_').lower()}.mp3"
            try:
                import shutil
                shutil.copy2(audio_path, sample_path)
                logger.info(f"Saved voice sample to {sample_path}")
            except Exception as e:
                logger.warning(f"Failed to save voice sample: {e}")
            
            # Save the updated database
            self.save_voice_database()
            
            logger.info(f"Added voice profile for {speaker_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding voice profile: {e}")
            return False
    
    def extract_voice_embedding(self, audio_path: Path) -> Optional[np.ndarray]:
        """
        Extract a voice embedding from an audio sample.
        
        Args:
            audio_path: Path to the audio sample
            
        Returns:
            np.ndarray: Voice embedding or None if extraction failed
        """
        try:
            # Check if the audio file exists
            if not audio_path.exists():
                logger.error(f"Audio file not found: {audio_path}")
                return None
            
            # Import required libraries
            try:
                import numpy as np
                import librosa
                import torch
                import torchaudio
                from scipy.spatial.distance import cosine
                logger.info("Successfully imported required libraries for voice embedding extraction")
            except ImportError as e:
                logger.error(f"Failed to import required libraries: {e}")
                return None
            
            # Load the audio file
            try:
                # Load audio with librosa
                audio, sr = librosa.load(str(audio_path), sr=16000, mono=True)
                logger.info(f"Loaded audio: {audio_path}, duration: {len(audio)/sr:.2f}s")
                
                # Check if the audio is too short
                if len(audio) < sr:  # Less than 1 second
                    logger.warning(f"Audio too short: {len(audio)/sr:.2f}s")
                    return None
                
                # Try to use a pre-trained model for speaker embedding if available
                try:
                    # Try to use speechbrain's speaker embedding model if available
                    try:
                        from speechbrain.pretrained import EncoderClassifier
                        # Initialize the speaker embedding model
                        speaker_model = EncoderClassifier.from_hparams(
                            source="speechbrain/spkrec-ecapa-voxceleb",
                            savedir="pretrained_models/spkrec-ecapa-voxceleb"
                        )
                        
                        # Convert audio to torch tensor
                        waveform = torch.tensor(audio).unsqueeze(0)
                        
                        # Extract the embedding
                        with torch.no_grad():
                            embeddings = speaker_model.encode_batch(waveform)
                            embedding = embeddings[0].squeeze().cpu().numpy()
                        
                        logger.info(f"Extracted voice embedding with speechbrain: {embedding.shape}")
                        return embedding
                    except Exception as sb_e:
                        logger.warning(f"Failed to use speechbrain model: {sb_e}")
                        # Fall back to basic features
                        pass
                    
                    # Try to use torchaudio's speaker embedding model if available
                    try:
                        import torchaudio.pipelines as pipelines
                        
                        # Initialize the speaker embedding model
                        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
                        speaker_model = pipelines.SpectrogramToSpeakerEmbedding.from_pretrained(
                            "speechbrain/spkrec-xvect-voxceleb"
                        ).to(device)
                        
                        # Convert audio to torch tensor and resample if needed
                        waveform = torch.tensor(audio).unsqueeze(0)
                        if sr != speaker_model.sample_rate:
                            waveform = torchaudio.functional.resample(
                                waveform, sr, speaker_model.sample_rate
                            )
                        
                        # Extract the embedding
                        with torch.no_grad():
                            embedding = speaker_model(waveform.to(device))
                            embedding = embedding.squeeze().cpu().numpy()
                        
                        logger.info(f"Extracted voice embedding with torchaudio: {embedding.shape}")
                        return embedding
                    except Exception as ta_e:
                        logger.warning(f"Failed to use torchaudio model: {ta_e}")
                        # Fall back to basic features
                        pass
                    
                except Exception as model_e:
                    logger.warning(f"Failed to use pre-trained models: {model_e}")
                
                # Fall back to basic audio features if pre-trained models are not available
                logger.info("Using basic audio features for voice embedding")
                
                # Extract MFCCs
                mfccs = librosa.feature.mfcc(y=audio, sr=sr, n_mfcc=40)
                mfcc_mean = np.mean(mfccs, axis=1)
                mfcc_std = np.std(mfccs, axis=1)
                
                # Extract spectral features
                spectral_centroid = librosa.feature.spectral_centroid(y=audio, sr=sr)
                spectral_mean = np.mean(spectral_centroid, axis=1)
                
                # Extract pitch features
                pitch, _ = librosa.core.piptrack(y=audio, sr=sr)
                pitch_mean = np.mean(pitch, axis=1)
                
                # Combine features
                features = np.concatenate([mfcc_mean, mfcc_std, spectral_mean, pitch_mean[:40]])
                
                # Normalize the features
                norm = np.linalg.norm(features)
                if norm > 0:
                    features = features / norm
                
                logger.info(f"Extracted voice embedding with {len(features)} dimensions using basic features")
                return features
                
            except Exception as e:
                logger.error(f"Error loading audio: {e}")
                return None
            
            
        except Exception as e:
            logger.error(f"Error in voice embedding extraction: {e}")
            return None
    
    def update_from_samples(self) -> bool:
        """
        Update the voice database from all samples in the voice samples directory.
        
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.voice_samples_dir.exists():
            logger.error(f"Voice samples directory not found: {self.voice_samples_dir}")
            return False
        
        # Reset the database
        self.known_voice_encodings = []
        self.known_voice_names = []
        self.known_voice_metadata = []
        
        # Process each sample
        success = True
        for sample_file in self.voice_samples_dir.glob("*.mp3"):
            try:
                # Extract speaker name from filename
                speaker_name = sample_file.stem.replace('_', ' ').title()
                
                # Add voice profile
                if not self.add_voice_profile(sample_file, speaker_name):
                    logger.warning(f"Failed to add voice profile for {speaker_name}")
                    success = False
                
            except Exception as e:
                logger.error(f"Error processing sample {sample_file}: {e}")
                success = False
        
        # Save the database
        if not self.save_voice_database():
            logger.error("Failed to save voice database")
            success = False
        
        return success
    
    def match_voice(self, embedding: np.ndarray, threshold: float = 0.7) -> Tuple[Optional[str], float]:
        """
        Match a voice embedding with known voices.
        
        Args:
            embedding: Voice embedding to match
            threshold: Similarity threshold (0-1)
            
        Returns:
            Tuple[str, float]: Speaker name and confidence, or (None, 0.0) if no match
        """
        if not self.known_voice_encodings:
            logger.warning("No known voice encodings available for matching")
            return None, 0.0
        
        try:
            # Import required libraries
            try:
                import torch
                from scipy.spatial.distance import cosine
                logger.info("Successfully imported required libraries for voice matching")
            except ImportError as e:
                logger.error(f"Failed to import required libraries: {e}")
                return None, 0.0
            
            # Calculate cosine similarity with each known embedding
            similarities = []
            for known_embedding in self.known_voice_encodings:
                # Calculate cosine similarity (1 - cosine distance)
                similarity = 1.0 - cosine(embedding, known_embedding)
                similarities.append(similarity)
            
            # Find the best match
            if not similarities:
                return None, 0.0
                
            best_idx = np.argmax(similarities)
            best_similarity = similarities[best_idx]
            
            # Check if the similarity is above the threshold
            if best_similarity >= threshold:
                return self.known_voice_names[best_idx], float(best_similarity)
            else:
                return None, float(best_similarity)
            
        except Exception as e:
            logger.error(f"Error matching voice: {e}")
            return None, 0.0

def check_dependencies():
    """Check if required dependencies are installed."""
    try:
        # Check for required Python packages
        import importlib
        
        required_packages = [
            "torch", 
            "torchaudio", 
            "pyannote.audio", 
            "numpy", 
            "scipy"
        ]
        
        missing_packages = []
        for package in required_packages:
            try:
                importlib.import_module(package)
            except ImportError:
                missing_packages.append(package)
        
        if missing_packages:
            logger.warning(f"Missing required packages: {', '.join(missing_packages)}")
            return False
        
        return True
    except Exception as e:
        logger.error(f"Error checking dependencies: {e}")
        return False

def main():
    """Main function to run the voice profile manager."""
    parser = argparse.ArgumentParser(description="Voice Profile Manager for Parliament TV Audio")
    parser.add_argument("--update", action="store_true", help="Update the voice database from samples")
    parser.add_argument("--sample", help="Path to a voice sample to add")
    parser.add_argument("--speaker", help="Name of the speaker for the sample")
    parser.add_argument("--debug", "-d", action="store_true", help="Enable debug mode with extra logging")
    args = parser.parse_args()
    
    try:
        # Set up logging based on debug flag
        if args.debug:
            logging.basicConfig(level=logging.DEBUG)
            print("Debug mode enabled - verbose logging will be shown")
        
        # Check dependencies
        if not check_dependencies():
            logger.error("Required dependencies are missing. Please install them first.")
            return 1
        
        # Create the voice profile manager
        manager = VoiceProfileManager()
        
        # Update the database from samples
        if args.update:
            print("Updating voice database from samples...")
            result = manager.update_from_samples()
            print(f"Update result: {result}")
            return 0 if result else 1
        
        # Add a sample
        if args.sample and args.speaker:
            sample_path = Path(args.sample)
            print(f"Adding voice profile for {args.speaker} from {sample_path}...")
            result = manager.add_voice_profile(sample_path, args.speaker)
            print(f"Add result: {result}")
            return 0 if result else 1
        
        # If no action specified, print help
        if not (args.update or (args.sample and args.speaker)):
            parser.print_help()
        
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
