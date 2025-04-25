from fastapi import APIRouter
from backend.api.v1.endpoints import auth, video, capture, transcription, storage, social, dashboard

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(video.router, prefix="/clips", tags=["clips"])
api_router.include_router(capture.router, prefix="/capture", tags=["capture"])
api_router.include_router(transcription.router, prefix="/transcriptions", tags=["transcriptions"])
api_router.include_router(storage.router, prefix="/storage", tags=["storage"])
api_router.include_router(social.router, prefix="/social", tags=["social"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
