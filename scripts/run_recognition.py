#!/usr/bin/env python3
"""
Script to run and monitor the recognition process for Parliament TV captures.
This script provides real-time feedback on the progress of the recognition process.
"""

import os
import sys
import json
import time
import argparse
import requests
import logging
from datetime import datetime
from typing import Dict, Optional, Any
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("run_recognition")

# Constants
API_BASE_URL = "http://localhost:8000/api/v1"
DEFAULT_USERNAME = "test@example.com"
DEFAULT_PASSWORD = "testpassword"
POLL_INTERVAL = 5  # seconds

# Initialize rich console
console = Console()

def authenticate(username: str, password: str) -> str:
    """Authenticate with the API and return the access token."""
    auth_url = f"{API_BASE_URL}/auth/login"
    
    data = {
        "username": username,
        "password": password
    }
    
    console.print(f"[bold blue]Authenticating as[/bold blue] [yellow]{username}[/yellow]")
    response = requests.post(auth_url, data=data)
    
    if response.status_code != 200:
        console.print(f"[bold red]Authentication failed:[/bold red] {response.status_code} - {response.text}")
        raise Exception(f"Authentication failed: {response.status_code}")
    
    token_data = response.json()
    access_token = token_data.get("access_token")
    
    if not access_token:
        console.print("[bold red]No access token in response[/bold red]")
        raise Exception("No access token in response")
    
    console.print("[bold green]Authentication successful[/bold green]")
    return access_token

def start_recognition(token: str, video_id: int, save_output: bool = True) -> dict:
    """Start the recognition process for a video."""
    url = f"{API_BASE_URL}/recognition/combined-recognition"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    data = {
        "video_id": video_id,
        "save_output": save_output
    }
    
    console.print(f"[bold blue]Starting recognition process for video ID:[/bold blue] [yellow]{video_id}[/yellow]")
    response = requests.post(url, headers=headers, json=data)
    
    if response.status_code != 200:
        console.print(f"[bold red]API call failed:[/bold red] {response.status_code} - {response.text}")
        return {"success": False, "error": response.text, "status_code": response.status_code}
    
    result = response.json()
    console.print(f"[bold green]Recognition process started successfully[/bold green]")
    return result

def get_recognition_status(token: str, video_id: int) -> dict:
    """Get the status of a recognition process."""
    url = f"{API_BASE_URL}/recognition/recognition-status/{video_id}"
    
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        console.print(f"[bold red]Failed to get status:[/bold red] {response.status_code} - {response.text}")
        return {"success": False, "error": response.text, "status_code": response.status_code}
    
    return response.json()

def monitor_recognition_progress(token: str, video_id: int, timeout: int = 600) -> dict:
    """Monitor the progress of a recognition process with a rich progress display."""
    start_time = time.time()
    last_status = None
    completed_steps = set()
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TextColumn("[bold]{task.fields[status]}"),
        TimeElapsedColumn(),
        console=console
    ) as progress:
        overall_task = progress.add_task("[yellow]Overall Recognition Process", total=100, status="Starting...")
        
        while True:
            # Check if we've exceeded the timeout
            if time.time() - start_time > timeout:
                progress.update(overall_task, description="[red]Recognition Timed Out", status="TIMEOUT")
                console.print("[bold red]Recognition process timed out[/bold red]")
                return {"success": False, "error": "Timeout"}
            
            # Get the current status
            status_result = get_recognition_status(token, video_id)
            if not status_result.get("success", False):
                progress.update(overall_task, description="[red]Failed to get status", status="ERROR")
                console.print("[bold red]Failed to get recognition status[/bold red]")
                return status_result
            
            status = status_result.get("status", {})
            progress_data = status.get("progress", {})
            
            # Update the overall status
            current_status = status.get("status", "unknown")
            progress.update(overall_task, description=f"[yellow]Recognition Process: {current_status}", status=current_status.upper())
            
            # Display steps
            steps = progress_data.get("steps", [])
            for step in steps:
                step_name = step.get("name")
                step_status = step.get("status")
                
                # Create a new task for this step if we haven't seen it before
                if step_name not in completed_steps and step_status == "completed":
                    completed_steps.add(step_name)
                    console.print(f"[green]✓ Completed step:[/green] {step_name}")
                elif step_name not in completed_steps and step_status == "started":
                    console.print(f"[blue]→ Started step:[/blue] {step_name}")
            
            # Check if the process is complete or has an error
            if current_status == "completed":
                progress.update(overall_task, completed=100, status="COMPLETED")
                console.print("[bold green]Recognition process completed successfully[/bold green]")
                return status_result
            elif current_status == "error":
                progress.update(overall_task, description="[red]Recognition Failed", status="ERROR")
                error_message = progress_data.get("error", "Unknown error")
                console.print(f"[bold red]Recognition process failed:[/bold red] {error_message}")
                return status_result
            
            # Update progress percentage based on steps completed
            if steps:
                completed_count = sum(1 for step in steps if step.get("status") == "completed")
                progress_percentage = min(int((completed_count / len(steps)) * 100), 99)
                progress.update(overall_task, completed=progress_percentage)
            
            # Save the last status
            last_status = status
            
            # Wait before polling again
            time.sleep(POLL_INTERVAL)

def display_recognition_results(token: str, video_id: int) -> None:
    """Display the results of a completed recognition process."""
    status_result = get_recognition_status(token, video_id)
    if not status_result.get("success", False):
        console.print("[bold red]Failed to get recognition results[/bold red]")
        return
    
    status = status_result.get("status", {})
    if status.get("status") != "completed":
        console.print("[bold yellow]Recognition process is not completed yet[/bold yellow]")
        return
    
    # Get the recognition results
    url = f"{API_BASE_URL}/recognition/combined-recognition"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    data = {
        "video_id": video_id,
        "save_output": False
    }
    
    response = requests.post(url, headers=headers, json=data)
    
    if response.status_code != 200:
        console.print(f"[bold red]Failed to get results:[/bold red] {response.status_code} - {response.text}")
        return
    
    result = response.json()
    
    # Display the results
    console.print("\n[bold green]Recognition Results:[/bold green]")
    console.print(f"[bold]Video ID:[/bold] {video_id}")
    
    # Speaker identification results
    speaker_result = result.get("speaker_identification", {})
    console.print("\n[bold blue]Speaker Identification:[/bold blue]")
    console.print(f"[bold]Success:[/bold] {speaker_result.get('success', False)}")
    
    if speaker_result.get("success", False):
        speakers = speaker_result.get("results", {}).get("speakers", [])
        console.print(f"[bold]Total speakers:[/bold] {len(speakers)}")
        
        for i, speaker in enumerate(speakers, 1):
            console.print(f"  [bold]{i}.[/bold] {speaker.get('name')} (confidence: {speaker.get('confidence'):.2f})")
            console.print(f"     Time: {speaker.get('start_time'):.2f}s - {speaker.get('end_time'):.2f}s")
    
    # Transcription results
    transcript_result = result.get("transcription", {})
    console.print("\n[bold blue]Transcription:[/bold blue]")
    console.print(f"[bold]Success:[/bold] {transcript_result.get('success', False)}")
    
    if transcript_result.get("success", False):
        transcript = transcript_result.get("transcript", "")
        if transcript:
            preview = transcript[:500] + "..." if len(transcript) > 500 else transcript
            console.print(f"[bold]Transcript preview:[/bold]\n{preview}")
        
        output_file = transcript_result.get("output_file")
        if output_file:
            console.print(f"[bold]Output file:[/bold] {output_file}")
    
    # Processing details
    processing_details = result.get("processing_details", {})
    console.print("\n[bold blue]Processing Details:[/bold blue]")
    console.print(f"[bold]Video available:[/bold] {processing_details.get('video_available', False)}")
    console.print(f"[bold]Audio available:[/bold] {processing_details.get('audio_available', False)}")
    
    if processing_details.get("video_path"):
        console.print(f"[bold]Video path:[/bold] {processing_details.get('video_path')}")
    
    if processing_details.get("audio_path"):
        console.print(f"[bold]Audio path:[/bold] {processing_details.get('audio_path')}")

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description='Run and monitor recognition process for Parliament TV captures')
    parser.add_argument('--video-id', '-v', type=int, required=True, help='ID of the video to process')
    parser.add_argument('--username', '-u', default=DEFAULT_USERNAME, help='Username for authentication')
    parser.add_argument('--password', '-p', default=DEFAULT_PASSWORD, help='Password for authentication')
    parser.add_argument('--no-save', action='store_true', help='Do not save output files')
    parser.add_argument('--timeout', '-t', type=int, default=600, help='Timeout in seconds for monitoring (default: 600)')
    parser.add_argument('--monitor-only', '-m', action='store_true', help='Only monitor an existing recognition process')
    parser.add_argument('--results-only', '-r', action='store_true', help='Only display results of a completed recognition process')
    args = parser.parse_args()
    
    try:
        # Authenticate
        token = authenticate(args.username, args.password)
        
        if args.results_only:
            # Only display results
            display_recognition_results(token, args.video_id)
        elif args.monitor_only:
            # Only monitor an existing process
            console.print(f"[bold blue]Monitoring recognition process for video ID:[/bold blue] [yellow]{args.video_id}[/yellow]")
            result = monitor_recognition_progress(token, args.video_id, args.timeout)
            
            if result.get("success", False):
                display_recognition_results(token, args.video_id)
        else:
            # Start a new recognition process and monitor it
            start_result = start_recognition(token, args.video_id, not args.no_save)
            
            if start_result.get("success", False):
                console.print("[bold green]Recognition process started[/bold green]")
                result = monitor_recognition_progress(token, args.video_id, args.timeout)
                
                if result.get("success", False):
                    display_recognition_results(token, args.video_id)
            else:
                console.print("[bold red]Failed to start recognition process[/bold red]")
        
        return 0
    
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
