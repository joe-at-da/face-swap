#!/usr/bin/env python
"""
Setup script for Parliament TV automation cron job.

This script creates a cron job that calls the unified Parliament TV processing
endpoint every few hours to automatically capture, recognize, and export
Parliament TV content to Supabase.

Usage:
    python setup_parliament_tv_cron.py [--interval HOURS] [--api-url URL] [--api-key KEY]
"""

import os
import sys
import argparse
import logging
import requests
from pathlib import Path
from crontab import CronTab
from datetime import datetime, timedelta

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from backend.core.config import settings

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_cron_job(interval_hours=2, api_url=None, api_key=None):
    """
    Create a cron job to call the Parliament TV processing endpoint.
    
    Args:
        interval_hours: Hours between cron job runs
        api_url: Base URL of the API
        api_key: API key for authentication
    """
    # Default values if not provided
    if not api_url:
        api_url = os.environ.get("API_URL", "http://localhost:8000")
    
    if not api_key:
        api_key = os.environ.get("API_KEY", settings.API_KEY)
    
    if not api_key:
        logger.error("No API key provided. Set API_KEY environment variable or pass --api-key.")
        return False
    
    # Create the cron command
    script_path = os.path.join(project_root, "backend", "scripts", "call_parliament_tv_endpoint.py")
    
    # Create the call script if it doesn't exist
    if not os.path.exists(script_path):
        with open(script_path, "w") as f:
            f.write(f"""#!/usr/bin/env python
\"\"\"
Script to call the Parliament TV processing endpoint.
This is called by the cron job to automate Parliament TV processing.
\"\"\"

import os
import sys
import requests
import logging
from datetime import datetime
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from backend.core.config import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename=os.path.join(project_root, "logs", "parliament_tv_cron.log"),
    filemode='a'
)
logger = logging.getLogger(__name__)

def call_parliament_tv_endpoint():
    \"\"\"Call the Parliament TV processing endpoint.\"\"\"
    try:
        # Get the current Parliament TV URL
        # This would typically come from a configuration or by scraping the Parliament TV website
        # For now, we'll use a hardcoded URL for the live stream
        parliament_tv_url = "https://www.parliamentlive.tv/Event/Index/"
        
        # Get the current date and time for the title
        now = datetime.now()
        title = f"Parliament TV Automated Capture {now.strftime('%Y-%m-%d %H:%M')}"
        
        # Set up the API request
        api_url = "{api_url}/api/v1/supabase-automation/process-parliament-tv"
        headers = {{"X-API-Key": "{api_key}"}}
        data = {{
            "url": parliament_tv_url,
            "title": title,
            "description": f"Automated capture of Parliament TV on {now.strftime('%Y-%m-%d')}",
            "duration": 7200  # 2 hours
        }}
        
        # Call the API
        logger.info(f"Calling Parliament TV processing endpoint with URL: {{parliament_tv_url}}")
        response = requests.post(api_url, json=data, headers=headers)
        response.raise_for_status()
        
        logger.info(f"API call successful: {{response.json()}}")
        return True
    except Exception as e:
        logger.error(f"Error calling Parliament TV endpoint: {{str(e)}}")
        return False

if __name__ == "__main__":
    # Create logs directory if it doesn't exist
    logs_dir = os.path.join(project_root, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    
    # Call the endpoint
    call_parliament_tv_endpoint()
""")
        os.chmod(script_path, 0o755)
        logger.info(f"Created call script at {script_path}")
    
    # Set up the cron job
    try:
        cron = CronTab(user=True)
        
        # Remove any existing jobs with the same comment
        for job in cron.find_comment("parliament_tv_automation"):
            cron.remove(job)
            logger.info("Removed existing Parliament TV automation cron job")
        
        # Create a new job
        job = cron.new(command=f"{sys.executable} {script_path}", comment="parliament_tv_automation")
        
        # Set the schedule to run every X hours
        job.hour.every(interval_hours)
        
        # Write the cron job
        cron.write()
        
        # Calculate the next run time
        next_run = job.schedule(date_from=datetime.now()).get_next()
        
        logger.info(f"Created cron job to run every {interval_hours} hours")
        logger.info(f"Next run scheduled for: {next_run}")
        
        return True
    except Exception as e:
        logger.error(f"Error creating cron job: {str(e)}")
        return False

def main():
    """Main function to parse arguments and create the cron job."""
    parser = argparse.ArgumentParser(description="Setup Parliament TV automation cron job")
    parser.add_argument("--interval", type=int, default=2, help="Hours between cron job runs (default: 2)")
    parser.add_argument("--api-url", type=str, help="Base URL of the API (default: http://localhost:8000)")
    parser.add_argument("--api-key", type=str, help="API key for authentication")
    
    args = parser.parse_args()
    
    # Create the cron job
    success = create_cron_job(
        interval_hours=args.interval,
        api_url=args.api_url,
        api_key=args.api_key
    )
    
    if success:
        logger.info("Parliament TV automation cron job setup completed successfully")
        sys.exit(0)
    else:
        logger.error("Failed to set up Parliament TV automation cron job")
        sys.exit(1)

if __name__ == "__main__":
    main()
