#!/usr/bin/env python
"""
Script to run all database migrations.
"""

import os
import sys
import importlib
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_migrations():
    """Run all migrations in the migrations directory."""
    logger.info("Starting database migrations")
    
    # Add the project root to the Python path
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, project_root)
    
    # Import the migration modules
    migrations_dir = os.path.join(project_root, "backend", "db", "migrations")
    migration_files = [f for f in os.listdir(migrations_dir) 
                      if f.endswith('.py') and f != '__init__.py']
    
    logger.info(f"Found {len(migration_files)} migration files")
    
    for migration_file in migration_files:
        migration_name = os.path.splitext(migration_file)[0]
        logger.info(f"Running migration: {migration_name}")
        
        try:
            # Import the migration module
            module_path = f"backend.db.migrations.{migration_name}"
            migration_module = importlib.import_module(module_path)
            
            # Run the migration
            if hasattr(migration_module, 'run_migration'):
                migration_module.run_migration()
            else:
                logger.warning(f"Migration {migration_name} does not have a run_migration function")
        except Exception as e:
            logger.error(f"Error running migration {migration_name}: {str(e)}")
    
    logger.info("All migrations completed")

if __name__ == "__main__":
    run_migrations()
