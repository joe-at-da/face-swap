#!/usr/bin/env python3
"""
Script to rebuild the MP encodings file from individual MP photo JSON files.
This fixes the issue where face recognition isn't matching MPs because the
mp_encodings.json file only contains generic embeddings.
"""

import os
import json
import logging
import glob
from typing import Dict, List, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def rebuild_mp_encodings():
    """
    Rebuild the MP encodings file from individual MP photo JSON files.
    """
    logger.info("Starting MP encodings rebuild process")
    
    # Paths
    mp_photos_dir = "/app/data/mp_photos"
    mp_encodings_file = "/app/data/mp_encodings.json"
    
    # Check if MP photos directory exists
    if not os.path.exists(mp_photos_dir):
        logger.error(f"MP photos directory not found: {mp_photos_dir}")
        return False
    
    # Find all MP JSON files
    json_files = glob.glob(os.path.join(mp_photos_dir, "*.json"))
    logger.info(f"Found {len(json_files)} MP JSON files")
    
    if not json_files:
        logger.error("No MP JSON files found")
        return False
    
    # Initialize data structure for the encodings file
    encodings_data = {
        "names": [],
        "ids": [],
        "encodings": [],
        "metadata": []
    }
    
    # Process each JSON file
    processed_count = 0
    error_count = 0
    
    for json_file in json_files:
        try:
            # Extract MP ID from filename
            mp_id = os.path.basename(json_file).replace(".json", "")
            
            # Load the JSON data
            with open(json_file, 'r') as f:
                mp_data = json.load(f)
            
            # Check if this is a valid embedding file
            if not isinstance(mp_data, list):
                # This might be a metadata file, try to extract embedding
                if "embedding" in mp_data:
                    embedding = mp_data["embedding"]
                else:
                    logger.warning(f"No embedding found in {json_file}")
                    error_count += 1
                    continue
            else:
                # Direct embedding array
                embedding = mp_data
            
            # Get corresponding photo file to extract name
            photo_file = json_file.replace(".json", ".jpg")
            if not os.path.exists(photo_file):
                logger.warning(f"No photo file found for {mp_id}")
                name = f"MP {mp_id[-6:]}"  # Use last 6 chars of ID as name
            else:
                # Try to get name from filename or use ID
                name = os.path.basename(photo_file).replace(".jpg", "")
                name = name.replace("_", " ").title()
                if len(name) > 30:  # If name is too long, use ID
                    name = f"MP {mp_id[-6:]}"
            
            # Add to encodings data
            encodings_data["names"].append(name)
            encodings_data["ids"].append(mp_id)
            encodings_data["encodings"].append(embedding)
            
            # Add metadata
            metadata = {
                "id": mp_id,
                "name": name,
                "photo_path": photo_file
            }
            encodings_data["metadata"].append(metadata)
            
            processed_count += 1
            
            if processed_count % 100 == 0:
                logger.info(f"Processed {processed_count} MP embeddings")
                
        except Exception as e:
            logger.error(f"Error processing {json_file}: {str(e)}")
            error_count += 1
    
    # Save the encodings file
    if processed_count > 0:
        try:
            # Backup the original file if it exists
            if os.path.exists(mp_encodings_file):
                backup_file = f"{mp_encodings_file}.bak"
                logger.info(f"Backing up original encodings file to {backup_file}")
                os.rename(mp_encodings_file, backup_file)
            
            # Write the new encodings file
            with open(mp_encodings_file, 'w') as f:
                json.dump(encodings_data, f)
            
            logger.info(f"Successfully rebuilt MP encodings file with {processed_count} MPs")
            logger.info(f"New encodings file saved to {mp_encodings_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving encodings file: {str(e)}")
            return False
    else:
        logger.error("No MP embeddings were processed successfully")
        return False

if __name__ == "__main__":
    success = rebuild_mp_encodings()
    if success:
        print("✅ MP encodings file rebuilt successfully")
    else:
        print("❌ Failed to rebuild MP encodings file")
