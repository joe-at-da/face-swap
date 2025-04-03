from datetime import datetime
from backend.db import models

def create_test_clip(
    user_id: int,
    title: str,
    description: str,
    source_url: str,
    start_time: datetime,
    end_time: datetime,
    db
) -> models.VideoClip:
    """Create a test video clip."""
    clip = models.VideoClip(
        user_id=user_id,
        title=title,
        description=description,
        source_url=source_url,
        start_time=start_time,
        end_time=end_time,
        status="ready",
        storage_path="/test/path.mp4"
    )
    db.add(clip)
    db.commit()
    db.refresh(clip)
    return clip
