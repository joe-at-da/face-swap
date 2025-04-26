from pydantic_settings import BaseSettings
from pathlib import Path
from typing import Optional

class Settings(BaseSettings):
    # Base settings
    PROJECT_NAME: str = "Parliament Video Clip Manager"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "info"  # Will be overridden by uvicorn's --log-level flag
    
    # Authentication
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    
    # Database
    DATABASE_URL: str
    TEST_DATABASE_URL: Optional[str] = None
    
    # Video Settings
    # Using a reliable test stream for development
    # For production, replace with the actual Parliament TV stream URL
    PARLIAMENT_TV_URL: str = "http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"
    TEMP_STORAGE_PATH: str = "/app/data/temp"
    MEDIA_STORAGE_PATH: str = "/app/data/media"
    MAX_CLIP_DURATION_MINUTES: int = 30
    CLEANUP_AGE_HOURS: int = 24
    
    # Storage Limits
    MAX_STORAGE_GB: int = 500  # Maximum storage limit in GB
    TEMP_STORAGE_MAX_GB: int = 50  # Maximum temporary storage in GB
    MEDIA_STORAGE_QUOTA: int = 10 * 1024 * 1024 * 1024  # 10GB default
    TEMP_STORAGE_QUOTA: int = 2 * 1024 * 1024 * 1024   # 2GB default
    ARCHIVE_RETENTION_DAYS: int = 180  # How long to keep archived files
    BACKUP_RETENTION_DAYS: int = 30   # How long to keep backups
    
    # Redis
    REDIS_URL: str
    
    # AWS
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    AWS_REGION: str
    S3_BUCKET: str

    # Social Media
    TWITTER_API_KEY: str
    TWITTER_API_SECRET: str
    TWITTER_ACCESS_TOKEN: str = ""
    TWITTER_ACCESS_TOKEN_SECRET: str = ""
    FACEBOOK_APP_ID: str
    FACEBOOK_APP_SECRET: str
    FACEBOOK_ACCESS_TOKEN: str = ""
    FACEBOOK_PAGE_ID: str = ""
    INSTAGRAM_ACCESS_TOKEN: str
    INSTAGRAM_ACCOUNT_ID: str = ""

    # Parliament TV
    PARLIAMENT_TV_API_KEY: str

    # Development Settings
    DEBUG: bool = False
    ALLOWED_HOSTS: str = "localhost,127.0.0.1"
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000,http://frontend:3000,http://host.docker.internal:3000,*"

    class Config:
        env_file = Path(".env")

settings = Settings()
