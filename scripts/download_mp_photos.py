#!/usr/bin/env python3
"""
Download MP Photos Script

This script downloads sample MP photos from public sources to use for facial recognition.
It's designed to help set up the facial recognition system with real MP data rather than
using fake data.

Usage:
    python download_mp_photos.py [--output-dir /path/to/output/directory]

Example:
    python download_mp_photos.py --output-dir /app/data/mp_photos
"""

import os
import sys
import argparse
import logging
import requests
from pathlib import Path
from tqdm import tqdm

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("download_mp_photos")

# Sample MP data with photo URLs
# These are public domain photos of UK politicians from Wikipedia
SAMPLE_MPS = [
    {
        "name": "Keir Starmer",
        "party": "Labour",
        "constituency": "Holborn and St Pancras",
        "photo_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/23/Official_portrait_of_Keir_Starmer_crop_2.jpg/440px-Official_portrait_of_Keir_Starmer_crop_2.jpg"
    },
    {
        "name": "Rishi Sunak",
        "party": "Conservative",
        "constituency": "Richmond (Yorks)",
        "photo_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7e/Official_portrait_of_Rishi_Sunak_crop_2.jpg/440px-Official_portrait_of_Rishi_Sunak_crop_2.jpg"
    },
    {
        "name": "Angela Rayner",
        "party": "Labour",
        "constituency": "Ashton-under-Lyne",
        "photo_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7a/Official_portrait_of_Angela_Rayner_crop_2.jpg/440px-Official_portrait_of_Angela_Rayner_crop_2.jpg"
    },
    {
        "name": "Jeremy Hunt",
        "party": "Conservative",
        "constituency": "South West Surrey",
        "photo_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9f/Official_portrait_of_Rt_Hon_Jeremy_Hunt_MP_crop_2.jpg/440px-Official_portrait_of_Rt_Hon_Jeremy_Hunt_MP_crop_2.jpg"
    },
    {
        "name": "Ed Davey",
        "party": "Liberal Democrats",
        "constituency": "Kingston and Surbiton",
        "photo_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e3/Official_portrait_of_Sir_Edward_Davey_crop_2.jpg/440px-Official_portrait_of_Sir_Edward_Davey_crop_2.jpg"
    }
]

def download_photo(mp, output_dir):
    """Download an MP photo from a URL."""
    try:
        # Create a safe filename from the MP name
        safe_name = mp["name"].lower().replace(" ", "_")
        filename = f"{safe_name}.jpg"
        
        # Destination path
        dest_path = output_dir / filename
        
        # Download the photo
        response = requests.get(mp["photo_url"], stream=True)
        if response.status_code != 200:
            logger.error(f"Failed to download photo for {mp['name']}: HTTP {response.status_code}")
            return None
        
        # Save the photo
        with open(dest_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        logger.info(f"Downloaded photo for {mp['name']} to {dest_path}")
        return dest_path
    except Exception as e:
        logger.exception(f"Error downloading photo for {mp['name']}: {str(e)}")
        return None

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Download sample MP photos")
    parser.add_argument("--output-dir", default="/app/data/mp_photos", help="Output directory for photos")
    
    args = parser.parse_args()
    
    # Create the output directory if it doesn't exist
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Download photos
    downloaded_photos = []
    
    for mp in tqdm(SAMPLE_MPS, desc="Downloading MP photos"):
        photo_path = download_photo(mp, output_dir)
        if photo_path:
            downloaded_photos.append({
                "name": mp["name"],
                "party": mp["party"],
                "constituency": mp["constituency"],
                "photo_path": str(photo_path)
            })
    
    logger.info(f"Downloaded {len(downloaded_photos)} MP photos")
    
    # Print instructions for adding MP profiles
    print("\nTo add these MPs to the database, run the following commands:")
    for mp in downloaded_photos:
        cmd = f"python add_mp_profile.py --name \"{mp['name']}\" --photo \"{mp['photo_path']}\" --party \"{mp['party']}\" --constituency \"{mp['constituency']}\""
        print(cmd)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
