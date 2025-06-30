"""
Utility functions for services
"""
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Union, Set, Optional


def make_json_serializable(obj: Any, _visited: Optional[Set[int]]=None, _depth: int=0) -> Any:
    """
    Convert objects to JSON serializable format
    
    Args:
        obj: The object to convert
        _visited: Set of object ids already visited (to prevent circular references)
        _depth: Current recursion depth
        
    Returns:
        JSON serializable version of the object
    """
    # Initialize visited set on first call
    if _visited is None:
        _visited = set()
    
    # Prevent infinite recursion
    if _depth > 10:  # Limit recursion depth
        return str(obj)
    
    # Handle circular references
    obj_id = id(obj)
    if obj_id in _visited:
        return "[Circular Reference]"
    
    try:
        if obj is None or isinstance(obj, (str, int, float, bool)):
            return obj
        elif isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, Path):
            # Handle Path objects by converting to string
            return str(obj)
        elif isinstance(obj, dict):
            _visited.add(obj_id)
            result = {}
            for k, v in obj.items():
                if isinstance(k, (str, int, float, bool)):
                    key = k
                else:
                    try:
                        key = str(k)
                    except:
                        key = f"[Key-{id(k)}]"
                result[key] = make_json_serializable(v, _visited, _depth + 1)
            return result
        elif isinstance(obj, list):
            _visited.add(obj_id)
            return [make_json_serializable(item, _visited, _depth + 1) for item in obj]
        elif hasattr(obj, '__dict__'):
            # Handle objects with __dict__ attribute (like MetaData)
            _visited.add(obj_id)
            try:
                # Filter out private attributes and methods
                filtered_dict = {k: v for k, v in obj.__dict__.items() 
                               if not k.startswith('_') and not callable(v)}
                return make_json_serializable(filtered_dict, _visited, _depth + 1)
            except Exception as e:
                return f"[Object: {type(obj).__name__}]"
        elif hasattr(obj, 'keys') and callable(getattr(obj, 'keys', None)):
            # Handle dictionary-like objects
            _visited.add(obj_id)
            try:
                result = {}
                for k in obj.keys():
                    if isinstance(k, (str, int, float, bool)):
                        key = k
                    else:
                        try:
                            key = str(k)
                        except:
                            key = f"[Key-{id(k)}]"
                    result[key] = make_json_serializable(obj[k], _visited, _depth + 1)
                return result
            except Exception as e:
                return f"[Dict-like: {type(obj).__name__}]"
        elif hasattr(obj, '__iter__') and callable(getattr(obj, '__iter__', None)) and not isinstance(obj, (str, bytes)):
            # Handle iterable objects
            _visited.add(obj_id)
            try:
                return [make_json_serializable(item, _visited, _depth + 1) for item in obj]
            except Exception as e:
                return f"[Iterable: {type(obj).__name__}]"
        
        # Default case - convert to string
        return str(obj)
    except Exception as e:
        return f"[Error: {str(e)[:50]}...]"  # Truncate long error messages


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
