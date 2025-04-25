import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from datetime import datetime

from backend.core.config import settings

logger = logging.getLogger(__name__)

class SocialMediaPlatform(ABC):
    """Base abstract class for all social media platform integrations."""
    
    def __init__(self):
        self.platform_name = self.__class__.__name__
        logger.info(f"Initializing {self.platform_name} integration")
    
    @abstractmethod
    def authenticate(self) -> bool:
        """
        Authenticate with the social media platform.
        
        Returns:
            True if authentication was successful, False otherwise
        """
        pass
    
    @abstractmethod
    def post_content(self, 
                     text: str, 
                     media_paths: Optional[List[str]] = None, 
                     scheduled_time: Optional[datetime] = None,
                     **kwargs) -> Dict:
        """
        Post content to the social media platform.
        
        Args:
            text: The text content to post
            media_paths: Optional list of paths to media files to include
            scheduled_time: Optional time to schedule the post
            **kwargs: Additional platform-specific parameters
            
        Returns:
            Dictionary with post details including ID and status
        """
        pass
    
    @abstractmethod
    def get_post_status(self, post_id: str) -> Dict:
        """
        Get the status of a post.
        
        Args:
            post_id: ID of the post to check
            
        Returns:
            Dictionary with post status details
        """
        pass
    
    @abstractmethod
    def delete_post(self, post_id: str) -> bool:
        """
        Delete a post from the platform.
        
        Args:
            post_id: ID of the post to delete
            
        Returns:
            True if deletion was successful, False otherwise
        """
        pass
    
    @abstractmethod
    def get_analytics(self, post_id: str) -> Dict:
        """
        Get analytics for a specific post.
        
        Args:
            post_id: ID of the post to get analytics for
            
        Returns:
            Dictionary with analytics data
        """
        pass
