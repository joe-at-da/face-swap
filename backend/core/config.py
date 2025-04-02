from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str

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

    # Security
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    # Development Settings
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    ALLOWED_HOSTS: str = "localhost,127.0.0.1"
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    class Config:
        env_file = ".env"

@lru_cache()
def get_settings():
    return Settings()
