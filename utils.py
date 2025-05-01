"""
Utility functions for services
"""
from datetime import datetime
from typing import Any, Dict, List, Union


def make_json_serializable(obj: Any) -> Any:
    """
    Convert objects to JSON serializable format
    
    Args:
        obj: The object to convert
        
    Returns:
        JSON serializable version of the object
    """
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: make_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [make_json_serializable(item) for item in obj]
    elif hasattr(obj, "__dict__"):
        return make_json_serializable(obj.__dict__)
    else:
        return obj


def format_timestamp(seconds: float) -> str:
    """
    Format seconds into HH:MM:SS.mmm format
    
    Args:
        seconds: Time in seconds
        
    Returns:
        Formatted timestamp string
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:06.3f}".replace(".", ",")


def parse_timestamp(timestamp: str) -> float:
    """
    Parse HH:MM:SS.mmm format to seconds
    
    Args:
        timestamp: Timestamp string in HH:MM:SS.mmm format
        
    Returns:
        Time in seconds
    """
    timestamp = timestamp.replace(",", ".")
    parts = timestamp.split(":")
    
    if len(parts) == 3:
        hours, minutes, seconds = parts
        return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    elif len(parts) == 2:
        minutes, seconds = parts
        return int(minutes) * 60 + float(seconds)
    else:
        return float(parts[0])
