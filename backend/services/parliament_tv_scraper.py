"""
Parliament TV Scraper

This module provides functionality to scrape the Parliament TV website
to find live or recent archived videos from the Commons.
"""

import logging
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple

# Configure logging
logger = logging.getLogger(__name__)

class ParliamentTVScraper:
    """
    Scraper for Parliament TV website to find live or recent videos.
    """
    
    COMMONS_URL = "https://www.parliamentlive.tv/Commons"
    
    def __init__(self):
        """Initialize the Parliament TV scraper."""
        self.session = requests.Session()
        # Set a reasonable timeout for requests
        self.timeout = 30
        # Set a user agent to mimic a browser
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def get_latest_video(self) -> Dict[str, Any]:
        """
        Get the latest video from the Parliament TV Commons page.
        
        Returns:
            Dict with video information including:
            - url: The URL of the video
            - title: The title of the video
            - is_live: Whether the video is currently live
            - timestamp: When the video was published/started
        """
        try:
            logger.info(f"Fetching Parliament TV Commons page: {self.COMMONS_URL}")
            response = self.session.get(self.COMMONS_URL, timeout=self.timeout)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # First check for live videos
            live_video = self._extract_live_video(soup)
            if live_video:
                logger.info(f"Found live video: {live_video['title']}")
                return live_video
            
            # If no live video, get the most recent archived video
            recent_video = self._extract_recent_video(soup)
            if recent_video:
                logger.info(f"Found recent video: {recent_video['title']}")
                return recent_video
            
            logger.warning("No live or recent videos found on Parliament TV Commons page")
            return {
                "url": None,
                "title": None,
                "is_live": False,
                "timestamp": None,
                "error": "No videos found"
            }
            
        except Exception as e:
            logger.error(f"Error scraping Parliament TV Commons page: {str(e)}")
            return {
                "url": None,
                "title": None,
                "is_live": False,
                "timestamp": None,
                "error": str(e)
            }
    
    def _extract_live_video(self, soup: BeautifulSoup) -> Optional[Dict[str, Any]]:
        """
        Extract information about a currently live video from the Commons page.
        
        Args:
            soup: BeautifulSoup object of the Commons page
            
        Returns:
            Dict with video information or None if no live video found
        """
        try:
            # Look for elements that indicate a live broadcast
            live_indicators = [
                soup.select_one('.live-now'),
                soup.select_one('.live-indicator'),
                soup.select_one('[data-status="live"]')
            ]
            
            live_element = next((el for el in live_indicators if el is not None), None)
            
            if not live_element:
                logger.info("No live video indicators found")
                return None
            
            # Find the parent element that contains the video link
            video_container = None
            current = live_element
            
            # Traverse up to find the container with the link
            for _ in range(5):  # Limit the number of parent traversals
                if current is None:
                    break
                
                # Check if this element or any of its children has a link
                links = current.select('a')
                if links:
                    video_container = current
                    break
                
                current = current.parent
            
            if not video_container:
                logger.warning("Found live indicator but couldn't locate the video container")
                return None
            
            # Extract the video link
            video_link = video_container.select_one('a[href*="/event/index/"]')
            if not video_link:
                logger.warning("Found live indicator but couldn't locate the video link")
                return None
            
            video_url = video_link.get('href')
            if not video_url.startswith('http'):
                video_url = f"https://www.parliamentlive.tv{video_url}"
            
            # Extract the title
            title_element = video_container.select_one('.event-title, .title, h3, h4')
            title = title_element.get_text(strip=True) if title_element else "Live Commons Debate"
            
            # Extract timestamp if available
            timestamp_element = video_container.select_one('.timestamp, .date, time')
            timestamp = None
            if timestamp_element:
                timestamp_text = timestamp_element.get_text(strip=True)
                # Try to parse the timestamp (format may vary)
                try:
                    timestamp = datetime.strptime(timestamp_text, "%d/%m/%Y %H:%M:%S")
                except ValueError:
                    try:
                        timestamp = datetime.strptime(timestamp_text, "%d/%m/%Y %H:%M")
                    except ValueError:
                        timestamp = datetime.now()  # Fallback to current time
            else:
                timestamp = datetime.now()
            
            return {
                "url": video_url,
                "title": title,
                "is_live": True,
                "timestamp": timestamp
            }
            
        except Exception as e:
            logger.error(f"Error extracting live video: {str(e)}")
            return None
    
    def _extract_recent_video(self, soup: BeautifulSoup) -> Optional[Dict[str, Any]]:
        """
        Extract information about the most recent archived video from the Commons page.
        
        Args:
            soup: BeautifulSoup object of the Commons page
            
        Returns:
            Dict with video information or None if no recent video found
        """
        try:
            # Look for video containers
            video_containers = soup.select('.event-item, .video-item, .archive-item')
            
            if not video_containers:
                logger.warning("No video containers found")
                return None
            
            # Get the first (most recent) video
            video_container = video_containers[0]
            
            # Extract the video link
            video_link = video_container.select_one('a[href*="/event/index/"]')
            if not video_link:
                logger.warning("Couldn't locate the video link in the container")
                return None
            
            video_url = video_link.get('href')
            if not video_url.startswith('http'):
                video_url = f"https://www.parliamentlive.tv{video_url}"
            
            # Extract the title
            title_element = video_container.select_one('.event-title, .title, h3, h4')
            title = title_element.get_text(strip=True) if title_element else "Commons Debate"
            
            # Extract timestamp if available
            timestamp_element = video_container.select_one('.timestamp, .date, time')
            timestamp = None
            if timestamp_element:
                timestamp_text = timestamp_element.get_text(strip=True)
                # Try to parse the timestamp (format may vary)
                try:
                    timestamp = datetime.strptime(timestamp_text, "%d/%m/%Y %H:%M:%S")
                except ValueError:
                    try:
                        timestamp = datetime.strptime(timestamp_text, "%d/%m/%Y %H:%M")
                    except ValueError:
                        timestamp = datetime.now()  # Fallback to current time
            
            return {
                "url": video_url,
                "title": title,
                "is_live": False,
                "timestamp": timestamp
            }
            
        except Exception as e:
            logger.error(f"Error extracting recent video: {str(e)}")
            return None
