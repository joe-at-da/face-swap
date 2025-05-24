import React, { useState } from 'react';
import { useRouter } from 'next/router';
import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import DarkLayout from '../../../components/layout/DarkLayout';
import { withAuth } from '../../../contexts/AuthContext';
import { api } from '../../../utils/api';
import SocialMediaShare from '../../../components/clips/SocialMediaShare';

interface VideoClip {
  id: number;
  title: string;
  description: string;
  duration: number;
  file_path: string;
  storage_path: string;
  thumbnail_url: string;
  created_at: string;
  updated_at: string;
  owner_id: number;
  created_by: {
    id: number;
    name: string;
    email: string;
  };
  has_transcription: boolean;
  status: string;
  source_url: string;
  start_time: string;
  end_time: string;
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
  const [activeTab, setActiveTab] = useState<'details' | 'transcription' | 'share'>('details');
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
    refetchOnWindowFocus: false,
  });

  // Fetch transcription if available
  const { data: transcription, isLoading: transcriptionLoading } = useQuery<Transcription>({
    queryKey: ['transcription', id],
    queryFn: async () => {
      if (!id) throw new Error('No clip ID provided');
      return await api.get(`/transcriptions/clip/${id}`);
    },
    enabled: !!id && !!clip?.has_transcription,
    refetchOnWindowFocus: false,
  });
  
  // Fetch speaker recognition data if available
  const { data: speakerData } = useQuery({
    queryKey: ['speakerRecognition', id],
    queryFn: async () => {
      if (!id) throw new Error('No clip ID provided');
      try {
        return await api.get(`/recognition/speakers/clip/${id}`);
      } catch (error) {
        console.log('No speaker recognition data available');
        return null;
      }
    },
    enabled: !!id,
    refetchOnWindowFocus: false,
  });
  
  // Fetch face recognition data if available
  const { data: faceData } = useQuery({
    queryKey: ['faceRecognition', id],
    queryFn: async () => {
      if (!id) throw new Error('No clip ID provided');
      try {
        return await api.get(`/recognition/faces/clip/${id}`);
      } catch (error) {
        console.log('No face recognition data available');
        return null;
      }
    },
    enabled: !!id,
    refetchOnWindowFocus: false,
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
            <h1 className="text-3xl font-bold text-white">{clip.title}</h1>
            <p className="text-gray-400 mt-1">
              {formatDuration(clip.duration)} • Created {formatDate(clip.created_at)}
            </p>
          </div>
          <div className="mt-4 md:mt-0 flex space-x-3">
            <Link href={`/clips/${clip.id}/edit`}>
              <span className="bg-blue-600 text-white hover:bg-blue-700 rounded-md px-4 py-2 text-center cursor-pointer inline-block transition duration-150">
                Edit Clip
              </span>
            </Link>
            <Link href={`/social/new?clipId=${clip.id}`}>
              <span className="bg-indigo-600 text-white hover:bg-indigo-700 rounded-md px-4 py-2 text-center cursor-pointer inline-block transition duration-150">
                Share on Social Media
              </span>
            </Link>
          </div>
        </div>

        {/* Video player */}
        <div className="bg-gray-800 rounded-lg shadow overflow-hidden mb-6">
          <div className="aspect-w-16 aspect-h-9 bg-black">
            {clip.storage_path ? (
              <video
                src={`/api/v1/stream/clip/${clip.id}`}
                poster={clip.thumbnail_url || `/api/v1/thumbnail/clip/${clip.id}`}
                controls
                onTimeUpdate={handleTimeUpdate}
                onPlay={() => setIsPlaying(true)}
                onPause={() => setIsPlaying(false)}
                className="w-full h-full object-contain"
                preload="metadata"
              />
            ) : (
              <div className="flex items-center justify-center h-full">
                <div className="text-center text-gray-300">
                  <svg className="w-16 h-16 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                  </svg>
                  <p className="text-lg font-medium">Processing Video</p>
                  <p className="mt-2">The video is still being processed. Please check back later.</p>
                </div>
              </div>
            )}
          </div>
          {clip.status === 'processing' && (
            <div className="bg-yellow-100 text-yellow-800 p-3 text-center">
              <p className="text-sm font-medium">This clip is still processing. The video may not be available yet.</p>
            </div>
          )}
        </div>

        {/* Tabs */}
        <div className="bg-gray-800 rounded-lg shadow mb-6">
          <div className="border-b border-gray-700">
            <nav className="-mb-px flex space-x-8 px-4">
              <button
                onClick={() => setActiveTab('details')}
                className={`whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm ${activeTab === 'details' ? 'border-blue-500 text-blue-500' : 'border-transparent text-gray-400 hover:text-gray-300 hover:border-gray-600'}`}
              >
                Details
              </button>
              
              <button
                onClick={() => setActiveTab('transcription')}
                className={`whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm ${activeTab === 'transcription' ? 'border-blue-500 text-blue-500' : 'border-transparent text-gray-400 hover:text-gray-300 hover:border-gray-600'}`}
                disabled={!clip?.has_transcription}
              >
                Transcription
              </button>
              
              <button
                onClick={() => setActiveTab('share')}
                className={`whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm ${activeTab === 'share' ? 'border-blue-500 text-blue-500' : 'border-transparent text-gray-400 hover:text-gray-300 hover:border-gray-600'}`}
              >
                Share
              </button>
            </nav>
          </div>

          <div className="p-6">
            {activeTab === 'details' ? (
              <div>
                <h2 className="text-lg font-medium text-white mb-4">Clip Details</h2>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <h3 className="text-sm font-medium text-gray-400 mb-1">Description</h3>
                    <p className="text-gray-300">{clip.description || 'No description provided'}</p>
                  </div>
                  
                  <div>
                    <h3 className="text-sm font-medium text-gray-400 mb-1">Created By</h3>
                    <p className="text-gray-300">{clip.created_by?.name || 'Unknown'}</p>
                  </div>
                  
                  <div>
                    <h3 className="text-sm font-medium text-gray-400 mb-1">Status</h3>
                    <span className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${
                      clip.status === 'ready'
                        ? 'bg-green-800 text-green-200'
                        : clip.status === 'processing'
                        ? 'bg-yellow-800 text-yellow-200'
                        : 'bg-red-800 text-red-200'
                    }`}>
                      {clip.status.charAt(0).toUpperCase() + clip.status.slice(1)}
                    </span>
                    {clip.has_transcription && (
                      <span className="ml-2 px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full bg-blue-800 text-blue-200">
                        Transcribed
                      </span>
                    )}
                  </div>
                  
                  <div>
                    <h3 className="text-sm font-medium text-gray-400 mb-1">Source URL</h3>
                    <p className="text-gray-300 break-all">{clip.source_url || 'Not available'}</p>
                  </div>
                  
                  <div>
                    <h3 className="text-sm font-medium text-gray-400 mb-1">Storage Path</h3>
                    <p className="text-gray-300 break-all">{clip.storage_path || 'Processing...'}</p>
                  </div>
                  
                  <div>
                    <h3 className="text-sm font-medium text-gray-400 mb-1">Video URL</h3>
                    <a 
                      href={`/api/v1/stream/clip/${clip.id}`} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="text-blue-400 hover:text-blue-300 break-all"
                    >
                      {`/api/v1/stream/clip/${clip.id}`}
                    </a>
                  </div>
                </div>
              </div>
            ) : activeTab === 'transcription' ? (
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
                    {/* Speaker and Face Recognition Summary */}
                    {(speakerData || faceData) && (
                      <div className="mb-6 p-4 bg-gray-800 text-white rounded-md">
                        <h3 className="text-lg font-medium mb-2">Recognition Data</h3>
                        
                        {speakerData && (
                          <div className="mb-3">
                            <h4 className="text-md font-medium text-blue-400">Speaker Recognition</h4>
                            <p className="text-sm text-gray-300">
                              {speakerData.speaker_name || 'Unknown speaker'}
                              {speakerData.confidence && ` (${Math.round(speakerData.confidence * 100)}% confidence)`}
                            </p>
                          </div>
                        )}
                        
                        {faceData && (
                          <div>
                            <h4 className="text-md font-medium text-green-400">Face Recognition</h4>
                            <p className="text-sm text-gray-300">
                              {faceData.person_name || 'Unknown person'}
                              {faceData.confidence && ` (${Math.round(faceData.confidence * 100)}% confidence)`}
                            </p>
                          </div>
                        )}
                      </div>
                    )}
                    
                    {/* Current segment highlight */}
                    {currentSegment && (
                      <div className="mb-6 p-4 bg-blue-900 text-white border-l-4 border-blue-500 rounded-md">
                        <p className="text-lg font-medium">
                          {currentSegment.text}
                        </p>
                        <div className="flex items-center mt-2">
                          <span className="text-sm text-gray-300">
                            {formatDuration(currentSegment.start_time)} - {formatDuration(currentSegment.end_time)}
                          </span>
                          {currentSegment.speaker && (
                            <span className="ml-2 px-2 py-1 text-xs font-semibold rounded-full bg-blue-700 text-white">
                              {currentSegment.speaker}
                            </span>
                          )}
                          <button 
                            onClick={() => jumpToTime(currentSegment.start_time)}
                            className="ml-auto text-xs bg-blue-600 hover:bg-blue-700 text-white py-1 px-2 rounded"
                          >
                            Play
                          </button>
                        </div>
                      </div>
                    )}
                    
                    {/* Full transcription */}
                    <div className="space-y-4 max-h-96 overflow-y-auto">
                      {transcription.segments.map((segment, index) => (
                        <div 
                          key={index} 
                          className={`p-3 rounded-md cursor-pointer hover:bg-gray-700 ${
                            currentSegment?.id === segment.id ? 'bg-gray-700' : 'bg-gray-800'
                          }`}
                          onClick={() => jumpToTime(segment.start_time)}
                        >
                          <p className="text-white">{segment.text}</p>
                          <div className="flex items-center mt-1">
                            <span className="text-xs text-gray-400">
                              {formatDuration(segment.start_time)} - {formatDuration(segment.end_time)}
                            </span>
                            {segment.speaker && (
                              <span className="ml-2 px-2 py-0.5 text-xs font-semibold rounded-full bg-blue-600 text-white">
                                {segment.speaker}
                              </span>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              /* Share Tab */
              <div>
                {clip && (
                  <SocialMediaShare
                    clipId={clip.id}
                    clipTitle={clip.title}
                    clipUrl={`/api/v1/stream/clip/${clip.id}`}
                    thumbnailUrl={clip.thumbnail_url || `/api/v1/thumbnail/clip/${clip.id}`}
                    duration={clip.duration}
                    hasTranscription={clip.has_transcription}
                    startTime={clip.start_time}
                    endTime={clip.end_time}
                  />
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
