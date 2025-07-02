"""
Module for handling default members for unidentified speakers
"""
import logging
import uuid
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

def get_default_member_for_house(members: List[Dict[str, Any]], house_id: str) -> Optional[str]:
    """
    Get or create a default member for unidentified speakers in a specific house
    
    Args:
        members: List of parliament members
        house_id: ID of the house (commons, lords, etc.)
        
    Returns:
        ID of the default member or None if failed
    """
    try:
        # Normalize house ID
        normalized_house = house_id.lower() if isinstance(house_id, str) else str(house_id).lower()
        
        # Define default member names based on house
        if normalized_house == 'commons':
            default_name = 'Unidentified MP (Commons)'
        elif normalized_house == 'lords':
            default_name = 'Unidentified Peer (Lords)'
        else:
            default_name = 'Unidentified Speaker'
            
        # Check if default member already exists in local cache
        for member in members:
            member_id = member.get('id')
            member_display_name = member.get('display_name')
            
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
            
            if member_display_name and default_name in member_display_name and member_house == normalized_house:
                logger.info(f"Found existing default member for house {house_id} with ID {member_id}")
                return member_id
        
        # Create a new default member if not found
        member_id = str(uuid.uuid4())
        
        logger.info(f"Created new default member for house {house_id} with ID {member_id}")
        return member_id
    except Exception as e:
        logger.error(f"Error getting/creating default member for house {house_id}: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None
