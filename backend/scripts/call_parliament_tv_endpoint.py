#!/usr/bin/env python
"""
Script to call the Parliament TV processing endpoint.
This is called by the cron job to automate Parliament TV processing.
"""

import os
import sys
import requests
import logging
from datetime import datetime
from pathlib import Path
import json

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from backend.core.config import settings

# Create logs directory if it doesn't exist
logs_dir = os.path.join(project_root, "logs")
os.makedirs(logs_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename=os.path.join(logs_dir, "parliament_tv_cron.log"),
    filemode='a'
)
logger = logging.getLogger(__name__)

def get_current_parliament_tv_url():
    """
    Get the current Parliament TV URL.
    
    In a production environment, this would scrape the Parliament TV website
    to get the current live stream URL or upcoming event.
    
    Returns:
        URL of the current Parliament TV event
    """
    # For now, we'll use a hardcoded URL for the live stream
    # In production, this should be replaced with a scraper or API call
    return "https://www.parliamentlive.tv/Event/Index/"

def call_parliament_tv_endpoint():
    """Call the Parliament TV processing endpoint."""
    try:
        # Get the current Parliament TV URL
        parliament_tv_url = get_current_parliament_tv_url()
        
        # Get the current date and time for the title
        now = datetime.now()
        title = f"Parliament TV Automated Capture {now.strftime('%Y-%m-%d %H:%M')}"
        
        # Set up the API request
        api_url = f"http://localhost:8000/api/v1/supabase-automation/process-parliament-tv"
        
        # Get API key from environment or settings
        api_key = os.environ.get("API_KEY", settings.API_KEY)
        
        if not api_key:
            logger.error("No API key available. Set API_KEY environment variable.")
            return False
        
        headers = {"X-API-Key": api_key}
        data = {
            "url": parliament_tv_url,
            "title": title,
            "description": f"Automated capture of Parliament TV on {now.strftime('%Y-%m-%d')}",
            "duration": 7200  # 2 hours
        }
        
        # Call the API
        logger.info(f"Calling Parliament TV processing endpoint with URL: {parliament_tv_url}")
        response = requests.post(api_url, json=data, headers=headers)
        response.raise_for_status()
        
        # Log the response
        response_data = response.json()
        logger.info(f"API call successful: {json.dumps(response_data)}")
        
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"API request error: {str(e)}")
        if hasattr(e, 'response') and e.response:
            try:
                error_detail = e.response.json()
                logger.error(f"API error response: {json.dumps(error_detail)}")
            except:
                logger.error(f"API error status code: {e.response.status_code}")
                logger.error(f"API error text: {e.response.text}")
        return False
    except Exception as e:
        logger.error(f"Error calling Parliament TV endpoint: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    # Call the endpoint
    success = call_parliament_tv_endpoint()
    
    # Exit with appropriate status code
    sys.exit(0 if success else 1)
