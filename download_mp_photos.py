#!/usr/bin/env python
"""
Script to download MP photos from the official UK Parliament website
and generate face embeddings for them
"""
import os
import json
import logging
import requests
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    from backend.db.session import SessionLocal
    from backend.services.integration.supabase_client import SupabaseService
    from backend.services.recognition.face_recognition import FaceRecognitionService
    from sqlalchemy import text
    
    # Initialize services
    db = SessionLocal()
    supabase_service = SupabaseService(use_service_role=True)
    face_recognition = FaceRecognitionService()
    
    # Create directories for MP photos
    mp_photos_dir = "/app/data/mp_photos"
    os.makedirs(mp_photos_dir, exist_ok=True)
    
    # Create a local cache file to track processed members
    cache_file = os.path.join(mp_photos_dir, "processed_members.json")
    processed_cache = {}
    
    # Load cache if it exists
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r') as f:
                processed_cache = json.load(f)
            logger.info(f"Loaded cache with {len(processed_cache)} previously processed members")
        except Exception as e:
            logger.warning(f"Failed to load cache file: {str(e)}")
    
    # Fetch all parliament members from Supabase
    logger.info("Fetching parliament members from Supabase...")
    response = supabase_service.client.table('parliament_members').select('*').execute()
    
    if not response.data:
        logger.error("No parliament members found in Supabase")
        return
    
    logger.info(f"Found {len(response.data)} parliament members in Supabase")
    
    # Process each member
    processed_count = 0
    failed_count = 0
    updated_count = 0
    skipped_count = 0
    
    for member in response.data:
        member_id = member.get('id')
        if not member_id:
            continue
        
        # Get member details
        name = member.get('name')
        image_url = member.get('image_url')
        
        # Skip default members (unidentified speakers)
        if member.get('is_default_member'):
            logger.info(f"Skipping default member: {name}")
            continue
        
        logger.info(f"Processing member: {name} (ID: {member_id})")
        
        # Check if we've already processed this member recently
        if member_id in processed_cache:
            cache_entry = processed_cache[member_id]
            last_processed = cache_entry.get('last_processed')
            has_embedding = cache_entry.get('has_embedding', False)
            
            # If processed in the last 7 days and has embedding, skip
            if last_processed and has_embedding:
                from datetime import datetime, timedelta
                last_date = datetime.fromisoformat(last_processed)
                if datetime.now() - last_date < timedelta(days=7):
                    logger.info(f"Member {name} was processed recently and has embedding, skipping")
                    skipped_count += 1
                    continue
        
        # Check if we already have an image URL
        if image_url and not image_url.startswith("http"):
            # This is a local path, check if it exists
            if os.path.exists(image_url):
                logger.info(f"Member already has a valid local image: {image_url}")
                
                # Generate face embedding if not already done
                if not member.get('face_embedding'):
                    try:
                        face_data = face_recognition.extract_face_embedding(image_url)
                        if face_data and 'embedding' in face_data:
                            # Update member with face embedding
                            update_data = {'face_embedding': face_data['embedding']}
                            supabase_service.client.table('parliament_members').update(update_data).eq('id', member_id).execute()
                            logger.info(f"Updated face embedding for member {name}")
                            updated_count += 1
                            
                            # Update local cache
                            processed_cache[member_id] = {
                                'last_processed': datetime.now().isoformat(),
                                'has_embedding': True,
                                'image_path': image_url
                            }
                    except Exception as e:
                        logger.error(f"Error generating face embedding for {name}: {str(e)}")
                else:
                    # Already has embedding, update cache
                    processed_cache[member_id] = {
                        'last_processed': datetime.now().isoformat(),
                        'has_embedding': True,
                        'image_path': image_url
                    }
                
                processed_count += 1
                continue
        
        # Try to find the member on the UK Parliament website
        try:
            # Search for the member by name
            search_url = f"https://members-api.parliament.uk/api/Members/Search?Name={name}&skip=0&take=20"
            
            # Add proper headers to avoid 403 errors
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'application/json',
                'Accept-Language': 'en-US,en;q=0.9',
                'Referer': 'https://members.parliament.uk/',
                'Origin': 'https://members.parliament.uk'
            }
            
            # Check if we already have a photo for this member in the local filesystem
            expected_photo_path = os.path.join(mp_photos_dir, f"{member_id}.jpg")
            if os.path.exists(expected_photo_path):
                logger.info(f"Found existing photo for {name} at {expected_photo_path}")
                photo_path = expected_photo_path
            else:
                # Need to download the photo
                response = requests.get(search_url, headers=headers)
                
                if response.status_code != 200:
                    logger.warning(f"Failed to search for member {name}: {response.status_code}")
                    failed_count += 1
                    continue
                
                search_results = response.json()
                
                if not search_results.get('items'):
                    logger.warning(f"No search results found for member {name}")
                    failed_count += 1
                    continue
                
                # Find the best match
                member_data = None
                for item in search_results['items']:
                    if item.get('value', {}).get('nameDisplayAs', '').lower() == name.lower():
                        member_data = item.get('value')
                        break
                
                if not member_data:
                    # Take the first result if no exact match
                    member_data = search_results['items'][0].get('value')
                
                if not member_data:
                    logger.warning(f"No member data found for {name}")
                    failed_count += 1
                    continue
                
                # Get member details
                member_id_uk = member_data.get('id')
                
                if not member_id_uk:
                    logger.warning(f"No UK Parliament ID found for member {name}")
                    failed_count += 1
                    continue
                
                # Get member photo URL
                photo_url = f"https://members-api.parliament.uk/api/Members/{member_id_uk}/Portrait?CropType=FullSize"
                
                # Download the photo
                photo_response = requests.get(photo_url, headers=headers)
                
                if photo_response.status_code != 200:
                    logger.warning(f"Failed to download photo for member {name}: {photo_response.status_code}")
                    failed_count += 1
                    continue
                
                # Save the photo
                photo_path = os.path.join(mp_photos_dir, f"{member_id}.jpg")
                
                with open(photo_path, 'wb') as f:
                    f.write(photo_response.content)
                
                logger.info(f"Downloaded photo for member {name} to {photo_path}")
                
                # Add a small delay to avoid overwhelming the API
                time.sleep(0.5)
            
            # Generate face embedding
            face_data = face_recognition.extract_face_embedding(photo_path)
            
            if face_data and 'embedding' in face_data:
                # Update member with image URL and face embedding
                update_data = {
                    'image_url': photo_path,
                    'face_embedding': face_data['embedding']
                }
                
                # Update in Supabase
                supabase_service.client.table('parliament_members').update(update_data).eq('id', member_id).execute()
                logger.info(f"Updated image URL and face embedding for member {name}")
                
                # Update in local SQLite database if the table exists
                try:
                    # Check if speakers table exists
                    result = db.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='speakers'")).fetchone()
                    if result:
                        # Update or insert into speakers table
                        db.execute(
                            text("INSERT OR REPLACE INTO speakers (parliament_id, name, photo_url, face_encoding) VALUES (:parliament_id, :name, :photo_url, :face_encoding)"),
                            {
                                "parliament_id": member_id,
                                "name": name,
                                "photo_url": photo_path,
                                "face_encoding": json.dumps(face_data['embedding'])
                            }
                        )
                        db.commit()
                        logger.info(f"Updated local database record for {name}")
                except Exception as e:
                    logger.warning(f"Could not update local database: {str(e)}")
                
                # Update cache
                processed_cache[member_id] = {
                    'last_processed': datetime.now().isoformat(),
                    'has_embedding': True,
                    'image_path': photo_path
                }
                
                updated_count += 1
            else:
                logger.warning(f"No face detected in photo for member {name}")
                
                # Still update the image URL even if no face was detected
                update_data = {'image_url': photo_path}
                supabase_service.client.table('parliament_members').update(update_data).eq('id', member_id).execute()
                logger.info(f"Updated image URL for member {name}")
                
                # Update cache
                processed_cache[member_id] = {
                    'last_processed': datetime.now().isoformat(),
                    'has_embedding': False,
                    'image_path': photo_path
                }
            
            processed_count += 1
            
        except Exception as e:
            logger.error(f"Error processing member {name}: {str(e)}")
            failed_count += 1
    
    # Save the cache
    try:
        with open(cache_file, 'w') as f:
            json.dump(processed_cache, f, indent=2)
        logger.info(f"Saved cache with {len(processed_cache)} processed members")
    except Exception as e:
        logger.warning(f"Failed to save cache file: {str(e)}")
    
    logger.info(f"Processed {processed_count} members, updated {updated_count}, skipped {skipped_count}, failed {failed_count}")

if __name__ == "__main__":
    main()
