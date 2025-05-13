#!/usr/bin/env python3
"""
Test script for the combined recognition endpoint that waits for results.
This script:
1. Authenticates with the API
2. Calls the combined recognition endpoint
3. Polls the status endpoint until the process completes
4. Retrieves and displays the results
"""

import os
import sys
import json
import time
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
POLL_INTERVAL = 5  # seconds

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

def start_recognition(token: str, video_id: int, save_output: bool = True) -> dict:
    """Start the combined recognition process."""
    url = f"{API_BASE_URL}/recognition/combined-recognition"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    data = {
        "video_id": video_id,
        "save_output": save_output
    }
    
    logger.info(f"Starting combined recognition for video ID: {video_id}")
    response = requests.post(url, headers=headers, json=data)
    
    if response.status_code != 200:
        logger.error(f"API call failed: {response.status_code} - {response.text}")
        return {"success": False, "error": response.text, "status_code": response.status_code}
    
    result = response.json()
    logger.info(f"Recognition started: {json.dumps(result, indent=2)}")
    return result

def get_recognition_status(token: str, video_id: int, detailed: bool = True) -> dict:
    """Get the status of the recognition process."""
    if detailed:
        url = f"{API_BASE_URL}/recognition/detailed-status/{video_id}"
    else:
        url = f"{API_BASE_URL}/recognition/recognition-status/{video_id}"
    
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    try:
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            logger.error(f"Status check failed: {response.status_code} - {response.text}")
            return {"success": False, "error": response.text, "status_code": response.status_code}
        
        # Parse the JSON response
        try:
            result = response.json()
            # Ensure we have a proper dictionary
            if not isinstance(result, dict):
                logger.error(f"Unexpected response format: {result}")
                return {"success": False, "error": "Unexpected response format", "raw_response": result}
            return result
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            return {"success": False, "error": f"JSON parse error: {e}", "raw_response": response.text}
    except Exception as e:
        logger.error(f"Error getting recognition status: {e}")
        return {"success": False, "error": str(e)}

def get_capture_data(token: str, video_id: int) -> dict:
    """Get the capture data including recognition results."""
    url = f"{API_BASE_URL}/capture/{video_id}"
    
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    try:
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            logger.error(f"Failed to get capture data: {response.status_code} - {response.text}")
            return {"success": False, "error": response.text, "status_code": response.status_code}
        
        try:
            result = response.json()
            logger.info(f"Got capture data for video ID {video_id}")
            return result
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse capture data JSON: {e}")
            return {"success": False, "error": f"JSON parse error: {e}", "raw_response": response.text}
    except Exception as e:
        logger.error(f"Error getting capture data: {e}")
        return {"success": False, "error": str(e)}

def wait_for_recognition_completion(token: str, video_id: int, timeout: int = 300) -> dict:
    """Wait for the recognition process to complete and return the final status."""
    logger.info(f"Waiting for recognition to complete (timeout: {timeout}s)")
    
    start_time = time.time()
    last_progress = -1
    
    while time.time() - start_time < timeout:
        try:
            status = get_recognition_status(token, video_id, detailed=True)
            
            if not status.get("success", False):
                logger.error(f"Failed to get status: {status.get('error', 'Unknown error')}")
                time.sleep(POLL_INTERVAL)
                continue
            
            # Handle different response formats
            status_info = status.get("status", {})
            if not isinstance(status_info, dict):
                logger.error(f"Unexpected status format: {status_info}")
                time.sleep(POLL_INTERVAL)
                continue
                
            current_status = status_info.get("status")
            progress_data = status_info.get("progress", {})
            
            # Log the current status
            logger.info(f"Current recognition status: {current_status}")
            
            # Get completion percentage if available
            completion_percentage = 0
            if isinstance(progress_data, dict):
                completion_percentage = progress_data.get("completion_percentage", 0)
                if completion_percentage != last_progress:
                    last_progress = completion_percentage
                    logger.info(f"Recognition progress: {completion_percentage}% - Status: {current_status}")
            
            # Check if process is complete
            if current_status == "completed":
                logger.info("Recognition process completed successfully")
                return status
            elif current_status == "failed" or current_status == "error":
                error_msg = "Unknown error"
                if isinstance(progress_data, dict):
                    error_msg = progress_data.get("error", "Unknown error")
                logger.error(f"Recognition process failed: {error_msg}")
                return status
            
            # Print current step if available
            if isinstance(progress_data, dict) and "current_step" in progress_data:
                current_step = progress_data.get("current_step")
                logger.info(f"Current step: {current_step}")
        except Exception as e:
            logger.error(f"Error checking recognition status: {e}")
        
        time.sleep(POLL_INTERVAL)
    
    logger.error(f"Recognition timed out after {timeout} seconds")
    return {"success": False, "error": "Timeout", "status": {"status": "timeout"}}

def display_recognition_results(results: dict):
    """Display the recognition results in a readable format."""
    if not results:
        print("No results available")
        return
    
    print("\n===== RECOGNITION RESULTS =====")
    
    # Try to parse the results if they're a string
    if isinstance(results, str):
        try:
            results = json.loads(results)
        except json.JSONDecodeError:
            print("Failed to parse results JSON")
            print(f"Raw results: {results}")
            return
    
    # Speaker identification results
    if "speaker_identification" in results:
        speaker_data = results["speaker_identification"]
        print("\n----- SPEAKER IDENTIFICATION -----")
        print(f"Success: {speaker_data.get('success', False)}")
        
        if speaker_data.get("results"):
            speakers = speaker_data["results"].get("speakers", [])
            segments = speaker_data["results"].get("segments", [])
            
            print(f"Total speakers identified: {len(speakers)}")
            for i, speaker in enumerate(speakers, 1):
                print(f"  {i}. {speaker.get('name')} (confidence: {speaker.get('confidence', 0):.2f})")
            
            print(f"\nTotal segments: {len(segments)}")
            for i, segment in enumerate(segments[:5], 1):  # Show first 5 segments
                print(f"  {i}. Speaker: {segment.get('speaker', 'Unknown')}")
                print(f"     Time: {segment.get('start', 0):.2f}s - {segment.get('end', 0):.2f}s")
                if segment.get('text'):
                    print(f"     Text: \"{segment.get('text')}\"")
            
            if len(segments) > 5:
                print(f"  ... and {len(segments) - 5} more segments")
        
        if speaker_data.get("message"):
            print(f"Message: {speaker_data['message']}")
    
    # Transcription results
    if "transcription" in results:
        transcript_data = results["transcription"]
        print("\n----- TRANSCRIPTION -----")
        print(f"Success: {transcript_data.get('success', False)}")
        
        if transcript_data.get("transcript"):
            transcript = transcript_data["transcript"]
            print("\nTranscript:")
            print("-" * 50)
            print(transcript)
            print("-" * 50)
        
        if transcript_data.get("message"):
            print(f"Message: {transcript_data['message']}")
    
    # Results summary if available
    if "results_summary" in results:
        summary = results["results_summary"]
        print("\n----- RESULTS SUMMARY -----")
        
        if summary.get("transcript_text"):
            print("\nTranscript Summary:")
            print("-" * 50)
            print(summary["transcript_text"])
            print("-" * 50)
        
        if summary.get("speaker_identification_message"):
            print(f"Speaker ID Message: {summary['speaker_identification_message']}")
        
        if summary.get("transcription_message"):
            print(f"Transcription Message: {summary['transcription_message']}")

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description='Test the combined recognition endpoint with results')
    parser.add_argument('--video-id', '-v', type=int, required=True, help='ID of the video to process')
    parser.add_argument('--username', '-u', default=DEFAULT_USERNAME, help='Username for authentication')
    parser.add_argument('--password', '-p', default=DEFAULT_PASSWORD, help='Password for authentication')
    parser.add_argument('--no-save', action='store_true', help='Do not save output files')
    parser.add_argument('--timeout', '-t', type=int, default=300, help='Timeout in seconds (default: 300)')
    parser.add_argument('--skip-start', '-s', action='store_true', help='Skip starting the recognition process (only check status)')
    parser.add_argument('--debug', '-d', action='store_true', help='Show debug information')
    args = parser.parse_args()
    
    # Set debug level if requested
    if args.debug:
        logger.setLevel(logging.DEBUG)
    
    try:
        # Authenticate
        token = authenticate(args.username, args.password)
        
        # Start recognition if not skipped
        if not args.skip_start:
            start_result = start_recognition(token, args.video_id, not args.no_save)
            if not isinstance(start_result, dict) or not start_result.get("success", False):
                error_msg = "Unknown error"
                if isinstance(start_result, dict):
                    error_msg = start_result.get('error', 'Unknown error')
                print(f"Failed to start recognition: {error_msg}")
                return 1
        
        # Wait for recognition to complete
        final_status = wait_for_recognition_completion(token, args.video_id, args.timeout)
        
        # Check if recognition completed successfully
        status_info = {}
        if isinstance(final_status, dict):
            status_info = final_status.get("status", {})
        
        if isinstance(final_status, dict) and final_status.get("success", False) and \
           isinstance(status_info, dict) and status_info.get("status") == "completed":
            # Get the capture data with recognition results
            capture_data = get_capture_data(token, args.video_id)
            
            if isinstance(capture_data, dict) and "recognition_results" in capture_data:
                # Display the recognition results
                display_recognition_results(capture_data["recognition_results"])
                return 0
            else:
                print("No recognition results found in capture data")
                if args.debug and isinstance(capture_data, dict):
                    print("Capture data:")
                    print(json.dumps(capture_data, indent=2))
                return 1
        else:
            print(f"Recognition did not complete successfully")
            if args.debug:
                print("Final status:")
                print(json.dumps(final_status, indent=2) if isinstance(final_status, dict) else final_status)
            return 1
    
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
