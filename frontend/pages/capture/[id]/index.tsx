import React, { useState } from 'react';
import { useRouter } from 'next/router';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import Link from 'next/link';
import MainLayout from '../../../components/layout/MainLayout';
import { withAuth, UserRole } from '../../../contexts/AuthContext';
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
              <div className="mb-6">
                <h3 className="text-lg font-medium mb-2">Audio</h3>
                
                {capture.audio_file_path ? (
                  <>
                    <button
                      onClick={() => setShowAudioPlayer(!showAudioPlayer)}
                      className="px-3 py-1 bg-blue-500 text-white rounded text-sm hover:bg-blue-600 transition-colors mb-2"
                    >
                      {showAudioPlayer ? 'Hide Audio Player' : 'Show Audio Player'}
                    </button>
                    
                    {showAudioPlayer && (
                      <div>
                        <AudioPlayer 
                          audioUrl={`${API_BASE_URL}/static/audio/${capture.audio_file_path.split('/').pop()}`}
                          title="Capture Audio"
                        />
                        
                        {/* Direct audio file links for testing */}
                        <div className="mt-2 text-xs text-gray-500">
                          <p>Try alternative audio sources:</p>
                          <ul className="list-disc pl-5 mt-1">
                            <li>
                              <a 
                                href={`${API_BASE_URL}/static/audio/${capture.audio_file_path.split('/').pop()}`} 
                                target="_blank" 
                                rel="noopener noreferrer"
                                className="text-blue-500 hover:underline"
                              >
                                Direct audio file link
                              </a>
                            </li>
                            <li>
                              <a 
                                href={`${API_BASE_URL}/static/audio/capture_${capture.id.toString().padStart(4, '0')}.audio.mp3`} 
                                target="_blank" 
                                rel="noopener noreferrer"
                                className="text-blue-500 hover:underline"
                              >
                                ID-based audio file
                              </a>
                            </li>
                            <li>
                              <a 
                                href={`${API_BASE_URL}/static/audio/sample1.mp3`} 
                                target="_blank" 
                                rel="noopener noreferrer"
                                className="text-blue-500 hover:underline"
                              >
                                Sample audio file 1
                              </a>
                            </li>
                          </ul>
                        </div>
                      </div>
                    )}
                  </>
                ) : (
                  <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4">
                    <div className="flex">
                      <div className="flex-shrink-0">
                        <svg className="h-5 w-5 text-yellow-400" viewBox="0 0 20 20" fill="currentColor">
                          <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                        </svg>
                      </div>
                      <div className="ml-3">
                        <p className="text-sm text-yellow-700">
                          No audio file available for this capture. Audio extraction may not have been performed.
                        </p>
                      </div>
                    </div>
                  </div>
                )}
              </div>
              
              {/* Debug Info */}
              <div className="mt-8">
                <details className="text-xs text-gray-500" open>
                  <summary className="cursor-pointer font-semibold">Debug Information</summary>
                  <div className="mt-2 p-3 bg-gray-100 rounded">
                    <h4 className="font-semibold mb-2">Audio Information</h4>
                    <p>Audio File Path: {capture.audio_file_path || 'Not available'}</p>
                    <p>Audio File Name: {capture.audio_file_path ? capture.audio_file_path.split('/').pop() : 'Not available'}</p>
                    <p>Audio Source URL: {capture.audio_file_path ? 
                      `${API_BASE_URL}/static/audio/${capture.audio_file_path.split('/').pop()}` : 'Not available'}</p>
                    
                    <h4 className="font-semibold mt-3 mb-2">Video Information</h4>
                    <p>Video File Path: {capture.file_path || 'Not available'}</p>
                    <p>Video File Name: {capture.file_path ? capture.file_path.split('/').pop() : 'Not available'}</p>
                    <p>Source URL: {capture.source_url || 'Not available'}</p>
                    
                    <h4 className="font-semibold mt-3 mb-2">Capture Information</h4>
                    <p>Capture ID: {capture.id}</p>
                    <p>Status: {capture.status}</p>
                    <p>Created At: {new Date(capture.created_at).toLocaleString()}</p>
                    <p>Metadata: {JSON.stringify(capture.metadata || {}, null, 2)}</p>
                    
                    <h4 className="font-semibold mt-3 mb-2">Alternative Audio Paths</h4>
                    <p>ID-based path: capture_{capture.id.toString().padStart(4, '0')}.audio.mp3</p>
                    <p>Full ID-based URL: {`${API_BASE_URL}/static/audio/capture_${capture.id.toString().padStart(4, '0')}.audio.mp3`}</p>
                    <p>Sample Audio URL: {`${API_BASE_URL}/static/audio/sample1.mp3`}</p>
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
