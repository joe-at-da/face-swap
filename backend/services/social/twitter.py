import logging
import os
import tempfile
from typing import Dict, List, Optional, Any
from datetime import datetime
import tweepy

from backend.core.config import settings
from backend.services.social.base import SocialMediaPlatform

logger = logging.getLogger(__name__)

class TwitterPlatform(SocialMediaPlatform):
    """Twitter platform integration using Tweepy."""
    
    def __init__(self):
        super().__init__()
        self.api_key = settings.TWITTER_API_KEY
        self.api_secret = settings.TWITTER_API_SECRET
        self.access_token = settings.TWITTER_ACCESS_TOKEN
        self.access_token_secret = settings.TWITTER_ACCESS_TOKEN_SECRET
        self.client = None
        self.api = None
        
    def authenticate(self) -> bool:
        """
        Authenticate with Twitter using API credentials.
        
        Returns:
            True if authentication was successful, False otherwise
        """
        try:
            # Initialize the Twitter API v2 client
            self.client = tweepy.Client(
                consumer_key=self.api_key,
                consumer_secret=self.api_secret,
                access_token=self.access_token,
                access_token_secret=self.access_token_secret
            )
            
            # For media uploads, we still need v1.1 API
            auth = tweepy.OAuth1UserHandler(
                self.api_key,
                self.api_secret,
                self.access_token,
                self.access_token_secret
            )
            self.api = tweepy.API(auth)
            
            # Verify credentials
            self.api.verify_credentials()
            logger.info("Twitter authentication successful")
            return True
            
        except Exception as e:
            logger.error(f"Twitter authentication failed: {str(e)}")
            return False
    
    def post_content(self, 
                     text: str, 
                     media_paths: Optional[List[str]] = None, 
                     scheduled_time: Optional[datetime] = None,
                     **kwargs) -> Dict:
        """
        Post content to Twitter.
        
        Args:
            text: The text content to tweet (max 280 chars)
            media_paths: Optional list of paths to media files to include
            scheduled_time: Optional time to schedule the tweet
            **kwargs: Additional Twitter-specific parameters
                - reply_to: ID of tweet to reply to
                - quote_tweet: ID of tweet to quote
                
        Returns:
            Dictionary with tweet details including ID and status
        """
        if not self.client or not self.api:
            if not self.authenticate():
                return {"status": "failed", "error": "Authentication failed"}
        
        try:
            # Truncate text if needed
            if len(text) > 280:
                logger.warning(f"Tweet text too long ({len(text)} chars), truncating to 280 chars")
                text = text[:277] + "..."
            
            # Handle media uploads
            media_ids = []
            if media_paths and len(media_paths) > 0:
                for media_path in media_paths[:4]:  # Twitter allows up to 4 media items
                    try:
                        if os.path.exists(media_path):
                            # Check file type
                            if media_path.lower().endswith(('.mp4', '.mov')):
                                # Video upload
                                media_id = self._upload_video(media_path)
                            else:
                                # Image upload
                                media_id = self.api.media_upload(media_path).media_id
                            
                            if media_id:
                                media_ids.append(media_id)
                                logger.info(f"Uploaded media: {media_path}")
                            
                    except Exception as e:
                        logger.error(f"Failed to upload media {media_path}: {str(e)}")
            
            # Get additional parameters
            reply_to = kwargs.get('reply_to')
            quote_tweet = kwargs.get('quote_tweet')
            
            # Create the tweet
            if scheduled_time:
                # For scheduled tweets, we'd use a different approach
                # This is a placeholder as Twitter API doesn't directly support scheduling
                logger.warning("Twitter API doesn't support scheduled tweets directly")
                
            # Post the tweet
            response = self.client.create_tweet(
                text=text,
                media_ids=media_ids if media_ids else None,
                in_reply_to_tweet_id=reply_to,
                quote_tweet_id=quote_tweet
            )
            
            tweet_id = response.data['id']
            logger.info(f"Tweet posted successfully: {tweet_id}")
            
            return {
                "status": "success",
                "post_id": tweet_id,
                "platform": "twitter",
                "url": f"https://twitter.com/user/status/{tweet_id}",
                "posted_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to post tweet: {str(e)}")
            return {"status": "failed", "error": str(e), "platform": "twitter"}
    
    def get_post_status(self, post_id: str) -> Dict:
        """
        Get the status of a tweet.
        
        Args:
            post_id: ID of the tweet to check
            
        Returns:
            Dictionary with tweet status details
        """
        if not self.client:
            if not self.authenticate():
                return {"status": "failed", "error": "Authentication failed"}
        
        try:
            tweet = self.client.get_tweet(post_id, expansions=["author_id"], 
                                         tweet_fields=["created_at", "public_metrics"])
            
            if not tweet.data:
                return {"status": "not_found", "post_id": post_id, "platform": "twitter"}
            
            return {
                "status": "active",
                "post_id": post_id,
                "platform": "twitter",
                "created_at": tweet.data.created_at,
                "metrics": tweet.data.public_metrics,
                "author_id": tweet.data.author_id
            }
            
        except Exception as e:
            logger.error(f"Failed to get tweet status: {str(e)}")
            return {"status": "error", "error": str(e), "platform": "twitter"}
    
    def delete_post(self, post_id: str) -> bool:
        """
        Delete a tweet.
        
        Args:
            post_id: ID of the tweet to delete
            
        Returns:
            True if deletion was successful, False otherwise
        """
        if not self.client:
            if not self.authenticate():
                return False
        
        try:
            self.client.delete_tweet(post_id)
            logger.info(f"Tweet {post_id} deleted successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete tweet {post_id}: {str(e)}")
            return False
    
    def get_analytics(self, post_id: str) -> Dict:
        """
        Get analytics for a specific tweet.
        
        Args:
            post_id: ID of the tweet to get analytics for
            
        Returns:
            Dictionary with analytics data
        """
        if not self.client:
            if not self.authenticate():
                return {"status": "failed", "error": "Authentication failed"}
        
        try:
            tweet = self.client.get_tweet(post_id, 
                                         tweet_fields=["public_metrics", "non_public_metrics", 
                                                      "organic_metrics", "promoted_metrics"])
            
            if not tweet.data:
                return {"status": "not_found", "post_id": post_id, "platform": "twitter"}
            
            metrics = {
                "public": tweet.data.public_metrics,
            }
            
            # These metrics are only available to the tweet author
            if hasattr(tweet.data, "non_public_metrics"):
                metrics["non_public"] = tweet.data.non_public_metrics
            
            if hasattr(tweet.data, "organic_metrics"):
                metrics["organic"] = tweet.data.organic_metrics
                
            if hasattr(tweet.data, "promoted_metrics"):
                metrics["promoted"] = tweet.data.promoted_metrics
            
            return {
                "status": "success",
                "post_id": post_id,
                "platform": "twitter",
                "metrics": metrics
            }
            
        except Exception as e:
            logger.error(f"Failed to get tweet analytics: {str(e)}")
            return {"status": "error", "error": str(e), "platform": "twitter"}
    
    def _upload_video(self, video_path: str) -> Optional[str]:
        """
        Upload a video to Twitter.
        
        Args:
            video_path: Path to the video file
            
        Returns:
            Media ID if successful, None otherwise
        """
        try:
            # Twitter has specific requirements for videos
            # This is a simplified version - in production you'd need to:
            # 1. Check video format and transcode if needed
            # 2. Use chunked upload for larger videos
            # 3. Handle video metadata
            
            # For now, we'll use the simple media_upload for smaller videos
            media = self.api.media_upload(
                video_path,
                media_category='tweet_video'
            )
            
            return media.media_id
            
        except Exception as e:
            logger.error(f"Failed to upload video: {str(e)}")
            return None
