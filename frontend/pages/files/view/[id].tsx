import React, { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/router';
import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import DarkLayout from '../../../components/layout/DarkLayout';
import { withAuth, useAuth } from '../../../contexts/AuthContext';
import { UserRole } from '../../../contexts/AuthContext';
import UnifiedRecognitionPanel from '../../../components/recognition/UnifiedRecognitionPanel';
import { toast } from 'react-toastify';
import { api } from '../../../utils/api';

// API base URL
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

interface VideoClip {
  id: number;
  title: string;
  description: string;
  duration: number;
  file_path: string;
  thumbnail_url: string;
  created_at: string;
  updated_at: string;
  created_by_id: number;
  has_transcription: boolean;
  status: string;
  capture_session_id?: number;
}

interface ParliamentTVVideo {
  id: number;
  title: string;
  status: string;
  file_path: string;
  file_size: number;
  created_at: string;
  updated_at: string;
  duration: number;
  url: string;
  facial_recognition_enabled: boolean;
  facial_recognition_status?: string;
  created_by: {
    id: number;
    name: string;
    email: string;
  };
}

const MediaViewPage: React.FC = () => {
  const router = useRouter();
  const { token } = useAuth();
  const { id, type, tab = 'player' } = router.query;
  
  const [activeTab, setActiveTab] = useState<string>(tab as string || 'player');
  const [showAudioPlayer, setShowAudioPlayer] = useState(false);
  const [syncPlayback, setSyncPlayback] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);
  const audioRef = useRef<HTMLAudioElement>(null);

  // Fetch clip data if type is 'clip'
  const { 
    data: clip, 
    isLoading: clipLoading, 
    isError: clipError 
  } = useQuery<VideoClip>({
    queryKey: ['videoClip', id],
    queryFn: async () => {
      if (!id) throw new Error('No clip ID provided');
      return await api.get(`/clips/${id}`);
    },
    enabled: !!id && type === 'clip',
    refetchOnWindowFocus: false,
  });

  // Fetch video data if type is 'video'
  const { 
    data: video, 
    isLoading: videoLoading, 
    isError: videoError 
  } = useQuery<ParliamentTVVideo>({
    queryKey: ['parliamentVideo', id],
    queryFn: async () => {
      if (!id || !token) throw new Error('No video ID provided');
      const response = await api.get(`/parliament-tv/${id}`);
      return response;
    },
    enabled: !!id && !!token && type === 'video',
    refetchOnWindowFocus: false,
  });

  // Determine if we're loading
  const isLoading = (type === 'clip' && clipLoading) || (type === 'video' && videoLoading);
  
  // Determine if there's an error
  const isError = (type === 'clip' && clipError) || (type === 'video' && videoError);

  // Set active tab when the tab query parameter changes
  useEffect(() => {
    if (tab) {
      setActiveTab(tab as string);
    }
  }, [tab]);

  // Sync video and audio playback if enabled
  useEffect(() => {
    const videoElement = videoRef.current;
    const audioElement = audioRef.current;

    if (!videoElement || !audioElement || !syncPlayback) return;

    const syncPlay = () => {
      if (videoElement.paused) {
        audioElement.pause();
      } else {
        audioElement.currentTime = videoElement.currentTime;
        audioElement.play().catch(err => console.error('Error playing audio:', err));
      }
    };

    const syncPause = () => {
      audioElement.pause();
    };

    const syncTimeUpdate = () => {
      if (!audioElement.paused) {
        audioElement.currentTime = videoElement.currentTime;
      }
    };

    videoElement.addEventListener('play', syncPlay);
    videoElement.addEventListener('pause', syncPause);
    videoElement.addEventListener('timeupdate', syncTimeUpdate);

    return () => {
      videoElement.removeEventListener('play', syncPlay);
      videoElement.removeEventListener('pause', syncPause);
      videoElement.removeEventListener('timeupdate', syncTimeUpdate);
    };
  }, [syncPlayback]);

  // Format file size
  const formatFileSize = (bytes: number) => {
    if (!bytes) return 'Unknown';
    
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    let size = bytes;
    let unitIndex = 0;
    
    while (size >= 1024 && unitIndex < units.length - 1) {
      size /= 1024;
      unitIndex++;
    }
    
    return `${size.toFixed(2)} ${units[unitIndex]}`;
  };

  // Format duration
  const formatDuration = (seconds: number) => {
    if (!seconds) return '--:--:--';
    
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    
    return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  // Format date
  const formatDate = (dateString: string): string => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-GB', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  // Get status badge color
  const getStatusBadgeColor = (status: string) => {
    const normalizedStatus = status.toLowerCase();
    
    if (normalizedStatus === 'ready' || normalizedStatus === 'completed') {
      return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300';
    } else if (normalizedStatus === 'processing') {
      return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300';
    } else if (normalizedStatus === 'failed') {
      return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300';
    } else {
      return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300';
    }
  };

  // Generate video URL based on type
  const getVideoUrl = () => {
    if (type === 'clip' && clip) {
      return `${API_BASE_URL}/stream/clip/${clip.id}`;
    } else if (type === 'video' && video) {
      return `${API_BASE_URL}/videos/stream-with-token/${video.file_path.split('/').pop()}?token=${token}`;
    }
    return '';
  };

  // Generate audio URL based on type
  const getAudioUrl = () => {
    if (type === 'video' && video) {
      const captureNumber = video.id.toString().padStart(4, '0');
      return `${API_BASE_URL}/videos/stream-audio-with-token/capture_${captureNumber}.audio.mp3?token=${token}`;
    }
    return '';
  };

  // Generate thumbnail URL
  const getThumbnailUrl = () => {
    if (type === 'clip' && clip) {
      return clip.thumbnail_url;
    } else if (type === 'video' && video) {
      return `${API_BASE_URL}/thumbnail/capture/${video.id}?token=${token}`;
    }
    return '/images/video-placeholder.jpg';
  };

  // Determine if we can show audio player
  const canShowAudio = type === 'video' && video;

  // Determine if we can show recognition panel
  const canShowRecognition = (type === 'clip' && clip && 
                             (clip.status === 'READY' || clip.status === 'ready' || clip.status === 'COMPLETED' || clip.status === 'completed')) ||
                             (type === 'video' && video);

  // Determine the capture ID for recognition panel
  const getRecognitionCaptureId = () => {
    if (type === 'clip' && clip) {
      return clip.capture_session_id || parseInt(id as string) || null;
    } else if (type === 'video' && video) {
      return video.id;
    }
    return parseInt(id as string) || null;
  };

  if (isLoading) {
    return (
      <DarkLayout>
        <div className="container mx-auto px-4 py-8">
          <div className="flex justify-center items-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
          </div>
        </div>
      </DarkLayout>
    );
  }

  if (isError) {
    return (
      <DarkLayout>
        <div className="container mx-auto px-4 py-8">
          <div className="text-center p-8">
            <h2 className="text-xl text-red-500 mb-4">Error loading media</h2>
            <p className="text-gray-400 mb-4">There was an error loading this media. It may have been deleted or you don't have permission to view it.</p>
            <Link href="/files" className="text-blue-500 hover:underline">
              Back to media library
            </Link>
          </div>
        </div>
      </DarkLayout>
    );
  }

  // Get the title based on type
  const getTitle = () => {
    if (type === 'clip' && clip) {
      return clip.title;
    } else if (type === 'video' && video) {
      return video.title;
    }
    return 'Media';
  };

  return (
    <DarkLayout>
      <div className="container mx-auto px-4 py-8">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-2xl font-bold text-white">{getTitle()}</h1>
          <Link href="/files" className="text-blue-400 hover:text-blue-300">
            Back to media library
          </Link>
        </div>

        {/* Media details */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 mb-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h2 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Details</h2>
              <dl className="grid grid-cols-1 gap-x-4 gap-y-6 sm:grid-cols-2">
                <div className="sm:col-span-1">
                  <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">Title</dt>
                  <dd className="mt-1 text-sm text-gray-900 dark:text-white">
                    {type === 'clip' ? clip?.title : video?.title}
                  </dd>
                </div>
                <div className="sm:col-span-1">
                  <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">Duration</dt>
                  <dd className="mt-1 text-sm text-gray-900 dark:text-white">
                    {formatDuration(type === 'clip' ? clip?.duration || 0 : video?.duration || 0)}
                  </dd>
                </div>
                <div className="sm:col-span-1">
                  <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">Created</dt>
                  <dd className="mt-1 text-sm text-gray-900 dark:text-white">
                    {formatDate(type === 'clip' ? clip?.created_at || '' : video?.created_at || '')}
                  </dd>
                </div>
                <div className="sm:col-span-1">
                  <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">Status</dt>
                  <dd className="mt-1 text-sm">
                    <span className={`px-2 py-1 text-xs rounded-full ${getStatusBadgeColor(type === 'clip' ? clip?.status || '' : video?.status || '')}`}>
                      {type === 'clip' ? clip?.status : video?.status}
                    </span>
                    {type === 'clip' && clip?.has_transcription && (
                      <span className="ml-2 px-2 py-1 text-xs rounded-full bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300">
                        Transcribed
                      </span>
                    )}
                  </dd>
                </div>
                {type === 'clip' && clip?.description && (
                  <div className="sm:col-span-2">
                    <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">Description</dt>
                    <dd className="mt-1 text-sm text-gray-900 dark:text-white">
                      {clip.description}
                    </dd>
                  </div>
                )}
                {type === 'video' && video?.file_size && (
                  <div className="sm:col-span-1">
                    <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">File Size</dt>
                    <dd className="mt-1 text-sm text-gray-900 dark:text-white">
                      {formatFileSize(video.file_size)}
                    </dd>
                  </div>
                )}
              </dl>
            </div>
            <div>
              <h2 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Preview</h2>
              <div className="w-full h-40 bg-gray-200 dark:bg-gray-700 rounded-lg overflow-hidden">
                <img 
                  src={getThumbnailUrl()} 
                  alt={getTitle()}
                  className="w-full h-full object-cover"
                />
              </div>
              {type === 'clip' && clip && (
                <div className="mt-4">
                  <Link href={`/capture/create-clip?source=${clip.capture_session_id}`} className="text-blue-500 hover:text-blue-400">
                    Create another clip from this source
                  </Link>
                </div>
              )}
              {type === 'video' && video && (
                <div className="mt-4">
                  <Link href={`/capture/create-clip?source=${video.id}`} className="text-blue-500 hover:text-blue-400">
                    Create clip from this video
                  </Link>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="mb-6">
          <div className="flex border-b border-gray-700">
            <button
              onClick={() => setActiveTab('player')}
              className={`py-2 px-4 border-b-2 font-medium ${
                activeTab === 'player'
                  ? 'border-blue-500 text-blue-500'
                  : 'border-transparent text-gray-400 hover:text-gray-300'
              }`}
            >
              Player
            </button>
            {canShowRecognition && (
              <button
                onClick={() => setActiveTab('recognition')}
                className={`py-2 px-4 border-b-2 font-medium ${
                  activeTab === 'recognition'
                    ? 'border-blue-500 text-blue-500'
                    : 'border-transparent text-gray-400 hover:text-gray-300'
                }`}
              >
                Recognition
              </button>
            )}
            {type === 'clip' && clip?.has_transcription && (
              <button
                onClick={() => setActiveTab('transcription')}
                className={`py-2 px-4 border-b-2 font-medium ${
                  activeTab === 'transcription'
                    ? 'border-blue-500 text-blue-500'
                    : 'border-transparent text-gray-400 hover:text-gray-300'
                }`}
              >
                Transcription
              </button>
            )}
          </div>
        </div>

        {/* Tab content */}
        {activeTab === 'player' && (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md overflow-hidden">
            <div className="px-4 py-5 sm:px-6 bg-gray-800">
              <h3 className="text-lg leading-6 font-medium text-white">Media Player</h3>
            </div>
            <div className="border-t border-gray-700 p-4">
              <div className="aspect-w-16 aspect-h-9">
                <video 
                  ref={videoRef}
                  controls 
                  className="w-full h-full object-cover rounded-lg"
                  src={getVideoUrl()}
                  poster={getThumbnailUrl()}
                >
                  Your browser does not support the video tag.
                </video>
              </div>
              
              {/* Audio Player Section */}
              {canShowAudio && (
                <div className="mt-6">
                  <h4 className="text-lg font-medium text-white mb-2">Audio Track</h4>
                  <div className="flex items-center mb-2">
                    <button
                      onClick={() => setShowAudioPlayer(!showAudioPlayer)}
                      className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded mr-2"
                    >
                      {showAudioPlayer ? 'Hide Audio Player' : 'Show Audio Player'}
                    </button>
                    
                    <label className="inline-flex items-center cursor-pointer ml-2">
                      <input 
                        type="checkbox" 
                        className="sr-only peer"
                        checked={syncPlayback}
                        onChange={() => setSyncPlayback(!syncPlayback)}
                      />
                      <div className="relative w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-500"></div>
                      <span className="ml-3 text-sm font-medium text-gray-300">Synchronize audio and video playback</span>
                    </label>
                  </div>
                  
                  {showAudioPlayer && (
                    <div className="mt-2">
                      <audio 
                        ref={audioRef}
                        controls 
                        className="w-full" 
                        src={getAudioUrl()}
                      >
                        Your browser does not support the audio element.
                      </audio>
                    </div>
                  )}
                </div>
              )}
              
              <div className="mt-4 text-sm text-gray-400">
                <p>Note: If the video or audio doesn't play, it may be in a format not supported by your browser or the file may not be accessible.</p>
                {canShowAudio && (
                  <p>For best results, play both the video and audio simultaneously or enable synchronization.</p>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Recognition Panel */}
        {activeTab === 'recognition' && canShowRecognition && (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
            <UnifiedRecognitionPanel 
              captureId={getRecognitionCaptureId() || 0} 
              onProcessingComplete={() => {
                toast.success('Recognition processing completed');
                router.reload();
              }}
            />
          </div>
        )}

        {/* Transcription Panel */}
        {activeTab === 'transcription' && type === 'clip' && clip?.has_transcription && (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
            <h2 className="text-lg font-medium text-white mb-4">Transcription</h2>
            <div className="text-center p-8">
              <p className="text-gray-400">Loading transcription data...</p>
              {/* This would be replaced with actual transcription component */}
            </div>
          </div>
        )}

        {/* Action buttons */}
        <div className="mt-8 flex justify-between">
          <Link href="/files" className="text-blue-400 hover:text-blue-300">
            Back to media library
          </Link>
          {type === 'clip' && clip && (
            <Link href={`/social/new?clipId=${clip.id}`}>
              <button className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded">
                Share on Social Media
              </button>
            </Link>
          )}
        </div>
      </div>
    </DarkLayout>
  );
};

export default withAuth(MediaViewPage, [UserRole.ADMIN, UserRole.MP, UserRole.STAFF]);
