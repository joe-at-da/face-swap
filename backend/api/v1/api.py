from fastapi import APIRouter
from backend.api.v1.endpoints import auth, video, capture

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(video.router, prefix="/videos", tags=["videos"])
api_router.include_router(capture.router, prefix="/capture", tags=["capture"])
