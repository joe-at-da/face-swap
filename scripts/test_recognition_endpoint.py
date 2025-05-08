#!/usr/bin/env python3
"""
Test script for the combined recognition endpoint.
This script authenticates with the API and then calls the combined recognition endpoint.
"""

import os
import sys
import json
import requests
import argparse
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test_recognition")

# Constants
API_BASE_URL = "http://localhost:8000/api/v1"
DEFAULT_USERNAME = "test@example.com"
DEFAULT_PASSWORD = "testpassword"

def authenticate(username: str, password: str) -> str:
    """Authenticate with the API and return the access token."""
    auth_url = f"{API_BASE_URL}/auth/login"
    
    data = {
        "username": username,
        "password": password
    }
    
    logger.info(f"Authenticating as {username}")
    response = requests.post(auth_url, data=data)
    
    if response.status_code != 200:
        logger.error(f"Authentication failed: {response.status_code} - {response.text}")
        raise Exception(f"Authentication failed: {response.status_code}")
    
    token_data = response.json()
    access_token = token_data.get("access_token")
    
    if not access_token:
        logger.error("No access token in response")
        raise Exception("No access token in response")
    
    logger.info("Authentication successful")
    return access_token

def test_combined_recognition(token: str, video_id: int, save_output: bool = True) -> dict:
    """Test the combined recognition endpoint."""
    url = f"{API_BASE_URL}/recognition/combined-recognition"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    data = {
        "video_id": video_id,
        "save_output": save_output
    }
    
    logger.info(f"Calling combined recognition endpoint for video ID: {video_id}")
    response = requests.post(url, headers=headers, json=data)
    
    if response.status_code != 200:
        logger.error(f"API call failed: {response.status_code} - {response.text}")
        return {"success": False, "error": response.text, "status_code": response.status_code}
    
    result = response.json()
    logger.info(f"API call successful: {json.dumps(result, indent=2)}")
    return result

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description='Test the combined recognition endpoint')
    parser.add_argument('--video-id', '-v', type=int, required=True, help='ID of the video to process')
    parser.add_argument('--username', '-u', default=DEFAULT_USERNAME, help='Username for authentication')
    parser.add_argument('--password', '-p', default=DEFAULT_PASSWORD, help='Password for authentication')
    parser.add_argument('--no-save', action='store_true', help='Do not save output files')
    args = parser.parse_args()
    
    try:
        # Authenticate
        token = authenticate(args.username, args.password)
        
        # Test combined recognition
        result = test_combined_recognition(token, args.video_id, not args.no_save)
        
        # Print results
        print("\nCombined Recognition Results:")
        if result.get("success", False):
            print("✅ Recognition successful")
            
            # Speaker identification results
            if "speaker_identification" in result:
                speaker_data = result["speaker_identification"]
                print("\nSpeaker Identification:")
                print(f"Success: {speaker_data.get('success', False)}")
                if speaker_data.get("results"):
                    speakers = speaker_data["results"].get("speakers", [])
                    print(f"Total speakers: {len(speakers)}")
                    for i, speaker in enumerate(speakers, 1):
                        print(f"  {i}. {speaker.get('name')} (confidence: {speaker.get('confidence'):.2f})")
                        print(f"     Time: {speaker.get('start_time'):.2f}s - {speaker.get('end_time'):.2f}s")
                
                if speaker_data.get("output_file"):
                    print(f"Output file: {speaker_data['output_file']}")
            
            # Transcription results
            if "transcription" in result:
                transcript_data = result["transcription"]
                print("\nTranscription:")
                print(f"Success: {transcript_data.get('success', False)}")
                if transcript_data.get("transcript"):
                    # Show first 200 characters of transcript
                    transcript = transcript_data["transcript"]
                    preview = transcript[:200] + "..." if len(transcript) > 200 else transcript
                    print(f"Transcript preview: {preview}")
                
                if transcript_data.get("output_file"):
                    print(f"Output file: {transcript_data['output_file']}")
        else:
            print("❌ Recognition failed")
            print(f"Error: {result.get('error', 'Unknown error')}")
        
        return 0
    
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
