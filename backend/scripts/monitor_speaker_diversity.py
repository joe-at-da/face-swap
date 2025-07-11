#!/usr/bin/env python3
"""
Monitor speaker attribution diversity in newly processed clips.

This script monitors the parliament_clips database for new clips and
tracks the distribution of member IDs to verify that our diversity-promoting
changes are working as expected.
"""

import os
import sys
import json
import time
import logging
import sqlite3
from datetime import datetime, timedelta
from collections import Counter, defaultdict
from typing import Dict, List, Any, Optional, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_clip_stats(db_path: str, since_timestamp: Optional[float] = None) -> Dict[str, Any]:
    """
    Get statistics on clips in the database, optionally filtered by timestamp.
    
    Args:
        db_path: Path to the SQLite database
        since_timestamp: Only include clips created after this timestamp
        
    Returns:
        Dictionary with clip statistics
    """
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # Enable row factory for named columns
        cursor = conn.cursor()
        
        # Base query
        query = "SELECT id, member_id, confidence_score, created_at, metadata FROM parliament_clips"
        params = []
        
        # Add timestamp filter if provided
        if since_timestamp is not None:
            # Convert timestamp to ISO format for SQLite comparison
            since_dt = datetime.fromtimestamp(since_timestamp)
            since_iso = since_dt.isoformat()
            query += " WHERE created_at > ?"
            params.append(since_iso)
        
        # Execute query
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        # Process results
        total_clips = len(rows)
        member_counts = Counter()
        confidence_by_member = defaultdict(list)
        
        for row in rows:
            member_id = row['member_id']
            member_counts[member_id] += 1
            
            # Track confidence scores
            if row['confidence_score'] is not None:
                confidence_by_member[member_id].append(float(row['confidence_score']))
        
        # Calculate average confidence by member
        avg_confidence_by_member = {
            member_id: sum(scores)/len(scores) if scores else 0
            for member_id, scores in confidence_by_member.items()
        }
        
        # Format results
        results = {
            "total_clips": total_clips,
            "unique_members": len(member_counts),
            "member_distribution": [
                {"member_id": member_id, "count": count, "percentage": (count/total_clips)*100 if total_clips else 0}
                for member_id, count in member_counts.most_common()
            ],
            "avg_confidence_by_member": [
                {"member_id": member_id, "avg_confidence": avg_confidence}
                for member_id, avg_confidence in avg_confidence_by_member.items()
            ]
        }
        
        return results
    except Exception as e:
        logger.error(f"Error getting clip stats: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {"error": str(e)}
    finally:
        if 'conn' in locals():
            conn.close()

def print_text_bar_chart(data, title, key_field, value_field, max_bars=10):
    """Print a simple text-based bar chart."""
    print(f"\n{title}")
    print("-" * 60)
    
    # Sort and limit data
    sorted_data = sorted(data, key=lambda x: x[value_field], reverse=True)[:max_bars]
    
    # Find maximum value for scaling
    max_value = max([item[value_field] for item in sorted_data]) if sorted_data else 0
    
    # Print bars
    for item in sorted_data:
        key = str(item[key_field])
        value = item[value_field]
        bar_length = int((value / max_value) * 40) if max_value > 0 else 0
        bar = "#" * bar_length
        print(f"{key[:20]:<20} | {bar} {value}")
    
    print("-" * 60)

def monitor_speaker_diversity(db_path: str, interval_seconds: int = 60, duration_minutes: int = 60):
    """
    Monitor speaker attribution diversity in newly processed clips.
    
    Args:
        db_path: Path to the SQLite database
        interval_seconds: How often to check for new clips (in seconds)
        duration_minutes: How long to run the monitoring (in minutes)
    """
    logger.info(f"Starting speaker diversity monitoring for {duration_minutes} minutes")
    logger.info(f"Checking for new clips every {interval_seconds} seconds")
    
    # Get initial stats as baseline
    start_time = time.time()
    initial_stats = get_clip_stats(db_path)
    
    if "error" in initial_stats:
        logger.error(f"Error getting initial stats: {initial_stats['error']}")
        return
    
    logger.info("Initial speaker attribution stats:")
    logger.info(f"Total clips: {initial_stats['total_clips']}")
    logger.info(f"Unique members: {initial_stats['unique_members']}")
    
    # Print initial member distribution
    print_text_bar_chart(
        initial_stats["member_distribution"], 
        "Initial Member Distribution", 
        "member_id", 
        "count"
    )
    
    # Track the last check time
    last_check_time = start_time
    
    # Monitor for the specified duration
    end_time = start_time + (duration_minutes * 60)
    while time.time() < end_time:
        # Sleep for the interval
        time.sleep(interval_seconds)
        
        # Get stats for new clips since last check
        current_time = time.time()
        new_stats = get_clip_stats(db_path, last_check_time)
        last_check_time = current_time
        
        if "error" in new_stats:
            logger.error(f"Error getting new stats: {new_stats['error']}")
            continue
        
        # If new clips were found, print stats
        if new_stats["total_clips"] > 0:
            logger.info(f"\nFound {new_stats['total_clips']} new clips since last check")
            logger.info(f"Unique members in new clips: {new_stats['unique_members']}")
            
            # Print new member distribution
            print_text_bar_chart(
                new_stats["member_distribution"], 
                "New Clips Member Distribution", 
                "member_id", 
                "count"
            )
        
        # Get cumulative stats since monitoring started
        cumulative_stats = get_clip_stats(db_path, start_time)
        
        if "error" not in cumulative_stats and cumulative_stats["total_clips"] > 0:
            logger.info(f"\nCumulative stats since monitoring started:")
            logger.info(f"Total new clips: {cumulative_stats['total_clips']}")
            logger.info(f"Unique members: {cumulative_stats['unique_members']}")
            
            # Print cumulative member distribution
            print_text_bar_chart(
                cumulative_stats["member_distribution"], 
                "Cumulative Member Distribution", 
                "member_id", 
                "count"
            )
        
        # Calculate and display time remaining
        elapsed = time.time() - start_time
        remaining = (duration_minutes * 60) - elapsed
        remaining_minutes = int(remaining / 60)
        remaining_seconds = int(remaining % 60)
        logger.info(f"Monitoring time remaining: {remaining_minutes}m {remaining_seconds}s")
    
    # Get final stats
    final_stats = get_clip_stats(db_path, start_time)
    
    if "error" not in final_stats:
        logger.info("\nFinal speaker attribution stats for new clips:")
        logger.info(f"Total new clips: {final_stats['total_clips']}")
        logger.info(f"Unique members: {final_stats['unique_members']}")
        
        # Print final member distribution
        print_text_bar_chart(
            final_stats["member_distribution"], 
            "Final Member Distribution", 
            "member_id", 
            "count"
        )
    
    logger.info("Speaker diversity monitoring complete")

def main():
    """Main function to run the monitoring."""
    # Define database path
    db_path = os.path.join(os.path.dirname(__file__), '..', 'parliament_clips.db')
    
    # Check if database exists
    if not os.path.exists(db_path):
        logger.error(f"Database file not found: {db_path}")
        return
    
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description='Monitor speaker attribution diversity')
    parser.add_argument('--interval', type=int, default=60, help='Check interval in seconds (default: 60)')
    parser.add_argument('--duration', type=int, default=60, help='Monitoring duration in minutes (default: 60)')
    args = parser.parse_args()
    
    # Run the monitoring
    monitor_speaker_diversity(db_path, args.interval, args.duration)

if __name__ == "__main__":
    main()
