import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional

from backend.core.config import settings

# Create logs directory if it doesn't exist
logs_dir = Path("logs")
logs_dir.mkdir(exist_ok=True)

def setup_logging(name: str, log_file: Optional[str] = None) -> logging.Logger:
    """
    Set up logging configuration for the application.
    
    Args:
        name: The name of the logger
        log_file: Optional file name for the log file. If not provided, will use {name}.log
    
    Returns:
        logging.Logger: Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO if settings.ENVIRONMENT == "production" else logging.DEBUG)

    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
    )
    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )

    # Console handler (simple format for readability)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(simple_formatter)
    logger.addHandler(console_handler)

    # File handler (detailed format for debugging)
    if log_file is None:
        log_file = f"{name}.log"
    
    file_handler = RotatingFileHandler(
        logs_dir / log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(detailed_formatter)
    logger.addHandler(file_handler)

    return logger

# Create main application logger
app_logger = setup_logging("parliament_clips")

# Create service-specific loggers
capture_logger = setup_logging("capture_service", "capture.log")
storage_logger = setup_logging("storage_service", "storage.log")
video_logger = setup_logging("video_service", "video.log")

def get_logger(name: str) -> logging.Logger:
    """Get a logger by name."""
    return logging.getLogger(name)
