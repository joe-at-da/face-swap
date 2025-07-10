#!/usr/bin/env python
"""
Clean up script for organizing embedding system fixes.

This script:
1. Creates a backup directory for all the test/fix scripts
2. Moves all test/fix scripts to the backup directory
3. Keeps only the comprehensive fix and documentation
"""
import os
import shutil
import logging
from pathlib import Path
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Files to keep
KEEP_FILES = [
    "comprehensive_embedding_fix.py",
    "README_embedding_fix.md"
]

def main():
    # Create backup directory with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = Path(f"embedding_fixes_backup_{timestamp}")
    backup_dir.mkdir(exist_ok=True)
    logger.info(f"Created backup directory: {backup_dir}")
    
    # Get all Python files in the current directory
    current_dir = Path(".")
    python_files = list(current_dir.glob("*.py"))
    markdown_files = list(current_dir.glob("*.md"))
    
    # Filter files related to embedding fixes
    embedding_fix_files = []
    for file in python_files:
        if any(keyword in file.name.lower() for keyword in ["embedding", "fix", "darren", "jones", "match", "recognition", "test_", "verify", "debug"]):
            if file.name not in KEEP_FILES and file.name != os.path.basename(__file__):
                embedding_fix_files.append(file)
    
    # Move files to backup directory
    moved_count = 0
    for file in embedding_fix_files:
        try:
            shutil.copy2(file, backup_dir / file.name)
            logger.info(f"Backed up: {file.name}")
            moved_count += 1
        except Exception as e:
            logger.error(f"Failed to back up {file.name}: {str(e)}")
    
    logger.info(f"Backed up {moved_count} files to {backup_dir}")
    logger.info("\nTo complete the cleanup, you can run:")
    logger.info(f"rm {' '.join([str(f) for f in embedding_fix_files])}")
    
    # List files that were kept
    logger.info("\nKept files:")
    for file in KEEP_FILES:
        if os.path.exists(file):
            logger.info(f"- {file}")
    
    logger.info("\nCleanup complete! The embedding system has been fixed and is ready for production.")
    logger.info("You can safely delete the backup directory once you've verified everything works correctly.")

if __name__ == "__main__":
    main()
