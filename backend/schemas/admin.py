from typing import Dict, Optional
from pydantic import BaseModel


class StorageStats(BaseModel):
    total: int
    used: int
    available: int


class ClipStats(BaseModel):
    total: int
    processing: int
    completed: int
    failed: int


class CaptureStats(BaseModel):
    total: int
    active: int
    completed: int
    failed: int


class UserStats(BaseModel):
    total: int
    active: int
    inactive: int


class SocialStats(BaseModel):
    total_posts: int
    scheduled_posts: int
    published_posts: int


class SystemStats(BaseModel):
    storage: StorageStats
    clips: ClipStats
    captures: CaptureStats
    users: UserStats
    social: SocialStats
