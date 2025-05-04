import React, { useState } from 'react';
import { useRouter } from 'next/router';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import Link from 'next/link';
import MainLayout from '../../../components/layout/MainLayout';
import { withAuth } from '../../../contexts/AuthContext';
import { UserRole } from '../../../contexts/AuthContext';
import { api } from '../../../utils/api';
import AudioPlayer from '../../../components/AudioPlayer';

interface CaptureSession {
  id: number;
  title: string;
  description: string;
  status: string;
  source_url: string;
  start_time: string;
  end_time: string | null;
  scheduled_start: string | null;
  scheduled_end: string | null;
  file_path: string | null;
  audio_file_path: string | null;
  file_size: number | null;
  duration: number | null;
  created_by_id: number;
  created_by: {
    id: number;
    name: string;
    email: string;
  };
  created_at: string;
  updated_at: string;
  metadata?: Record<string, any>;
}

const CaptureDetailPage = () => {
  const router = useRouter();
  const { id } = router.query;
  const queryClient = useQueryClient();
  const [showAudioPlayer, setShowAudioPlayer] = useState(false);
  
  // API base URL for streaming
  const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api/v1';
  
  // Fetch capture session details
  const { data: capture, isLoading, isError } = useQuery({
    queryKey: ['captureSession', id],
    queryFn: async () => {
      if (!id) return null;
      return await api.get(`/capture/${id}`);
    },
    enabled: !!id,
  });

  if (isLoading) {
    return (
      <MainLayout title="Loading Capture | Parliament Video Clip Manager">
        <div className="container mx-auto p-6">
          <div className="flex justify-center items-center h-64">
            <div className="text-gray-500">Loading capture session details...</div>
          </div>
        </div>
      </MainLayout>
    );
  }

  if (isError || !capture) {
    return (
      <MainLayout title="Error | Parliament Video Clip Manager">
        <div className="container mx-auto p-6">
          <div className="bg-red-50 border-l-4 border-red-500 p-4">
            <div className="flex">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
              </div>
              <div className="ml-3">
                <p className="text-sm text-red-700">Error loading capture session. The session may not exist or you don't have permission to view it.</p>
              </div>
            </div>
          </div>
          <div className="mt-4">
            <Link href="/capture">
              <span className="text-blue-600 hover:text-blue-800 cursor-pointer">
                Back to Capture Sessions
              </span>
            </Link>
          </div>
        </div>
      </MainLayout>
    );
  }

  return (
    <MainLayout title={`${capture.title} | Capture Session | Parliament Video Clip Manager`}>
      <div className="container mx-auto p-6">
        <div className="mb-6">
          <Link href="/capture">
            <span className="text-blue-600 hover:text-blue-800 cursor-pointer">
              &larr; Back to Capture Sessions
            </span>
          </Link>
        </div>
        
        <div className="bg-white shadow-md rounded-lg p-6 mb-6">
          <h1 className="text-2xl font-bold mb-4">{capture.title}</h1>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h2 className="text-xl font-semibold mb-4">Capture Details</h2>
              <div className="space-y-4">
                <div>
                  <p className="text-sm font-medium text-gray-500">Status</p>
                  <p className="text-sm text-gray-900">{capture.status}</p>
                </div>
                
                <div>
                  <p className="text-sm font-medium text-gray-500">Start Time</p>
                  <p className="text-sm text-gray-900">{new Date(capture.start_time).toLocaleString()}</p>
                </div>
                
                {capture.end_time && (
                  <div>
                    <p className="text-sm font-medium text-gray-500">End Time</p>
                    <p className="text-sm text-gray-900">{new Date(capture.end_time).toLocaleString()}</p>
                  </div>
                )}
                
                <div>
                  <p className="text-sm font-medium text-gray-500">Source URL</p>
                  <p className="text-sm text-gray-900 break-all">
                    <a href={capture.source_url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:text-blue-800">
                      {capture.source_url}
                    </a>
                  </p>
                </div>
                
                {capture.description && (
                  <div>
                    <p className="text-sm font-medium text-gray-500">Description</p>
                    <p className="text-sm text-gray-900 whitespace-pre-line">{capture.description}</p>
                  </div>
                )}
              </div>
            </div>
            
            <div>
              <h2 className="text-xl font-semibold mb-4">Media</h2>
              
              {/* Video Preview */}
              {capture.file_path && (
                <div className="mb-6">
                  <h3 className="text-lg font-medium mb-2">Video</h3>
                  <video 
                    controls 
                    className="w-full rounded" 
                    src={`${API_BASE_URL}/parliament-tv/${capture.id}/stream`}
                  >
                    Your browser does not support the video tag.
                  </video>
                </div>
              )}
              
              {/* Audio Player */}
              {capture.audio_file_path && (
                <div className="mb-6">
                  <h3 className="text-lg font-medium mb-2">Audio</h3>
                  <button
                    onClick={() => setShowAudioPlayer(!showAudioPlayer)}
                    className="px-3 py-1 bg-blue-500 text-white rounded text-sm hover:bg-blue-600 transition-colors mb-2"
                  >
                    {showAudioPlayer ? 'Hide Audio Player' : 'Show Audio Player'}
                  </button>
                  
                  {showAudioPlayer && (
                    <AudioPlayer 
                      audioUrl={`${API_BASE_URL}/videos/static/audio/${capture.audio_file_path.split('/').pop()}`}
                      title="Capture Audio"
                    />
                  )}
                </div>
              )}
              
              {/* Debug Info */}
              <div className="mt-8">
                <details className="text-xs text-gray-500">
                  <summary className="cursor-pointer">Debug Information</summary>
                  <div className="mt-2 p-3 bg-gray-100 rounded">
                    <p>Audio File Path: {capture.audio_file_path || 'Not available'}</p>
                    <p>Video File Path: {capture.file_path || 'Not available'}</p>
                    <p>Audio Source: {capture.audio_file_path ? 
                      `${API_BASE_URL}/videos/static/audio/${capture.audio_file_path.split('/').pop()}` : 'Not available'}</p>
                    <p>Metadata: {JSON.stringify(capture.metadata || {}, null, 2)}</p>
                  </div>
                </details>
              </div>
            </div>
          </div>
        </div>
      </div>
    </MainLayout>
  );
};

export default withAuth(CaptureDetailPage, [UserRole.ADMIN, UserRole.MP, UserRole.STAFF]);
