import logging
import os
from typing import Dict, List, Optional, Any, Union
from datetime import datetime

from backend.core.config import settings
from backend.services.social.base import SocialMediaPlatform
from backend.services.social.twitter import TwitterPlatform
from backend.services.social.facebook import FacebookPlatform
from backend.services.social.instagram import InstagramPlatform

logger = logging.getLogger(__name__)

class SocialMediaManager:
    """
    Manager for coordinating social media posts across multiple platforms.
    Handles authentication, posting, and analytics for all connected platforms.
    """
    
    def __init__(self):
        self.platforms = {}
        self._initialize_platforms()
        
    def _initialize_platforms(self):
        """Initialize all configured social media platforms."""
        # Initialize Twitter if configured
        if settings.TWITTER_API_KEY and settings.TWITTER_API_SECRET:
            self.platforms["twitter"] = TwitterPlatform()
            logger.info("Twitter platform initialized")
            
        # Initialize Facebook if configured
        if settings.FACEBOOK_APP_ID and settings.FACEBOOK_APP_SECRET:
            self.platforms["facebook"] = FacebookPlatform()
            logger.info("Facebook platform initialized")
            
        # Initialize Instagram if configured
        if settings.INSTAGRAM_ACCESS_TOKEN:
            self.platforms["instagram"] = InstagramPlatform()
            logger.info("Instagram platform initialized")
            
        logger.info(f"Social Media Manager initialized with {len(self.platforms)} platforms")
    
    def get_platform(self, platform_name: str) -> Optional[SocialMediaPlatform]:
        """
        Get a specific platform by name.
        
        Args:
            platform_name: Name of the platform to retrieve
            
        Returns:
            Platform instance or None if not found
        """
        platform = self.platforms.get(platform_name.lower())
        if not platform:
            logger.warning(f"Platform '{platform_name}' not found or not configured")
        return platform
    
    def authenticate_all(self) -> Dict[str, bool]:
        """
        Authenticate with all configured platforms.
        
        Returns:
            Dictionary mapping platform names to authentication status
        """
        results = {}
        for name, platform in self.platforms.items():
            try:
                results[name] = platform.authenticate()
            except Exception as e:
                logger.error(f"Error authenticating with {name}: {str(e)}")
                results[name] = False
        
        return results
    
    def post_content(self, 
                     text: str, 
                     platforms: List[str], 
                     media_paths: Optional[List[str]] = None,
                     scheduled_time: Optional[datetime] = None,
                     platform_specific_params: Optional[Dict[str, Dict]] = None) -> Dict[str, Dict]:
        """
        Post content to multiple social media platforms.
        
        Args:
            text: The text content to post
            platforms: List of platform names to post to
            media_paths: Optional list of paths to media files
            scheduled_time: Optional time to schedule the post
            platform_specific_params: Optional dictionary mapping platform names to 
                                     platform-specific parameters
                                     
        Returns:
            Dictionary mapping platform names to post results
        """
        results = {}
        platform_specific_params = platform_specific_params or {}
        
        for platform_name in platforms:
            platform = self.get_platform(platform_name)
            if not platform:
                results[platform_name] = {
                    "status": "failed", 
                    "error": "Platform not found or not configured",
                    "platform": platform_name
                }
                continue
            
            try:
                # Get platform-specific parameters
                params = platform_specific_params.get(platform_name, {})
                
                # Post to the platform
                result = platform.post_content(
                    text=text,
                    media_paths=media_paths,
                    scheduled_time=scheduled_time,
                    **params
                )
                
                results[platform_name] = result
                
            except Exception as e:
                logger.error(f"Error posting to {platform_name}: {str(e)}")
                results[platform_name] = {
                    "status": "failed",
                    "error": str(e),
                    "platform": platform_name
                }
        
        return results
    
    def get_post_status(self, platform_name: str, post_id: str) -> Dict:
        """
        Get the status of a post on a specific platform.
        
        Args:
            platform_name: Name of the platform
            post_id: ID of the post to check
            
        Returns:
            Dictionary with post status details
        """
        platform = self.get_platform(platform_name)
        if not platform:
            return {
                "status": "failed", 
                "error": "Platform not found or not configured",
                "platform": platform_name
            }
        
        try:
            return platform.get_post_status(post_id)
        except Exception as e:
            logger.error(f"Error getting post status from {platform_name}: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "platform": platform_name,
                "post_id": post_id
            }
    
    def delete_post(self, platform_name: str, post_id: str) -> bool:
        """
        Delete a post from a specific platform.
        
        Args:
            platform_name: Name of the platform
            post_id: ID of the post to delete
            
        Returns:
            True if deletion was successful, False otherwise
        """
        platform = self.get_platform(platform_name)
        if not platform:
            logger.error(f"Platform '{platform_name}' not found or not configured")
            return False
        
        try:
            return platform.delete_post(post_id)
        except Exception as e:
            logger.error(f"Error deleting post from {platform_name}: {str(e)}")
            return False
    
    def get_analytics(self, platform_name: str, post_id: str) -> Dict:
        """
        Get analytics for a specific post.
        
        Args:
            platform_name: Name of the platform
            post_id: ID of the post to get analytics for
            
        Returns:
            Dictionary with analytics data
        """
        platform = self.get_platform(platform_name)
        if not platform:
            return {
                "status": "failed", 
                "error": "Platform not found or not configured",
                "platform": platform_name
            }
        
        try:
            return platform.get_analytics(post_id)
        except Exception as e:
            logger.error(f"Error getting analytics from {platform_name}: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "platform": platform_name,
                "post_id": post_id
            }
    
    def get_platform_status(self) -> Dict[str, bool]:
        """
        Get the status of all configured platforms.
        
        Returns:
            Dictionary mapping platform names to availability status
        """
        status = {}
        for name, platform in self.platforms.items():
            try:
                status[name] = platform.authenticate()
            except Exception:
                status[name] = False
        
        return status
