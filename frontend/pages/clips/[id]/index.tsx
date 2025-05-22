import React, { useState } from 'react';
import { useRouter } from 'next/router';
import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import DarkLayout from '../../../components/layout/DarkLayout';
import { withAuth } from '../../../contexts/AuthContext';
import { api } from '../../../utils/api';

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
  created_by: {
    id: number;
    name: string;
    email: string;
  };
  has_transcription: boolean;
  status: string;
}

interface Transcription {
  id: number;
  video_clip_id: number;
  content: string;
  segments: TranscriptionSegment[];
  language: string;
  status: string;
  created_at: string;
}

interface TranscriptionSegment {
  id: number;
  start_time: number;
  end_time: number;
  text: string;
  speaker?: string;
}

const VideoClipDetailPage: React.FC = () => {
  const router = useRouter();
  const { id } = router.query;
  const [activeTab, setActiveTab] = useState<'details' | 'transcription'>('details');
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);

  // Fetch video clip details
  const { data: clip, isLoading: clipLoading, isError: clipError } = useQuery<VideoClip>({
    queryKey: ['videoClip', id],
    queryFn: async () => {
      if (!id) throw new Error('No clip ID provided');
      return await api.get(`/clips/${id}`);
    },
    enabled: !!id,
  });

  // Fetch transcription if available
  const { data: transcription, isLoading: transcriptionLoading } = useQuery<Transcription>({
    queryKey: ['transcription', id],
    queryFn: async () => {
      if (!id) throw new Error('No clip ID provided');
      return await api.get(`/transcriptions/clip/${id}`);
    },
    enabled: !!id && !!clip?.has_transcription,
  });

  // Format duration in seconds to MM:SS
  const formatDuration = (seconds: number): string => {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
  };

  // Format date to readable format
  const formatDate = (dateString: string): string => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-GB', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  // Handle video player events
  const handleTimeUpdate = (e: React.SyntheticEvent<HTMLVideoElement>) => {
    setCurrentTime(e.currentTarget.currentTime);
  };

  const handlePlayPause = () => {
    setIsPlaying(!isPlaying);
  };

  // Jump to specific time in video
  const jumpToTime = (timeInSeconds: number) => {
    const videoElement = document.querySelector('video');
    if (videoElement) {
      videoElement.currentTime = timeInSeconds;
      if (!isPlaying) {
        videoElement.play();
        setIsPlaying(true);
      }
    }
  };

  // Find the current segment in the transcription
  const getCurrentSegment = () => {
    if (!transcription || !transcription.segments) return null;
    
    return transcription.segments.find(
      segment => currentTime >= segment.start_time && currentTime <= segment.end_time
    );
  };

  const currentSegment = getCurrentSegment();

  if (clipLoading) {
    return (
      <DarkLayout>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 flex items-center justify-center min-h-screen">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
            <p className="mt-4 text-gray-300">Loading video clip...</p>
          </div>
        </div>
      </DarkLayout>
    );
  }

  if (clipError || !clip) {
    return (
      <DarkLayout>
        <div className="page-container">
          <div className="bg-red-50 border-l-4 border-red-500 p-4 mb-6">
            <div className="flex">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
              </div>
              <div className="ml-3">
                <p className="text-sm text-red-700">
                  Error loading video clip. Please try again later.
                </p>
              </div>
            </div>
          </div>
          <div className="flex justify-center">
            <Link href="/clips">
              <span className="btn-primary rounded-md px-4 py-2 text-center cursor-pointer inline-block">
                Back to Video Clips
              </span>
            </Link>
          </div>
        </div>
      </DarkLayout>
    );
  }

  return (
    <DarkLayout>
      <div className="page-container">
        {/* Header with title and actions */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between mb-6">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">{clip.title}</h1>
            <p className="text-gray-500 mt-1">
              {formatDuration(clip.duration)} • Created {formatDate(clip.created_at)}
            </p>
          </div>
          <div className="mt-4 md:mt-0 flex space-x-3">
            <Link href={`/clips/${clip.id}/edit`}>
              <span className="btn-primary rounded-md px-4 py-2 text-center cursor-pointer inline-block">
                Edit Clip
              </span>
            </Link>
            <Link href={`/social/new?clipId=${clip.id}`}>
              <span className="bg-secondary text-white hover:bg-secondary-dark rounded-md px-4 py-2 text-center cursor-pointer inline-block">
                Share on Social Media
              </span>
            </Link>
          </div>
        </div>

        {/* Video player */}
        <div className="bg-white rounded-lg shadow overflow-hidden mb-6">
          <div className="aspect-w-16 aspect-h-9 bg-black">
            {clip.file_path && (
              <video
                src={clip.file_path}
                poster={clip.thumbnail_url}
                controls
                onTimeUpdate={handleTimeUpdate}
                onPlay={() => setIsPlaying(true)}
                onPause={() => setIsPlaying(false)}
                className="w-full h-full object-contain"
              />
            )}
          </div>
        </div>

        {/* Tabs */}
        <div className="bg-white rounded-lg shadow mb-6">
          <div className="border-b border-gray-200">
            <nav className="-mb-px flex">
              <button
                onClick={() => setActiveTab('details')}
                className={`py-4 px-6 text-center border-b-2 font-medium text-sm ${
                  activeTab === 'details'
                    ? 'border-primary text-primary'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                Details
              </button>
              {clip.has_transcription && (
                <button
                  onClick={() => setActiveTab('transcription')}
                  className={`py-4 px-6 text-center border-b-2 font-medium text-sm ${
                    activeTab === 'transcription'
                      ? 'border-primary text-primary'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  Transcription
                </button>
              )}
            </nav>
          </div>

          <div className="p-6">
            {activeTab === 'details' ? (
              <div>
                <h2 className="text-lg font-medium text-gray-900 mb-4">Clip Details</h2>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <h3 className="text-sm font-medium text-gray-500 mb-1">Description</h3>
                    <p className="text-gray-900">{clip.description || 'No description provided'}</p>
                  </div>
                  
                  <div>
                    <h3 className="text-sm font-medium text-gray-500 mb-1">Created By</h3>
                    <p className="text-gray-900">{clip.created_by?.name || 'Unknown'}</p>
                  </div>
                  
                  <div>
                    <h3 className="text-sm font-medium text-gray-500 mb-1">Status</h3>
                    <span className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${
                      clip.status === 'ready'
                        ? 'bg-green-100 text-green-800'
                        : clip.status === 'processing'
                        ? 'bg-yellow-100 text-yellow-800'
                        : 'bg-red-100 text-red-800'
                    }`}>
                      {clip.status.charAt(0).toUpperCase() + clip.status.slice(1)}
                    </span>
                    {clip.has_transcription && (
                      <span className="ml-2 px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full bg-blue-100 text-blue-800">
                        Transcribed
                      </span>
                    )}
                  </div>
                  
                  <div>
                    <h3 className="text-sm font-medium text-gray-500 mb-1">File Path</h3>
                    <p className="text-gray-900 break-all">{clip.file_path}</p>
                  </div>
                </div>
              </div>
            ) : (
              <div>
                <h2 className="text-lg font-medium text-gray-900 mb-4">Transcription</h2>
                
                {transcriptionLoading ? (
                  <div className="text-center py-8">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
                    <p className="mt-4 text-gray-600">Loading transcription...</p>
                  </div>
                ) : !transcription ? (
                  <div className="text-center py-8">
                    <p className="text-gray-600">No transcription available for this clip.</p>
                  </div>
                ) : (
                  <div>
                    {/* Current segment highlight */}
                    {currentSegment && (
                      <div className="mb-6 p-4 bg-blue-50 border-l-4 border-blue-500 rounded-md">
                        <p className="text-lg font-medium text-gray-900">
                          {currentSegment.text}
                        </p>
                        <p className="text-sm text-gray-500 mt-1">
                          {formatDuration(currentSegment.start_time)} - {formatDuration(currentSegment.end_time)}
                          {currentSegment.speaker && ` • ${currentSegment.speaker}`}
                        </p>
                      </div>
                    )}
                    
                    {/* Full transcription */}
                    <div className="space-y-4 max-h-96 overflow-y-auto">
                      {transcription.segments.map((segment, index) => (
                        <div 
                          key={index} 
                          className={`p-3 rounded-md cursor-pointer hover:bg-gray-50 ${
                            currentSegment?.id === segment.id ? 'bg-blue-50' : ''
                          }`}
                          onClick={() => jumpToTime(segment.start_time)}
                        >
                          <p className="text-gray-900">{segment.text}</p>
                          <p className="text-xs text-gray-500 mt-1">
                            {formatDuration(segment.start_time)} - {formatDuration(segment.end_time)}
                            {segment.speaker && ` • ${segment.speaker}`}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </DarkLayout>
  );
};

export default withAuth(VideoClipDetailPage);
