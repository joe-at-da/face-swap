"""
Module for handling default members for unidentified speakers
"""
import logging
import uuid
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

def get_default_member_for_house(house_id: str, members: List[Dict[str, Any]] = None) -> Optional[int]:
    """
    Get or create a default member for unidentified speakers in a specific house
    
    Args:
        house_id: ID of the house (commons, lords, etc.)
        members: Optional list of parliament members to search for existing default members
        
    Returns:
        ID of the default member or None if failed
    """
    try:
        # Normalize house ID
        normalized_house = house_id.lower() if isinstance(house_id, str) else str(house_id).lower()
        
        # Define default IDs and names based on house
        if normalized_house == 'commons':
            default_id = -1  # Using numeric ID instead of 'default_commons'
            default_name = 'Unidentified MP (Commons)'
        elif normalized_house == 'lords':
            default_id = -1  # Using numeric ID instead of 'default_lords'
            default_name = 'Unidentified Peer (Lords)'
        else:
            default_id = -1  # Using numeric ID instead of 'default_unknown'
            default_name = 'Unidentified Speaker'
        
        # If members list is provided, check if default member already exists
        if members:
            for member in members:
                member_id = member.get('id')
                member_name = member.get('name', '')
                member_display_name = member.get('display_name', '')
                is_default = member.get('is_default', False)
                
                # Handle house_id that could be int or string
                house_id_value = member.get('house_id')
                if house_id_value is not None:
                    if isinstance(house_id_value, int):
                        # Convert int to string
                        member_house = str(house_id_value).lower()
                    elif isinstance(house_id_value, str):
                        member_house = house_id_value.lower()
                    else:
                        member_house = str(house_id_value).lower()
                else:
                    member_house = None
                
                # Check if this is a default member for the requested house
                if member_house == normalized_house and is_default:
                    logger.info(f"Found existing default member for house {house_id} with ID {member_id}")
                    return member_id
                
                # Fallback check using name
                display_name_match = member_display_name and default_name in member_display_name
                name_match = member_name and default_name in member_name
                
                if member_house == normalized_house and (display_name_match or name_match):
                    logger.info(f"Found existing default member for house {house_id} with ID {member_id}")
                    return member_id
        
        # Return predefined default ID if no members list or default not found
        logger.info(f"Using predefined default member for house {house_id} with ID {default_id}")
        return default_id
    except Exception as e:
        logger.error(f"Error getting/creating default member for house {house_id}: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None
