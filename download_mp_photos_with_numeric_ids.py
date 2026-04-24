#!/usr/bin/env python
"""
Script to download MP photos from the official UK Parliament website
and generate face embeddings for them using numeric member IDs as filenames
"""
import os
import json
import logging
import requests
import shutil
import face_recognition
import numpy as np
import time
import urllib.parse
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def ensure_local_directories_exist():
    """Ensure that the necessary directories exist for storing MP photos and embeddings"""
    try:
        # Create directories for MP photos and embeddings
        mp_photos_dir = "/app/data/mp_photos"
        os.makedirs(mp_photos_dir, exist_ok=True)
        logger.info(f"Ensured directory exists: {mp_photos_dir}")
        
        # Check if we can write to the directory
        test_file = os.path.join(mp_photos_dir, "test_write.tmp")
        try:
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)
            logger.info(f"Directory {mp_photos_dir} is writable")
        except Exception as e:
            logger.error(f"Directory {mp_photos_dir} is not writable: {str(e)}")
            
    except Exception as e:
        logger.error(f"Error ensuring directories exist: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

def download_mp_photos(db):
    """Download MP photos and generate face embeddings"""
    # We'll use the face_recognition module directly instead of the custom class
    # This is already imported at the top of the file
    
    # Directory for MP photos
    mp_photos_dir = "/app/data/mp_photos"
    os.makedirs(mp_photos_dir, exist_ok=True)
    
    # Directory for MP embeddings - separate from photos
    mp_embeddings_dir = "/app/data/mp_embeddings"
    os.makedirs(mp_embeddings_dir, exist_ok=True)
    
    # Create a backup directory for existing files
    backup_dir = os.path.join(mp_photos_dir, "backup_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
    os.makedirs(backup_dir, exist_ok=True)
    logger.info(f"Created backup directory: {backup_dir}")
    
    # Backup existing JSON files
    json_files = [f for f in os.listdir(mp_photos_dir) if f.endswith('.json')]
    for json_file in json_files:
        src_path = os.path.join(mp_photos_dir, json_file)
        dst_path = os.path.join(backup_dir, json_file)
        try:
            shutil.copy2(src_path, dst_path)
            logger.info(f"Backed up {json_file} to {backup_dir}")
        except Exception as e:
            logger.error(f"Failed to back up {json_file}: {str(e)}")
            
    # Also backup embedding files if they exist
    if os.path.exists(mp_embeddings_dir):
        embeddings_backup_dir = os.path.join(backup_dir, "embeddings")
        os.makedirs(embeddings_backup_dir, exist_ok=True)
        
        embedding_files = [f for f in os.listdir(mp_embeddings_dir) if f.endswith('.json')]
        for embedding_file in embedding_files:
            src_path = os.path.join(mp_embeddings_dir, embedding_file)
            dst_path = os.path.join(embeddings_backup_dir, embedding_file)
            try:
                shutil.copy2(src_path, dst_path)
                logger.info(f"Backed up embedding file {embedding_file} to {embeddings_backup_dir}")
            except Exception as e:
                logger.error(f"Failed to back up embedding file {embedding_file}: {str(e)}")
    
    # Query the database for parliament members
    result = db.execute(text("""
        SELECT id, parliament_id, name, photo_url
        FROM speakers
        WHERE parliament_id IS NOT NULL
        ORDER BY name
    """))
    members = result.fetchall()
    
    if not members:
        logger.error("No members found in database")
        return
    
    logger.info(f"Found {len(members)} members in database")
    
    # Process each member
    for member in members:
        id = member[0]
        parliament_id = member[1]
        name = member[2]
        photo_url = member[3]
        
        if not parliament_id:
            logger.warning(f"Member {name} has no parliament_id, skipping")
            continue
        
        logger.info(f"Processing member {name} (ID: {id}, Parliament ID: {parliament_id})")
        
        # Download photo if needed
        if not photo_url or not photo_url.startswith("http"):
            # Try to find a photo on the Parliament website
            try:
                # Construct the URL for the member's photo
                member_photo_url = f"https://members-api.parliament.uk/api/Members/{parliament_id}/Portrait?cropType=ThreeFour"
                logger.info(f"Attempting to download photo from {member_photo_url}")
                
                # Download the photo
                response = requests.get(member_photo_url, stream=True)
                
                if response.status_code == 200:
                    # Save the photo to the local directory using parliament_id as filename
                    photo_path = os.path.join(mp_photos_dir, f"{parliament_id}.jpg")
                    
                    with open(photo_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=1024):
                            if chunk:
                                f.write(chunk)
                    
                    logger.info(f"Downloaded photo to {photo_path}")
                    
                    # Update photo_url in the database
                    try:
                        db.execute(text("""
                            UPDATE speakers 
                            SET photo_url = :photo_url 
                            WHERE parliament_id = :parliament_id
                        """), {"photo_url": photo_path, "parliament_id": parliament_id})
                        db.commit()
                        logger.info(f"Updated photo_url for member {name} (Parliament ID: {parliament_id})")
                    except Exception as e:
                        logger.warning(f"Failed to update photo_url in database: {str(e)}")
                else:
                    logger.warning(f"Failed to download photo for {name}: HTTP {response.status_code}")
                    continue
                
            except Exception as e:
                logger.error(f"Error downloading photo for {name}: {str(e)}")
                continue
        else:
            # Use the existing photo URL
            photo_path = photo_url
            logger.info(f"Using existing photo at {photo_path}")
        
        # Generate face embedding
        embedding = None
        try:
            # The face recognition module expects a file path
            # For local files, use the file path directly
            if os.path.exists(photo_path):
                # Load the image
                image = face_recognition.load_image_file(photo_path)
                
                # Find all face locations in the image
                face_locations = face_recognition.face_locations(image)
                
                if not face_locations:
                    logger.warning(f"No faces detected in photo for {name} (Parliament ID: {parliament_id})")
                    continue
                    
                # Generate face encodings (embeddings)
                face_encodings = face_recognition.face_encodings(image, face_locations)
                
                if not face_encodings or len(face_encodings) == 0:
                    logger.warning(f"Could not generate embedding for {name} (Parliament ID: {parliament_id})")
                    continue
                    
                # Use the first face encoding if multiple faces are detected
                embedding = face_encodings[0]  # This is already a numpy array
            else:
                # For URLs, we'd need to download the image first
                # For simplicity, we'll just log a warning and skip
                logger.warning(f"Photo path {photo_path} does not exist, skipping embedding generation")
                continue
        except Exception as e:
            logger.error(f"Error processing image for {name}: {str(e)}")
            continue
        
        if embedding is not None:
            # Save face embedding to JSON file in the embeddings directory
            json_file = os.path.join(mp_embeddings_dir, f"{parliament_id}.json")
            try:
                with open(json_file, "w") as f:
                    # Handle both numpy arrays and lists
                    if hasattr(embedding, 'tolist'):
                        json.dump({"embedding": embedding.tolist()}, f)
                    else:
                        # It's already a list
                        json.dump({"embedding": embedding}, f)
                logger.info(f"Saved face embedding for {name} (Parliament ID: {parliament_id}) to {json_file}")
            except Exception as e:
                logger.error(f"Error generating face embedding for {name}: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
    
    # Create a mapping file from UUID to parliament_id for reference
    mapping = {}
    for member in members:
        id = member[0]
        parliament_id = member[1]
        name = member[2]
        if id and parliament_id:
            mapping[str(id)] = {
                "parliament_id": str(parliament_id),
                "name": name
            }
    
    # Also create a consolidated mp_encodings.json file for compatibility
    try:
        # Prepare data for mp_encodings.json
        ids = []
        encodings = []
        names = []
        
        # Collect all embeddings from the individual files
        for member in members:
            parliament_id = member[1]
            name = member[2]
            if parliament_id:
                embedding_file = os.path.join(mp_embeddings_dir, f"{parliament_id}.json")
                if os.path.exists(embedding_file):
                    try:
                        with open(embedding_file, 'r') as f:
                            data = json.load(f)
                        
                        if 'embedding' in data:
                            ids.append(str(member_id))
                            encodings.append(data['embedding'])
                            names.append(name)
                    except Exception as e:
                        logger.error(f"Error reading embedding file {embedding_file}: {str(e)}")
        
        # Create the mp_encodings.json file
        mp_encodings_file = os.path.join("/app/data", "mp_encodings.json")
        with open(mp_encodings_file, 'w') as f:
            json.dump({
                "ids": ids,
                "encodings": encodings,
                "names": names
            }, f)
        logger.info(f"Created consolidated mp_encodings.json with {len(ids)} embeddings")
    except Exception as e:
        logger.error(f"Error creating mp_encodings.json: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
    
    # Save the UUID to member_id mapping
    mapping_file = os.path.join(mp_photos_dir, "uuid_to_member_id.json")
    with open(mapping_file, 'w') as f:
        json.dump(mapping, f, indent=2)
    logger.info(f"Saved UUID to member_id mapping for {len(mapping)} members to {mapping_file}")
    
    # Create a README file explaining the changes
    readme_path = os.path.join(mp_photos_dir, "README.txt")
    with open(readme_path, 'w') as f:
        f.write(f"""
MP Photo and Embedding Files
===========================

Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

This directory contains MP photos and face embeddings saved using numeric member IDs as filenames.
Previous files (if any) have been backed up to the '{os.path.basename(backup_dir)}' directory.

File naming convention:
- <member_id>.jpg - Photo of the MP
- <member_id>.json - Face embedding for the MP

The mapping between UUIDs and member IDs is stored in 'uuid_to_member_id.json'.
""")
    
    logger.info(f"Created README file at {readme_path}")
    logger.info("Done!")

def main():
    import sys
    import os
    
    # Add the project root to the Python path
    sys.path.append('/app')
    
    try:
        # Ensure the necessary directories exist
        ensure_local_directories_exist()
        
        # Initialize database connection using SQLAlchemy directly
        # PostgreSQL connection
        try:
            engine = create_engine('postgresql://postgres:postgres@db:5432/parliament_clips')
            Session_cls = sessionmaker(bind=engine)
            db_session = Session_cls()
            logger.info("Connected to PostgreSQL database")
            
            # Download MP photos and generate face embeddings
            download_mp_photos(db_session)
            
        except Exception as e:
            logger.error(f"Error connecting to PostgreSQL: {e}")
            logger.warning("Trying SQLite database instead...")
            
            # Try SQLite as fallback
            try:
                sqlite_engine = create_engine('sqlite:////app/backend/parliament_clips.db')
                SQLiteSession = sessionmaker(bind=sqlite_engine)
                db_session = SQLiteSession()
                logger.info("Connected to SQLite database")
                
                # Download MP photos and generate face embeddings
                download_mp_photos(db_session)
                
            except Exception as e:
                logger.error(f"Error connecting to SQLite database: {e}")
                raise
        finally:
            # Close database connection if it exists
            if 'db_session' in locals() and db_session:
                db_session.close()
                
    except ImportError as e:
        logger.error(f"Import error: {e}")
        logger.error("Make sure you're running this script within the Docker container")
    except Exception as e:
        logger.error(f"Error in main: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    main()
