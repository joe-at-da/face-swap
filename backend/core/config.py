from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    # Base settings
    PROJECT_NAME: str = "Parliament Video Clip Manager"
    API_V1_STR: str = "/api/v1"
    
    # Authentication
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    
    # Database
    DATABASE_URL: str
    TEST_DATABASE_URL: str = None
    
    # Video Settings
    PARLIAMENT_TV_URL: str = "https://www.parliamentlive.tv/Event/Index"
    TEMP_STORAGE_PATH: str = "/app/data/temp"
    MEDIA_STORAGE_PATH: str = "/app/data/media"
    MAX_CLIP_DURATION_MINUTES: int = 30
    CLEANUP_AGE_HOURS: int = 24
    
    # Storage Limits
    MAX_STORAGE_GB: int = 500  # Maximum storage limit in GB
    TEMP_STORAGE_MAX_GB: int = 50  # Maximum temporary storage in GB
    
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
    FACEBOOK_APP_ID: str
    FACEBOOK_APP_SECRET: str
    INSTAGRAM_ACCESS_TOKEN: str

    # Parliament TV
    PARLIAMENT_TV_API_KEY: str

    # Development Settings
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    ALLOWED_HOSTS: str = "localhost,127.0.0.1"
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    class Config:
        env_file = Path(".env")

settings = Settings()
