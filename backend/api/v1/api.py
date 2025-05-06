from fastapi import APIRouter
from backend.api.v1.endpoints import auth, video, capture, transcription, storage, social, dashboard, admin, parliament_tv, speaker_identification, videos, parliament_tv_audio, parliament_tv_video, videos_audio

api_router = APIRouter()

api_router.include_router(auth.router, prefix='/auth', tags=['authentication'])
api_router.include_router(video.router, prefix='/clips', tags=['clips'])
api_router.include_router(capture.router, prefix='/capture', tags=['capture'])
api_router.include_router(videos.router, prefix='/videos', tags=['videos'])
api_router.include_router(videos_audio.router, prefix='/videos-audio', tags=['videos-audio'])
api_router.include_router(speaker_identification.router, prefix='/speaker-identification', tags=['speaker-identification'])
# Audio extraction is now handled directly in the parliament_tv service
api_router.include_router(transcription.router, prefix='/transcription', tags=['transcriptions'])
api_router.include_router(storage.router, prefix='/storage', tags=['storage'])
api_router.include_router(social.router, prefix='/social', tags=['social'])
api_router.include_router(dashboard.router, prefix='/dashboard', tags=['dashboard'])
api_router.include_router(admin.router, prefix='/admin', tags=['admin'])
api_router.include_router(parliament_tv.router, prefix='/parliament-tv', tags=['parliament-tv'])
api_router.include_router(parliament_tv_audio.router, prefix='/audio-extraction', tags=['audio-extraction'])
api_router.include_router(parliament_tv_video.router, prefix='/video-download', tags=['video-download'])
