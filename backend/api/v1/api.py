from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from backend.api.v1.endpoints import auth, video, capture, transcription, storage, social, dashboard, admin, parliament_tv, speaker_identification, videos, recognition, audio_transcription, recognition_results, recognition_status, recognition_list, voice_profiles, face_profiles, multimodal_recognition, facial_recognition, mp_profiles, files, recognition_timeline, media, system

api_router = APIRouter()

api_router.include_router(auth.router, prefix='/auth', tags=['authentication'])
api_router.include_router(video.router, prefix='/clips', tags=['clips'])
api_router.include_router(capture.router, prefix='/capture', tags=['capture'])
api_router.include_router(videos.router, prefix='/videos', tags=['videos'])
api_router.include_router(speaker_identification.router, prefix='/speaker-identification', tags=['speaker-identification'])
api_router.include_router(transcription.router, prefix='/transcription', tags=['transcriptions'])
api_router.include_router(storage.router, prefix='/storage', tags=['storage'])
api_router.include_router(social.router, prefix='/social', tags=['social'])
api_router.include_router(dashboard.router, prefix='/dashboard', tags=['dashboard'])
api_router.include_router(admin.router, prefix='/admin', tags=['admin'])
api_router.include_router(parliament_tv.router, prefix='/parliament-tv', tags=['parliament-tv'])
api_router.include_router(recognition.router, prefix='/recognition', tags=['recognition'])
api_router.include_router(recognition_status.router, prefix='/recognition/status', tags=['recognition'])
api_router.include_router(recognition_list.router, prefix='/recognition', tags=['recognition'])
api_router.include_router(recognition_results.router, prefix='/recognition/results', tags=['recognition'])
api_router.include_router(recognition_timeline.router, prefix='/recognition/timeline', tags=['recognition'])
api_router.include_router(audio_transcription.router, prefix='/audio-transcription', tags=['audio-transcription'])
api_router.include_router(voice_profiles.router, prefix='/voice-profiles', tags=['voice-profiles'])
api_router.include_router(face_profiles.router, prefix='/face-profiles', tags=['face-profiles'])
api_router.include_router(multimodal_recognition.router, prefix='/multimodal-recognition', tags=['multimodal-recognition'])
api_router.include_router(facial_recognition.router, prefix='/facial-recognition', tags=['facial-recognition'])
api_router.include_router(mp_profiles.router, prefix='/mp-profiles', tags=['mp-profiles'])
api_router.include_router(files.router, prefix='/files', tags=['files'])
api_router.include_router(media.router, prefix='/media', tags=['media'])
api_router.include_router(system.router, prefix='/system', tags=['system'])

# Create a profiles router for compatibility with frontend paths
profiles_router = APIRouter(prefix='/profiles', tags=['profiles'])

# Redirect /profiles/voice to /voice-profiles
@profiles_router.get('/voice')
async def get_voice_profiles(request: Request):
    """Redirect to the voice-profiles endpoint"""
    return RedirectResponse(url='/api/v1/voice-profiles')

# Include the profiles router
api_router.include_router(profiles_router)
