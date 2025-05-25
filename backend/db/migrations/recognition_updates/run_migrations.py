#!/usr/bin/env python
"""
Script to run all recognition update migrations in order.
"""

import os
import sys
import logging
import importlib.util

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def import_module_from_file(file_path):
    """Import a module from a file path."""
    module_name = os.path.basename(file_path).replace('.py', '')
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def run_migrations():
    """Run all recognition update migrations in order."""
    logger.info("Starting recognition update migrations")
    
    # Get the directory of this script
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Get all migration files
    migration_files = []
    for file in os.listdir(current_dir):
        if file.endswith('.py') and file != 'run_migrations.py' and file != '__init__.py':
            migration_files.append(os.path.join(current_dir, file))
    
    # Sort migration files by name
    migration_files.sort()
    
    # Run each migration
    for file_path in migration_files:
        try:
            logger.info(f"Running migration: {os.path.basename(file_path)}")
            module = import_module_from_file(file_path)
            module.run_migration()
            logger.info(f"Successfully completed migration: {os.path.basename(file_path)}")
        except Exception as e:
            logger.error(f"Error running migration {os.path.basename(file_path)}: {str(e)}")
            return False
    
    logger.info("All recognition update migrations completed successfully")
    return True

if __name__ == "__main__":
    success = run_migrations()
    sys.exit(0 if success else 1)
