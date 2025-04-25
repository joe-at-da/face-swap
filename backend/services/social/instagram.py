import logging
import os
import json
import requests
from typing import Dict, List, Optional, Any
from datetime import datetime

from backend.core.config import settings
from backend.services.social.base import SocialMediaPlatform

logger = logging.getLogger(__name__)

class InstagramPlatform(SocialMediaPlatform):
    """Instagram platform integration using the Facebook Graph API."""
    
    def __init__(self):
        super().__init__()
        self.access_token = settings.INSTAGRAM_ACCESS_TOKEN
        self.instagram_account_id = settings.INSTAGRAM_ACCOUNT_ID
        self.api_version = "v16.0"  # Use appropriate API version
        self.base_url = f"https://graph.facebook.com/{self.api_version}"
        
    def authenticate(self) -> bool:
        """
        Verify Instagram authentication credentials.
        
        Returns:
            True if authentication was successful, False otherwise
        """
        try:
            # Verify access token by making a simple API call
            url = f"{self.base_url}/{self.instagram_account_id}"
            params = {
                "access_token": self.access_token,
                "fields": "username,name"
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            if "id" in data:
                logger.info(f"Instagram authentication successful for account {data.get('username', 'Unknown')}")
                return True
            else:
                logger.error("Instagram authentication failed: Invalid response")
                return False
                
        except Exception as e:
            logger.error(f"Instagram authentication failed: {str(e)}")
            return False
    
    def post_content(self, 
                     text: str, 
                     media_paths: Optional[List[str]] = None, 
                     scheduled_time: Optional[datetime] = None,
                     **kwargs) -> Dict:
        """
        Post content to Instagram.
        
        Args:
            text: The caption text for the post
            media_paths: List of paths to media files (required for Instagram)
            scheduled_time: Optional time to schedule the post
            **kwargs: Additional Instagram-specific parameters
                - location_id: ID of a location to tag
                - user_tags: List of user IDs to tag in the post
                
        Returns:
            Dictionary with post details including ID and status
        """
        if not self.authenticate():
            return {"status": "failed", "error": "Authentication failed", "platform": "instagram"}
        
        try:
            # Instagram requires media for posts
            if not media_paths or len(media_paths) == 0:
                logger.error("Instagram posts require at least one media file")
                return {"status": "failed", "error": "Media required for Instagram posts", "platform": "instagram"}
            
            # Determine post type based on media count
            if len(media_paths) == 1:
                # Single media post
                media_path = media_paths[0].lower()
                
                if media_path.endswith(('.mp4', '.mov')):
                    # Video post
                    return self._post_video(text, media_paths[0], scheduled_time, **kwargs)
                else:
                    # Image post
                    return self._post_image(text, media_paths[0], scheduled_time, **kwargs)
            else:
                # Carousel post (multiple media)
                return self._post_carousel(text, media_paths, scheduled_time, **kwargs)
                
        except Exception as e:
            logger.error(f"Failed to post to Instagram: {str(e)}")
            return {"status": "failed", "error": str(e), "platform": "instagram"}
    
    def get_post_status(self, post_id: str) -> Dict:
        """
        Get the status of an Instagram post.
        
        Args:
            post_id: ID of the post to check
            
        Returns:
            Dictionary with post status details
        """
        if not self.authenticate():
            return {"status": "failed", "error": "Authentication failed", "platform": "instagram"}
        
        try:
            url = f"{self.base_url}/{post_id}"
            params = {
                "access_token": self.access_token,
                "fields": "caption,timestamp,permalink,media_type,media_url,thumbnail_url"
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            return {
                "status": "active",
                "post_id": post_id,
                "platform": "instagram",
                "caption": data.get("caption"),
                "created_at": data.get("timestamp"),
                "url": data.get("permalink"),
                "media_type": data.get("media_type"),
                "media_url": data.get("media_url"),
                "thumbnail_url": data.get("thumbnail_url")
            }
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return {"status": "not_found", "post_id": post_id, "platform": "instagram"}
            else:
                logger.error(f"Failed to get Instagram post status: {str(e)}")
                return {"status": "error", "error": str(e), "platform": "instagram"}
        except Exception as e:
            logger.error(f"Failed to get Instagram post status: {str(e)}")
            return {"status": "error", "error": str(e), "platform": "instagram"}
    
    def delete_post(self, post_id: str) -> bool:
        """
        Delete an Instagram post.
        
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
                logger.info(f"Instagram post {post_id} deleted successfully")
                return True
            else:
                logger.error(f"Failed to delete Instagram post: {result}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to delete Instagram post {post_id}: {str(e)}")
            return False
    
    def get_analytics(self, post_id: str) -> Dict:
        """
        Get analytics for a specific Instagram post.
        
        Args:
            post_id: ID of the post to get analytics for
            
        Returns:
            Dictionary with analytics data
        """
        if not self.authenticate():
            return {"status": "failed", "error": "Authentication failed", "platform": "instagram"}
        
        try:
            url = f"{self.base_url}/{post_id}/insights"
            params = {
                "access_token": self.access_token,
                "metric": "engagement,impressions,reach,saved"
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
                    "platform": "instagram",
                    "metrics": metrics
                }
            else:
                logger.error(f"Failed to get Instagram post analytics: {data}")
                return {"status": "error", "error": "Invalid response", "platform": "instagram"}
                
        except Exception as e:
            logger.error(f"Failed to get Instagram post analytics: {str(e)}")
            return {"status": "error", "error": str(e), "platform": "instagram"}
    
    def _post_image(self, caption: str, image_path: str, scheduled_time: Optional[datetime] = None, **kwargs) -> Dict:
        """
        Post a single image to Instagram.
        
        Args:
            caption: The caption text for the post
            image_path: Path to the image file
            scheduled_time: Optional time to schedule the post
            **kwargs: Additional parameters
            
        Returns:
            Dictionary with post details
        """
        try:
            if not os.path.exists(image_path):
                logger.error(f"Image file not found: {image_path}")
                return {"status": "failed", "error": "Image file not found", "platform": "instagram"}
            
            # Step 1: Upload the image to get a container ID
            container_url = f"{self.base_url}/{self.instagram_account_id}/media"
            container_params = {"access_token": self.access_token}
            
            container_data = {
                "image_url": self._get_image_url(image_path),
                "caption": caption
            }
            
            # Add location if provided
            if "location_id" in kwargs:
                container_data["location_id"] = kwargs["location_id"]
            
            # Add user tags if provided
            if "user_tags" in kwargs and kwargs["user_tags"]:
                user_tags = []
                for tag in kwargs["user_tags"]:
                    user_tags.append({
                        "username": tag["username"],
                        "x": tag.get("x", 0.5),
                        "y": tag.get("y", 0.5)
                    })
                container_data["user_tags"] = json.dumps(user_tags)
            
            container_response = requests.post(container_url, params=container_params, data=container_data)
            container_response.raise_for_status()
            container_result = container_response.json()
            
            if "id" not in container_result:
                logger.error(f"Failed to create Instagram media container: {container_result}")
                return {"status": "failed", "error": "Failed to create media container", "platform": "instagram"}
            
            container_id = container_result["id"]
            
            # Step 2: Publish the container
            publish_url = f"{self.base_url}/{self.instagram_account_id}/media_publish"
            publish_params = {"access_token": self.access_token}
            publish_data = {"creation_id": container_id}
            
            publish_response = requests.post(publish_url, params=publish_params, data=publish_data)
            publish_response.raise_for_status()
            publish_result = publish_response.json()
            
            if "id" in publish_result:
                post_id = publish_result["id"]
                logger.info(f"Instagram image post created successfully: {post_id}")
                
                return {
                    "status": "success",
                    "post_id": post_id,
                    "platform": "instagram",
                    "posted_at": datetime.now().isoformat(),
                    "media_type": "IMAGE"
                }
            else:
                logger.error(f"Failed to publish Instagram image: {publish_result}")
                return {"status": "failed", "error": "Failed to publish media", "platform": "instagram"}
        
        except Exception as e:
            logger.error(f"Failed to post image to Instagram: {str(e)}")
            return {"status": "failed", "error": str(e), "platform": "instagram"}
    
    def _post_video(self, caption: str, video_path: str, scheduled_time: Optional[datetime] = None, **kwargs) -> Dict:
        """
        Post a video to Instagram.
        
        Args:
            caption: The caption text for the post
            video_path: Path to the video file
            scheduled_time: Optional time to schedule the post
            **kwargs: Additional parameters
            
        Returns:
            Dictionary with post details
        """
        try:
            if not os.path.exists(video_path):
                logger.error(f"Video file not found: {video_path}")
                return {"status": "failed", "error": "Video file not found", "platform": "instagram"}
            
            # For Instagram videos, we need:
            # 1. Upload the video to get a container ID
            # 2. Check the upload status until it's ready
            # 3. Publish the container
            
            # Step 1: Upload the video
            container_url = f"{self.base_url}/{self.instagram_account_id}/media"
            container_params = {"access_token": self.access_token}
            
            container_data = {
                "media_type": "VIDEO",
                "video_url": self._get_video_url(video_path),
                "caption": caption
            }
            
            # Add thumbnail if provided
            if "thumbnail_url" in kwargs:
                container_data["thumbnail_url"] = kwargs["thumbnail_url"]
            
            # Add location if provided
            if "location_id" in kwargs:
                container_data["location_id"] = kwargs["location_id"]
            
            container_response = requests.post(container_url, params=container_params, data=container_data)
            container_response.raise_for_status()
            container_result = container_response.json()
            
            if "id" not in container_result:
                logger.error(f"Failed to create Instagram video container: {container_result}")
                return {"status": "failed", "error": "Failed to create video container", "platform": "instagram"}
            
            container_id = container_result["id"]
            
            # Step 2: Check upload status (in production, you'd implement a polling mechanism)
            # For simplicity, we'll assume the upload is ready
            
            # Step 3: Publish the container
            publish_url = f"{self.base_url}/{self.instagram_account_id}/media_publish"
            publish_params = {"access_token": self.access_token}
            publish_data = {"creation_id": container_id}
            
            publish_response = requests.post(publish_url, params=publish_params, data=publish_data)
            publish_response.raise_for_status()
            publish_result = publish_response.json()
            
            if "id" in publish_result:
                post_id = publish_result["id"]
                logger.info(f"Instagram video post created successfully: {post_id}")
                
                return {
                    "status": "success",
                    "post_id": post_id,
                    "platform": "instagram",
                    "posted_at": datetime.now().isoformat(),
                    "media_type": "VIDEO"
                }
            else:
                logger.error(f"Failed to publish Instagram video: {publish_result}")
                return {"status": "failed", "error": "Failed to publish video", "platform": "instagram"}
        
        except Exception as e:
            logger.error(f"Failed to post video to Instagram: {str(e)}")
            return {"status": "failed", "error": str(e), "platform": "instagram"}
    
    def _post_carousel(self, caption: str, media_paths: List[str], scheduled_time: Optional[datetime] = None, **kwargs) -> Dict:
        """
        Post a carousel (multiple media) to Instagram.
        
        Args:
            caption: The caption text for the post
            media_paths: List of paths to media files
            scheduled_time: Optional time to schedule the post
            **kwargs: Additional parameters
            
        Returns:
            Dictionary with post details
        """
        try:
            # Step 1: Create media containers for each item
            children = []
            
            for media_path in media_paths:
                if not os.path.exists(media_path):
                    logger.warning(f"Media file not found: {media_path}")
                    continue
                
                # Determine media type
                is_video = media_path.lower().endswith(('.mp4', '.mov'))
                
                # Create child container
                child_url = f"{self.base_url}/{self.instagram_account_id}/media"
                child_params = {"access_token": self.access_token}
                
                child_data = {
                    "is_carousel_item": "true",
                    "media_type": "VIDEO" if is_video else "IMAGE"
                }
                
                if is_video:
                    child_data["video_url"] = self._get_video_url(media_path)
                    
                    # Add thumbnail if provided
                    if f"thumbnail_url_{len(children)}" in kwargs:
                        child_data["thumbnail_url"] = kwargs[f"thumbnail_url_{len(children)}"]
                else:
                    child_data["image_url"] = self._get_image_url(media_path)
                
                child_response = requests.post(child_url, params=child_params, data=child_data)
                child_response.raise_for_status()
                child_result = child_response.json()
                
                if "id" in child_result:
                    children.append(child_result["id"])
                else:
                    logger.warning(f"Failed to create carousel item: {child_result}")
            
            if not children:
                logger.error("No valid media items for carousel")
                return {"status": "failed", "error": "No valid media items", "platform": "instagram"}
            
            # Step 2: Create the carousel container
            carousel_url = f"{self.base_url}/{self.instagram_account_id}/media"
            carousel_params = {"access_token": self.access_token}
            
            carousel_data = {
                "media_type": "CAROUSEL",
                "caption": caption,
                "children": ",".join(children)
            }
            
            # Add location if provided
            if "location_id" in kwargs:
                carousel_data["location_id"] = kwargs["location_id"]
            
            carousel_response = requests.post(carousel_url, params=carousel_params, data=carousel_data)
            carousel_response.raise_for_status()
            carousel_result = carousel_response.json()
            
            if "id" not in carousel_result:
                logger.error(f"Failed to create Instagram carousel container: {carousel_result}")
                return {"status": "failed", "error": "Failed to create carousel container", "platform": "instagram"}
            
            carousel_id = carousel_result["id"]
            
            # Step 3: Publish the carousel
            publish_url = f"{self.base_url}/{self.instagram_account_id}/media_publish"
            publish_params = {"access_token": self.access_token}
            publish_data = {"creation_id": carousel_id}
            
            publish_response = requests.post(publish_url, params=publish_params, data=publish_data)
            publish_response.raise_for_status()
            publish_result = publish_response.json()
            
            if "id" in publish_result:
                post_id = publish_result["id"]
                logger.info(f"Instagram carousel post created successfully: {post_id}")
                
                return {
                    "status": "success",
                    "post_id": post_id,
                    "platform": "instagram",
                    "posted_at": datetime.now().isoformat(),
                    "media_type": "CAROUSEL",
                    "item_count": len(children)
                }
            else:
                logger.error(f"Failed to publish Instagram carousel: {publish_result}")
                return {"status": "failed", "error": "Failed to publish carousel", "platform": "instagram"}
        
        except Exception as e:
            logger.error(f"Failed to post carousel to Instagram: {str(e)}")
            return {"status": "failed", "error": str(e), "platform": "instagram"}
    
    def _get_image_url(self, image_path: str) -> str:
        """
        In a real implementation, this would upload the image to a temporary
        publicly accessible URL for Instagram to fetch. For this example,
        we'll return a placeholder.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Public URL to the image
        """
        # In production, you would:
        # 1. Upload the image to S3 or similar storage
        # 2. Return the public URL
        
        # For this example, we'll return a placeholder
        return f"https://example.com/temp/{os.path.basename(image_path)}"
    
    def _get_video_url(self, video_path: str) -> str:
        """
        In a real implementation, this would upload the video to a temporary
        publicly accessible URL for Instagram to fetch. For this example,
        we'll return a placeholder.
        
        Args:
            video_path: Path to the video file
            
        Returns:
            Public URL to the video
        """
        # In production, you would:
        # 1. Upload the video to S3 or similar storage
        # 2. Return the public URL
        
        # For this example, we'll return a placeholder
        return f"https://example.com/temp/{os.path.basename(video_path)}"
