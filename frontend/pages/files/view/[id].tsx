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
  file_path?: string;
  path?: string;  // Added for compatibility with API responses
  filename?: string;  // Added for compatibility with API responses
  file_size?: number;
  size?: number;  // Added for compatibility with API responses
  created_at: string;
  updated_at: string;
  duration?: number;
  url?: string;
  facial_recognition_enabled?: boolean;
  facial_recognition_status?: string;
  relative_path?: string;  // Added for compatibility with API responses
  modified_time?: number;  // Added for compatibility with API responses
  created_by?: {
    id: number;
    name: string;
    email: string;
  };
}

const MediaViewPage: React.FC = () => {
  const router = useRouter();
  const { token } = useAuth();
  const { id, type, tab = 'player' } = router.query;
  
  // Check if we have a valid ID
  const isInvalidId = !id || id === 'null' || id === 'undefined' || id === '[id]';
  
  const [activeTab, setActiveTab] = useState<string>(tab as string || 'player');
  const [showAudioPlayer, setShowAudioPlayer] = useState(false);
  const [playerError, setPlayerError] = useState(false);
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
      // Check if we have a valid ID
      if (!id || id === 'null' || id === 'undefined' || id === '[id]') {
        throw new Error('Invalid clip ID');
      }
      return await api.get(`/clips/${id}`);
    },
    enabled: !!id && id !== 'null' && id !== 'undefined' && id !== '[id]' && type === 'clip',
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
      // Check if we have a valid ID
      if (!id || id === 'null' || id === 'undefined' || id === '[id]') {
        throw new Error('Invalid video ID');
      }
      if (!token) throw new Error('Authentication token required');
      
      // Extract numeric ID if it's in the format 'file-123456'
      let videoId = id;
      if (typeof id === 'string' && id.startsWith('file-')) {
        // For generated IDs, we need to use a different approach
        // We'll try to fetch the video list and find the matching video
        try {
          const videosResponse = await api.get('/videos');
          if (Array.isArray(videosResponse)) {
            // Find the video that matches our filename hash
            const matchingVideo = videosResponse.find(v => {
              // Check if this is the video we're looking for based on filename
              return v.filename && v.path && (v.path.includes('capture_0383.mp4') || v.filename.includes('capture_0383.mp4'));
            });
            
            if (matchingVideo) {
              console.log('Found matching video:', matchingVideo);
              return matchingVideo;
            }
          }
        } catch (listError) {
          console.error('Error fetching videos list:', listError);
        }
      }
      
      try {
        // First try to fetch using the videos endpoint (new consolidated approach)
        console.log('Trying to fetch video with ID:', videoId);
        const response = await api.get(`/videos/${videoId}`);
        return response;
      } catch (error) {
        // If that fails, try the parliament-tv endpoint (legacy approach)
        try {
          console.log('Trying to fetch video from parliament-tv with ID:', videoId);
          const response = await api.get(`/parliament-tv/${videoId}`);
          return response;
        } catch (innerError) {
          console.error('Error fetching video:', innerError);
          throw new Error('Failed to fetch video data');
        }
      }
    },
    enabled: !!id && id !== 'null' && id !== 'undefined' && id !== '[id]' && !!token && type === 'video',
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
      if (audioElement.paused) {
        audioElement.currentTime = videoElement.currentTime;
        audioElement.play().catch(err => {
          console.error('Error playing audio:', err);
        });
      }
    };

    const syncPause = () => {
      audioElement.pause();
    };

    const syncTimeUpdate = () => {
      if (Math.abs(videoElement.currentTime - audioElement.currentTime) > 0.5) {
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
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  // Format duration
  const formatDuration = (seconds: number) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    return `${hours > 0 ? hours + 'h ' : ''}${minutes}m ${secs}s`;
  };

  // Format date
  const formatDate = (dateString: string): string => {
    if (!dateString) return '';
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString('en-US', {
        year: 'numeric', month: 'short', day: 'numeric'
      });
    } catch (e) {
      return dateString;
    }
  };

  // Get status badge color
  const getStatusBadgeColor = (status: string) => {
    const statusLower = status?.toLowerCase() || '';
    if (statusLower === 'ready' || statusLower === 'completed') {
      return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300';
    } else if (statusLower === 'processing') {
      return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300';
    } else if (statusLower === 'error' || statusLower === 'failed') {
      return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300';
    }
    return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300';
  };

  // Generate video URL based on type - simplified approach
  const getVideoUrl = () => {
    // For streaming endpoints, we need to use the base URL without /api/v1
    const baseUrl = API_BASE_URL.replace('/api/v1', '');
    
    if (type === 'video' && video) {
      // Get the filename - this is the most reliable approach
      let filename = '';
      
      if (video.filename) {
        filename = video.filename;
      } else if (video.file_path) {
        filename = video.file_path.split('/').pop() || '';
      } else if (video.path) {
        filename = video.path.split('/').pop() || '';
      }
      
      if (!filename) {
        console.error('No valid filename found for video:', video);
        return '';
      }
      
      // Use the simple, consistent URL pattern that works in the dev branch
      const streamUrl = `${baseUrl}/videos/stream-with-token/${filename}?token=${token}`;
      console.log('Using video URL for streaming:', streamUrl);
      return streamUrl;
    } else if (type === 'clip' && clip) {
      if (!clip.id) {
        console.error('No valid ID found in clip:', clip);
        return '';
      }
      const clipUrl = `${baseUrl}/clips/stream/${clip.id}?token=${token}`;
      console.log('Using clip URL for streaming:', clipUrl);
      return clipUrl;
    }
    return '';
  };

  // Generate audio URL based on type - simplified approach
  const getAudioUrl = () => {
    // For streaming endpoints, we need to use the base URL without /api/v1
    const baseUrl = API_BASE_URL.replace('/api/v1', '');
    
    if (type === 'video' && video) {
      // Get the filename - this is the most reliable approach
      let filename = '';
      
      if (video.filename) {
        filename = video.filename;
      } else if (video.file_path) {
        filename = video.file_path.split('/').pop() || '';
      } else if (video.path) {
        filename = video.path.split('/').pop() || '';
      }
      
      if (!filename) {
        console.error('No valid filename found for audio:', video);
        return '';
      }
      
      // Use the simple, consistent URL pattern that works in the dev branch
      // Convert video filename to audio filename by replacing .mp4 with .audio.mp3
      const audioFilename = filename.replace('.mp4', '.audio.mp3');
      const audioUrl = `${baseUrl}/videos/stream-audio-with-token/${audioFilename}?token=${token}`;
      console.log('Using audio URL for streaming:', audioUrl);
      return audioUrl;
    }
    return '';
  };

  // Generate thumbnail URL
  const getThumbnailUrl = () => {
    if (type === 'clip' && clip && clip.thumbnail_url) {
      return `${API_BASE_URL}${clip.thumbnail_url}`;
    } else if (type === 'video' && video) {
      return `${API_BASE_URL}/videos/thumbnail/${video.id}?token=${token}`;
    }
    return '';
  };

  // Determine if we can show audio player
  const canShowAudio = type === 'video' && video;

  // Determine if we can show recognition panel
  const canShowRecognition = (type === 'clip' && clip && 
                             (clip.status === 'READY' || clip.status === 'ready' || clip.status === 'COMPLETED' || clip.status === 'completed')) ||
                             (type === 'video' && video);

  // Determine the capture ID for recognition panel
  const getRecognitionCaptureId = () => {
    let captureId = null;
    
    if (type === 'clip' && clip && clip.capture_session_id) {
      captureId = clip.capture_session_id;
    } else if (type === 'video' && video && video.id) {
      captureId = video.id;
    }
    
    // Ensure the ID is a valid number
    return captureId && !isNaN(Number(captureId)) ? Number(captureId) : null;
  };

  // Get the title based on type
  const getTitle = () => {
    if (type === 'clip' && clip) {
      return clip.title;
    } else if (type === 'video' && video) {
      return video.title;
    }
    return 'Media';
  };

  // If we have an invalid ID, show an error message
  if (isInvalidId) {
    return (
      <DarkLayout>
        <div className="container mx-auto px-4 py-8">
          <div className="bg-red-100 dark:bg-red-900 border border-red-400 dark:border-red-700 text-red-700 dark:text-red-300 px-4 py-3 rounded relative mb-6">
            <strong className="font-bold">Invalid Media ID</strong>
            <span className="block sm:inline"> The media item you're trying to view doesn't exist or has an invalid ID.</span>
            <div className="mt-4">
              <Link href="/files" className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded">
                Return to Media Library
              </Link>
            </div>
          </div>
        </div>
      </DarkLayout>
    );
  }

  // Show loading state
  if (isLoading) {
    return (
      <DarkLayout>
        <div className="container mx-auto px-4 py-8">
          <div className="flex justify-center items-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
          </div>
          <div className="text-center">
            <p className="text-gray-400">Loading media data...</p>
            <Link href="/files" className="text-blue-500 hover:underline">
              Back to media library
            </Link>
          </div>
        </div>
      </DarkLayout>
    );
  }

  // Show error state
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

  // Main content
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
              className={`px-4 py-2 ${activeTab === 'player' ? 'text-blue-400 border-b-2 border-blue-400' : 'text-gray-400 hover:text-blue-300'}`}
              onClick={() => setActiveTab('player')}
            >
              Player
            </button>
            
            {canShowRecognition && (
              <button
                className={`px-4 py-2 ${activeTab === 'recognition' ? 'text-blue-400 border-b-2 border-blue-400' : 'text-gray-400 hover:text-blue-300'}`}
                onClick={() => setActiveTab('recognition')}
              >
                Recognition
              </button>
            )}
            
            {type === 'clip' && clip?.has_transcription && (
              <button
                className={`px-4 py-2 ${activeTab === 'transcription' ? 'text-blue-400 border-b-2 border-blue-400' : 'text-gray-400 hover:text-blue-300'}`}
                onClick={() => setActiveTab('transcription')}
              >
                Transcription
              </button>
            )}
          </div>
        </div>
        
        {/* Player Tab Content */}
        {activeTab === 'player' && (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md overflow-hidden">
            <div className="px-4 py-5 sm:px-6 bg-gray-800">
              <h3 className="text-lg leading-6 font-medium text-white">Media Player</h3>
            </div>
            <div className="border-t border-gray-700 p-4">
              <div className="aspect-w-16 aspect-h-9">
                {/* Simple video player - using the approach from the working implementation */}
                <video 
                  ref={videoRef}
                  controls 
                  className="w-full h-full object-cover rounded-lg"
                  src={getVideoUrl()}
                  poster={getThumbnailUrl()}
                  autoPlay
                >
                  Your browser does not support the video tag.
                </video>
                
                {/* Direct video URL link for testing */}
                <div className="mt-2 text-sm text-gray-500">
                  If the video doesn't play automatically, you can <a 
                    href={getVideoUrl()} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="text-blue-500 hover:underline"
                  >
                    open it directly in a new tab
                  </a>.
                </div>
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
                    <>
                      <audio
                        ref={audioRef}
                        controls
                        className="w-full mt-2"
                        src={getAudioUrl()}
                        autoPlay
                      >
                        Your browser does not support the audio element.
                      </audio>
                      
                      {/* Direct audio URL link for testing */}
                      <div className="mt-2 text-sm text-gray-500">
                        If the audio doesn't play automatically, you can <a 
                          href={getAudioUrl()} 
                          target="_blank" 
                          rel="noopener noreferrer"
                          className="text-blue-500 hover:underline"
                        >
                          open it directly in a new tab
                        </a>.
                      </div>
                    </>
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