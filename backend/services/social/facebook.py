import logging
import os
import json
import requests
from typing import Dict, List, Optional, Any
from datetime import datetime

from backend.core.config import settings
from backend.services.social.base import SocialMediaPlatform

logger = logging.getLogger(__name__)

class FacebookPlatform(SocialMediaPlatform):
    """Facebook platform integration using the Graph API."""
    
    def __init__(self):
        super().__init__()
        self.app_id = settings.FACEBOOK_APP_ID
        self.app_secret = settings.FACEBOOK_APP_SECRET
        self.access_token = settings.FACEBOOK_ACCESS_TOKEN
        self.page_id = settings.FACEBOOK_PAGE_ID
        self.api_version = "v16.0"  # Use appropriate API version
        self.base_url = f"https://graph.facebook.com/{self.api_version}"
        
    def authenticate(self) -> bool:
        """
        Verify Facebook authentication credentials.
        
        Returns:
            True if authentication was successful, False otherwise
        """
        try:
            # Verify access token by making a simple API call
            url = f"{self.base_url}/me"
            params = {"access_token": self.access_token}
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            if "id" in data:
                logger.info(f"Facebook authentication successful for user {data.get('name', 'Unknown')}")
                return True
            else:
                logger.error("Facebook authentication failed: Invalid response")
                return False
                
        except Exception as e:
            logger.error(f"Facebook authentication failed: {str(e)}")
            return False
    
    def post_content(self, 
                     text: str, 
                     media_paths: Optional[List[str]] = None, 
                     scheduled_time: Optional[datetime] = None,
                     **kwargs) -> Dict:
        """
        Post content to Facebook.
        
        Args:
            text: The text content to post
            media_paths: Optional list of paths to media files to include
            scheduled_time: Optional time to schedule the post (ISO 8601 format)
            **kwargs: Additional Facebook-specific parameters
                - link: URL to include in the post
                - place_id: ID of a location to tag
                - tags: List of user IDs to tag
                
        Returns:
            Dictionary with post details including ID and status
        """
        if not self.authenticate():
            return {"status": "failed", "error": "Authentication failed", "platform": "facebook"}
        
        try:
            # Determine the type of post based on media
            post_url = f"{self.base_url}/{self.page_id}/feed"
            params = {"access_token": self.access_token}
            
            # Prepare post data
            post_data = {"message": text}
            
            # Add link if provided
            if "link" in kwargs:
                post_data["link"] = kwargs["link"]
                
            # Add place if provided
            if "place_id" in kwargs:
                post_data["place"] = kwargs["place_id"]
                
            # Add tags if provided
            if "tags" in kwargs:
                post_data["tags"] = ",".join(kwargs["tags"])
                
            # Schedule post if time provided
            if scheduled_time:
                post_data["scheduled_publish_time"] = int(scheduled_time.timestamp())
                post_data["published"] = False
            
            # Handle media uploads
            if media_paths and len(media_paths) > 0:
                # For simplicity, we'll handle different media types separately
                # In a production environment, you'd want more robust handling
                
                # Check first media type
                first_media = media_paths[0].lower()
                
                if first_media.endswith(('.mp4', '.mov')):
                    # Video upload
                    return self._post_video(text, media_paths[0], scheduled_time, **kwargs)
                elif first_media.endswith(('.jpg', '.jpeg', '.png')):
                    # Photo upload (single or multiple)
                    return self._post_photos(text, media_paths, scheduled_time, **kwargs)
                else:
                    # Unsupported media type, post as text only
                    logger.warning(f"Unsupported media type: {first_media}, posting as text only")
            
            # Post to Facebook
            response = requests.post(post_url, params=params, data=post_data)
            response.raise_for_status()
            result = response.json()
            
            if "id" in result:
                post_id = result["id"]
                logger.info(f"Facebook post created successfully: {post_id}")
                
                return {
                    "status": "success",
                    "post_id": post_id,
                    "platform": "facebook",
                    "url": f"https://facebook.com/{post_id}",
                    "posted_at": datetime.now().isoformat(),
                    "scheduled": scheduled_time.isoformat() if scheduled_time else None
                }
            else:
                logger.error(f"Failed to create Facebook post: {result}")
                return {"status": "failed", "error": "Invalid response", "platform": "facebook"}
                
        except Exception as e:
            logger.error(f"Failed to post to Facebook: {str(e)}")
            return {"status": "failed", "error": str(e), "platform": "facebook"}
    
    def get_post_status(self, post_id: str) -> Dict:
        """
        Get the status of a Facebook post.
        
        Args:
            post_id: ID of the post to check
            
        Returns:
            Dictionary with post status details
        """
        if not self.authenticate():
            return {"status": "failed", "error": "Authentication failed", "platform": "facebook"}
        
        try:
            url = f"{self.base_url}/{post_id}"
            params = {
                "access_token": self.access_token,
                "fields": "message,created_time,permalink_url,is_published,scheduled_publish_time"
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            status = "active" if data.get("is_published", True) else "scheduled"
            
            return {
                "status": status,
                "post_id": post_id,
                "platform": "facebook",
                "message": data.get("message"),
                "created_at": data.get("created_time"),
                "url": data.get("permalink_url"),
                "scheduled_time": data.get("scheduled_publish_time")
            }
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return {"status": "not_found", "post_id": post_id, "platform": "facebook"}
            else:
                logger.error(f"Failed to get Facebook post status: {str(e)}")
                return {"status": "error", "error": str(e), "platform": "facebook"}
        except Exception as e:
            logger.error(f"Failed to get Facebook post status: {str(e)}")
            return {"status": "error", "error": str(e), "platform": "facebook"}
    
    def delete_post(self, post_id: str) -> bool:
        """
        Delete a Facebook post.
        
        Args:
            post_id: ID of the post to delete
            
        Returns:
            True if deletion was successful, False otherwise
        """
        if not self.authenticate():
            return False
        
        try:
            url = f"{self.base_url}/{post_id}"
            params = {"access_token": self.access_token}
            
            response = requests.delete(url, params=params)
            response.raise_for_status()
            result = response.json()
            
            if result.get("success", False):
                logger.info(f"Facebook post {post_id} deleted successfully")
                return True
            else:
                logger.error(f"Failed to delete Facebook post: {result}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to delete Facebook post {post_id}: {str(e)}")
            return False
    
    def get_analytics(self, post_id: str) -> Dict:
        """
        Get analytics for a specific Facebook post.
        
        Args:
            post_id: ID of the post to get analytics for
            
        Returns:
            Dictionary with analytics data
        """
        if not self.authenticate():
            return {"status": "failed", "error": "Authentication failed", "platform": "facebook"}
        
        try:
            url = f"{self.base_url}/{post_id}/insights"
            params = {
                "access_token": self.access_token,
                "metric": "post_impressions,post_engagements,post_reactions_by_type_total"
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if "data" in data:
                metrics = {}
                for metric in data["data"]:
                    name = metric["name"]
                    values = metric["values"][0]["value"]
                    metrics[name] = values
                
                return {
                    "status": "success",
                    "post_id": post_id,
                    "platform": "facebook",
                    "metrics": metrics
                }
            else:
                logger.error(f"Failed to get Facebook post analytics: {data}")
                return {"status": "error", "error": "Invalid response", "platform": "facebook"}
                
        except Exception as e:
            logger.error(f"Failed to get Facebook post analytics: {str(e)}")
            return {"status": "error", "error": str(e), "platform": "facebook"}
    
    def _post_photos(self, text: str, photo_paths: List[str], scheduled_time: Optional[datetime] = None, **kwargs) -> Dict:
        """
        Post photos to Facebook.
        
        Args:
            text: The text content to post
            photo_paths: List of paths to photo files
            scheduled_time: Optional time to schedule the post
            **kwargs: Additional parameters
            
        Returns:
            Dictionary with post details
        """
        try:
            # For multiple photos, we need to use a different endpoint
            if len(photo_paths) > 1:
                # Create a post with multiple photos
                url = f"{self.base_url}/{self.page_id}/photos"
                params = {"access_token": self.access_token}
                
                # Upload each photo and get the IDs
                photo_ids = []
                for photo_path in photo_paths:
                    if not os.path.exists(photo_path):
                        logger.warning(f"Photo file not found: {photo_path}")
                        continue
                        
                    with open(photo_path, "rb") as photo_file:
                        upload_data = {
                            "source": photo_file,
                            "published": "false"  # Don't publish individual photos
                        }
                        upload_response = requests.post(url, params=params, files=upload_data)
                        upload_response.raise_for_status()
                        result = upload_response.json()
                        
                        if "id" in result:
                            photo_ids.append(result["id"])
                
                if not photo_ids:
                    logger.error("No photos were successfully uploaded")
                    return {"status": "failed", "error": "No photos uploaded", "platform": "facebook"}
                
                # Create a post with the uploaded photos
                post_url = f"{self.base_url}/{self.page_id}/feed"
                post_data = {
                    "message": text,
                    "attached_media": [{"media_fbid": photo_id} for photo_id in photo_ids]
                }
                
                # Schedule if needed
                if scheduled_time:
                    post_data["scheduled_publish_time"] = int(scheduled_time.timestamp())
                    post_data["published"] = False
                
                # Add additional parameters
                if "link" in kwargs:
                    post_data["link"] = kwargs["link"]
                    
                if "place_id" in kwargs:
                    post_data["place"] = kwargs["place_id"]
                    
                if "tags" in kwargs:
                    post_data["tags"] = ",".join(kwargs["tags"])
                
                # Create the post
                post_response = requests.post(post_url, params=params, data=post_data)
                post_response.raise_for_status()
                post_result = post_response.json()
                
                if "id" in post_result:
                    post_id = post_result["id"]
                    logger.info(f"Facebook photo post created successfully: {post_id}")
                    
                    return {
                        "status": "success",
                        "post_id": post_id,
                        "platform": "facebook",
                        "url": f"https://facebook.com/{post_id}",
                        "posted_at": datetime.now().isoformat(),
                        "scheduled": scheduled_time.isoformat() if scheduled_time else None,
                        "photo_count": len(photo_ids)
                    }
                else:
                    logger.error(f"Failed to create Facebook photo post: {post_result}")
                    return {"status": "failed", "error": "Invalid response", "platform": "facebook"}
            
            else:
                # Single photo upload
                url = f"{self.base_url}/{self.page_id}/photos"
                params = {"access_token": self.access_token}
                
                photo_path = photo_paths[0]
                if not os.path.exists(photo_path):
                    logger.error(f"Photo file not found: {photo_path}")
                    return {"status": "failed", "error": "Photo file not found", "platform": "facebook"}
                
                # Prepare post data
                post_data = {"message": text}
                
                # Schedule if needed
                if scheduled_time:
                    post_data["scheduled_publish_time"] = int(scheduled_time.timestamp())
                    post_data["published"] = False
                
                # Add additional parameters
                if "link" in kwargs:
                    post_data["link"] = kwargs["link"]
                    
                if "place_id" in kwargs:
                    post_data["place"] = kwargs["place_id"]
                    
                if "tags" in kwargs:
                    post_data["tags"] = ",".join(kwargs["tags"])
                
                # Upload the photo
                with open(photo_path, "rb") as photo_file:
                    files = {"source": photo_file}
                    response = requests.post(url, params=params, data=post_data, files=files)
                    response.raise_for_status()
                    result = response.json()
                
                if "id" in result:
                    post_id = result["post_id"] if "post_id" in result else result["id"]
                    logger.info(f"Facebook photo post created successfully: {post_id}")
                    
                    return {
                        "status": "success",
                        "post_id": post_id,
                        "platform": "facebook",
                        "url": f"https://facebook.com/{post_id}",
                        "posted_at": datetime.now().isoformat(),
                        "scheduled": scheduled_time.isoformat() if scheduled_time else None
                    }
                else:
                    logger.error(f"Failed to create Facebook photo post: {result}")
                    return {"status": "failed", "error": "Invalid response", "platform": "facebook"}
        
        except Exception as e:
            logger.error(f"Failed to post photos to Facebook: {str(e)}")
            return {"status": "failed", "error": str(e), "platform": "facebook"}
    
    def _post_video(self, text: str, video_path: str, scheduled_time: Optional[datetime] = None, **kwargs) -> Dict:
        """
        Post a video to Facebook.
        
        Args:
            text: The text content to post
            video_path: Path to the video file
            scheduled_time: Optional time to schedule the post
            **kwargs: Additional parameters
            
        Returns:
            Dictionary with post details
        """
        try:
            if not os.path.exists(video_path):
                logger.error(f"Video file not found: {video_path}")
                return {"status": "failed", "error": "Video file not found", "platform": "facebook"}
            
            # For videos, we use the videos endpoint
            url = f"{self.base_url}/{self.page_id}/videos"
            params = {"access_token": self.access_token}
            
            # Prepare post data
            post_data = {"description": text}
            
            # Schedule if needed
            if scheduled_time:
                post_data["scheduled_publish_time"] = int(scheduled_time.timestamp())
                post_data["published"] = False
            
            # Add title if provided
            if "title" in kwargs:
                post_data["title"] = kwargs["title"]
            
            # Upload the video
            with open(video_path, "rb") as video_file:
                files = {"source": video_file}
                response = requests.post(url, params=params, data=post_data, files=files)
                response.raise_for_status()
                result = response.json()
            
            if "id" in result:
                video_id = result["id"]
                logger.info(f"Facebook video post created successfully: {video_id}")
                
                return {
                    "status": "success",
                    "post_id": video_id,
                    "platform": "facebook",
                    "url": f"https://facebook.com/{video_id}",
                    "posted_at": datetime.now().isoformat(),
                    "scheduled": scheduled_time.isoformat() if scheduled_time else None
                }
            else:
                logger.error(f"Failed to create Facebook video post: {result}")
                return {"status": "failed", "error": "Invalid response", "platform": "facebook"}
        
        except Exception as e:
            logger.error(f"Failed to post video to Facebook: {str(e)}")
            return {"status": "failed", "error": str(e), "platform": "facebook"}
