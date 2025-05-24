"""
API endpoints for serving files like unidentified face images.
"""

import os
import logging
from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Path
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import glob

from backend.api.deps import get_db, get_current_user
from backend.db import models
from backend.core.config import settings
from backend.core.security import has_permission, UserRole

# Set up logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

@router.get("/unidentified/{filename}")
async def get_unidentified_face_image(
    filename: str = Path(..., description="Filename of the unidentified face image"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Get an unidentified face image by filename.
    """
    try:
        has_permission(current_user, [UserRole.ADMIN, UserRole.MP, UserRole.STAFF])
        
        # Sanitize the filename to prevent directory traversal
        safe_filename = os.path.basename(filename)
        logger.info(f"Looking for unidentified face image: {safe_filename} (original: {filename})")
        
        # Define possible locations for unidentified face images
        data_dir = settings.DATA_DIR
        logger.info(f"Data directory: {data_dir}")
        
        possible_dirs = [
            os.path.join(data_dir, "temp"),
            os.path.join(data_dir, "unidentified_faces"),
            os.path.join(data_dir, "temp", "*_unidentified_faces")
        ]
        
        # Add more specific directories for recent captures
        for i in range(370, 380):  # Try recent capture IDs
            capture_dir = os.path.join(data_dir, "temp", f"capture_{i:04d}_unidentified_faces")
            if os.path.exists(capture_dir):
                logger.info(f"Found specific capture directory: {capture_dir}")
                possible_dirs.append(capture_dir)
        
        logger.info(f"Searching in possible directories: {possible_dirs}")
        
        # Search for the file in all possible directories
        for search_dir in possible_dirs:
            # Use glob to find files in directories that match the pattern
            if "*" in search_dir:
                search_pattern = os.path.join(search_dir, safe_filename)
                matching_files = glob.glob(search_pattern, recursive=True)
                if matching_files:
                    logger.info(f"Found unidentified face image: {matching_files[0]}")
                    return FileResponse(matching_files[0])
            else:
                # Direct file path
                file_path = os.path.join(search_dir, safe_filename)
                if os.path.exists(file_path):
                    logger.info(f"Found unidentified face image: {file_path}")
                    return FileResponse(file_path)
        
        # If we get here, the file wasn't found
        logger.warning(f"Unidentified face image not found: {safe_filename}")
        
        # List all files in the possible directories to help debugging
        all_files = []
        for search_dir in possible_dirs:
            if "*" in search_dir:
                pattern = os.path.join(os.path.dirname(search_dir), "*")
                logger.info(f"Searching with glob pattern: {pattern}")
                dirs = glob.glob(pattern)
                logger.info(f"Found directories: {dirs}")
                for d in dirs:
                    if os.path.isdir(d):
                        try:
                            files = os.listdir(d)
                            logger.info(f"Directory {d} contains {len(files)} files")
                            all_files.extend([os.path.join(d, f) for f in files if os.path.isfile(os.path.join(d, f))])
                        except Exception as e:
                            logger.error(f"Error listing directory {d}: {str(e)}")
            else:
                if os.path.exists(search_dir) and os.path.isdir(search_dir):
                    try:
                        files = os.listdir(search_dir)
                        logger.info(f"Directory {search_dir} contains {len(files)} files")
                        # Check if our target file is in this directory
                        if safe_filename in files:
                            logger.info(f"Found target file {safe_filename} in {search_dir}")
                        all_files.extend([os.path.join(search_dir, f) for f in files if os.path.isfile(os.path.join(search_dir, f))])
                    except Exception as e:
                        logger.error(f"Error listing directory {search_dir}: {str(e)}")
                else:
                    logger.warning(f"Directory does not exist or is not a directory: {search_dir}")
        
        # Log the first few files to help with debugging
        if all_files:
            logger.info(f"Available files (first 20): {[os.path.basename(f) for f in all_files[:20]]}")
        else:
            logger.warning("No files found in any of the search directories")
        
        # Try one more time with a direct approach - look for any file ending with the safe_filename
        # This is a fallback for when the directory structure might be different
        try:
            for root, dirs, files in os.walk(os.path.join(data_dir, "temp")):
                for file in files:
                    if file == safe_filename:
                        full_path = os.path.join(root, file)
                        logger.info(f"Found file with direct search: {full_path}")
                        return FileResponse(full_path)
        except Exception as e:
            logger.error(f"Error in direct file search: {str(e)}")
        
        raise HTTPException(status_code=404, detail=f"Unidentified face image not found: {safe_filename}")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting unidentified face image: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting unidentified face image: {str(e)}")
        
    # If we get here, something went wrong
    logger.error(f"Unexpected code path in get_unidentified_face_image for {safe_filename}")
    raise HTTPException(status_code=500, detail="Unexpected error in get_unidentified_face_image")
