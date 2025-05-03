import React, { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/router';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Link from 'next/link';
import MainLayout from '../../../components/layout/MainLayout';
import { withAuth } from '../../../contexts/AuthContext';
import { UserRole } from '../../../contexts/AuthContext';
import { api } from '../../../utils/api';

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

interface CaptureLog {
  id: number;
  capture_id: number;
  message: string;
  level: 'info' | 'warning' | 'error';
  timestamp: string;
}

const CaptureDetailPage: React.FC = () => {
  const router = useRouter();
  const { id } = router.query;
  const queryClient = useQueryClient();
  const videoRef = useRef<HTMLVideoElement>(null);
  
  // API base URL for streaming
  const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api/v1';
  
  // State for logs pagination
  const [logsPage, setLogsPage] = useState(1);
  const [logsPerPage] = useState(20);
  
  // Auto-refresh for active captures
  const [autoRefresh, setAutoRefresh] = useState(true);
  
  // Fetch capture session details
  const { data: capture, isLoading, isError, refetch } = useQuery({
    queryKey: ['captureSession', id],
    queryFn: async () => {
      if (!id) return null;
      return await api.get(`/capture/${id}`);
    },
    enabled: !!id,
    refetchInterval: autoRefresh ? 5000 : false, // Refresh every 5 seconds if auto-refresh is enabled
  });
  
  // Fetch capture logs
  const { data: logsData, isLoading: logsLoading, refetch: refetchLogs } = useQuery({
    queryKey: ['captureLogs', id, logsPage],
    queryFn: async () => {
      if (!id) return null;
      return await api.get(`/capture/${id}/logs`, {
        page: logsPage,
        per_page: logsPerPage,
      });
    },
    enabled: !!id,
    refetchInterval: autoRefresh ? 5000 : false, // Refresh every 5 seconds if auto-refresh is enabled
  });
  
  // Stop capture mutation
  const stopCaptureMutation = useMutation({
    mutationFn: async (captureId: number) => {
      return await api.post(`/capture/${captureId}/stop`);
    },
    onSuccess: () => {
      refetch();
      queryClient.invalidateQueries({ queryKey: ['captureSessions'] });
    },
  });
  
  // Effect to disable auto-refresh when capture is not active
  useEffect(() => {
    if (capture && capture.status !== 'active' && capture.status !== 'processing') {
      setAutoRefresh(false);
    }
  }, [capture]);
  
  // Handle stop capture
  const handleStopCapture = () => {
    if (!capture) return;
    
    if (confirm('Are you sure you want to stop this capture session?')) {
      stopCaptureMutation.mutate(capture.id);
    }
  };
  
  // Format duration in seconds to HH:MM:SS
  const formatDuration = (seconds: number | null): string => {
    if (seconds === null) return '--:--:--';
    
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const remainingSeconds = Math.floor(seconds % 60);
    
    return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
  };
  
  // Format date to readable format
  const formatDate = (dateString: string | null): string => {
    if (!dateString) return '--';
    
    const date = new Date(dateString);
    return date.toLocaleDateString('en-GB', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };
  
  // Format file size
  const formatFileSize = (bytes: number | null): string => {
    if (bytes === null) return '--';
    
    if (bytes < 1024) return bytes + ' B';
    else if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB';
    else if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
    else return (bytes / (1024 * 1024 * 1024)).toFixed(2) + ' GB';
  };
  
  // Calculate capture duration for active captures
  const getCaptureDuration = (): string => {
    if (!capture) return '--:--:--';
    
    if (capture.duration) {
      return formatDuration(capture.duration);
    }
    
    if (capture.status === 'active' && capture.start_time) {
      const startTime = new Date(capture.start_time).getTime();
      const now = new Date().getTime();
      const durationSeconds = (now - startTime) / 1000;
      return formatDuration(durationSeconds);
    }
    
    return '--:--:--';
  };
  
  // Get status badge color
  const getStatusBadgeClass = (status: string): string => {
    switch (status) {
      case 'active':
        return 'bg-green-100 text-green-800';
      case 'completed':
        return 'bg-blue-100 text-blue-800';
      case 'failed':
        return 'bg-red-100 text-red-800';
      case 'processing':
        return 'bg-yellow-100 text-yellow-800';
      case 'scheduled':
        return 'bg-purple-100 text-purple-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };
  
  // Get log level badge color
  const getLogLevelBadgeClass = (level: string): string => {
    switch (level) {
      case 'info':
        return 'bg-blue-100 text-blue-800';
      case 'warning':
        return 'bg-yellow-100 text-yellow-800';
      case 'error':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };
  
  // Handle refresh button click
  const handleRefresh = () => {
    refetch();
    refetchLogs();
  };
  
  // Toggle auto-refresh
  const toggleAutoRefresh = () => {
    setAutoRefresh(!autoRefresh);
  };
  
  // Calculate time remaining for active captures
  const getTimeRemaining = (): string => {
    if (!capture || !capture.scheduled_end || capture.status !== 'active') return '--';
    
    const endTime = new Date(capture.scheduled_end).getTime();
    const now = new Date().getTime();
    const remainingMs = endTime - now;
    
    if (remainingMs <= 0) return 'Ending soon';
    
    const hours = Math.floor(remainingMs / (1000 * 60 * 60));
    const minutes = Math.floor((remainingMs % (1000 * 60 * 60)) / (1000 * 60));
    
    return `${hours}h ${minutes}m remaining`;
  };
  
  // Check if capture is scheduled but not started yet
  const isScheduled = (): boolean => {
    if (!capture) return false;
    return capture.status === 'scheduled' && !!capture.scheduled_start;
  };
  
  // Get time until scheduled start
  const getTimeUntilStart = (): string => {
    if (!capture || !capture.scheduled_start) return '';
    
    const now = new Date();
    const scheduledStart = new Date(capture.scheduled_start);
    const diffMs = scheduledStart.getTime() - now.getTime();
    
    if (diffMs <= 0) return 'Starting soon';
    
    const diffSecs = Math.floor(diffMs / 1000);
    const days = Math.floor(diffSecs / 86400);
    const hours = Math.floor((diffSecs % 86400) / 3600);
    const minutes = Math.floor((diffSecs % 3600) / 60);
    const seconds = diffSecs % 60;
    
    if (days > 0) {
      return `${days}d ${hours}h ${minutes}m`;
    } else if (hours > 0) {
      return `${hours}h ${minutes}m ${seconds}s`;
    } else {
      return `${minutes}m ${seconds}s`;
    }
  };
  
  // Check if a capture is a Parliament TV capture
  const isParliamentTVCapture = (capture: CaptureSession): boolean => {
    if (!capture) return false;
    
    // Check if source URL is from Parliament TV
    if (capture.source_url && capture.source_url.includes('parliamentlive.tv')) {
      console.log('Parliament TV capture detected via source_url:', capture.source_url);
      return true;
    }
    
    // Check metadata for Parliament TV specific fields
    if (capture.metadata && typeof capture.metadata === 'object') {
      const metadata = capture.metadata as Record<string, any>;
      const isParlTV = !!metadata.parliament_tv_url;
      if (isParlTV) {
        console.log('Parliament TV capture detected via metadata:', metadata.parliament_tv_url);
      }
      return isParlTV;
    }
    
    return false;
  };
  
  // Get video source URL based on capture type
  const getVideoSourceUrl = (capture: CaptureSession): string => {
    if (!capture) return '';
    
    // For Parliament TV captures, use the streaming endpoint
    if (isParliamentTVCapture(capture)) {
      const streamUrl = `${API_BASE_URL}/parliament-tv/${capture.id}/stream`;
      console.log('Using Parliament TV streaming URL:', streamUrl);
      return streamUrl;
    }
    
    // For regular captures, use the file path
    if (capture.file_path) {
      console.log('Using regular file path:', capture.file_path);
      return capture.file_path;
    }
    
    // Fallback to the Parliament TV streaming endpoint even if not detected as Parliament TV
    // This increases our chances of finding the video
    const fallbackUrl = `${API_BASE_URL}/parliament-tv/${capture.id}/stream`;
    console.log('Using fallback streaming URL:', fallbackUrl);
    return fallbackUrl;
  };
  
  // Handle video error
  const handleVideoError = (e: React.SyntheticEvent<HTMLVideoElement, Event>) => {
    console.error('Video playback error:', e);
    const videoElement = e.currentTarget;
    
    // Try the alternate source if the current one fails
    if (videoElement.src.includes('/parliament-tv/')) {
      // If Parliament TV streaming failed, try the file path directly
      if (capture?.file_path) {
        console.log('Trying direct file path after streaming error:', capture.file_path);
        videoElement.src = capture.file_path;
        videoElement.load();
      }
    } else if (capture) {
      // If direct file path failed, try Parliament TV streaming
      const streamUrl = `${API_BASE_URL}/parliament-tv/${capture.id}/stream`;
      console.log('Trying Parliament TV streaming after direct path error:', streamUrl);
      videoElement.src = streamUrl;
      videoElement.load();
    }
  };
  
  if (isLoading) {
    return (
      <MainLayout title="Capture Session | Parliament Video Clip Manager">
        <div className="page-container">
          <div className="flex justify-center items-center h-64">
            <div className="text-gray-500">Loading capture session details...</div>
          </div>
        </div>
      </MainLayout>
    );
  }
  
  if (isError || !capture) {
    return (
      <MainLayout title="Capture Session | Parliament Video Clip Manager">
        <div className="page-container">
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
              <span className="text-primary hover:text-primary-dark cursor-pointer">
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
      <div className="page-container">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:justify-between md:items-center mb-6 space-y-4 md:space-y-0">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">{capture.title}</h1>
            <div className="flex items-center mt-2">
              <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${getStatusBadgeClass(capture.status)}`}>
                {capture.status.charAt(0).toUpperCase() + capture.status.slice(1)}
              </span>
              {capture.status === 'active' && (
                <span className="ml-2 text-sm text-gray-500">{getTimeRemaining()}</span>
              )}
              {isScheduled() && (
                <span className="ml-2 text-sm text-gray-500">{getTimeUntilStart()}</span>
              )}
            </div>
          </div>
          
          <div className="flex space-x-3">
            <button
              type="button"
              onClick={handleRefresh}
              className="px-3 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
            >
              Refresh
            </button>
            
            {(capture.status === 'active' || capture.status === 'processing') && (
              <button
                type="button"
                onClick={toggleAutoRefresh}
                className={`px-3 py-2 border rounded-md text-sm font-medium ${
                  autoRefresh
                    ? 'border-primary text-primary bg-primary-50 hover:bg-primary-100'
                    : 'border-gray-300 text-gray-700 bg-white hover:bg-gray-50'
                }`}
              >
                {autoRefresh ? 'Auto-Refresh On' : 'Auto-Refresh Off'}
              </button>
            )}
            
            {capture.status === 'active' && (
              <button
                type="button"
                onClick={handleStopCapture}
                disabled={stopCaptureMutation.isPending}
                className="px-3 py-2 border border-red-300 rounded-md text-sm font-medium text-red-700 bg-white hover:bg-red-50 disabled:opacity-50"
              >
                {stopCaptureMutation.isPending ? 'Stopping...' : 'Stop Capture'}
              </button>
            )}
            
            {capture.status === 'completed' && (
              <Link href={`/clips/new?source_type=capture&source_id=${capture.id}`}>
                <span className="btn-primary rounded-md px-3 py-2 text-center cursor-pointer inline-block">
                  Create Clip
                </span>
              </Link>
            )}
          </div>
        </div>
        
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left column - Capture details */}
          <div className="lg:col-span-2">
            <div className="bg-white rounded-lg shadow overflow-hidden mb-6">
              <div className="px-6 py-4 border-b border-gray-200">
                <h2 className="text-lg font-medium text-gray-800">Capture Details</h2>
              </div>
              
              <div className="p-6">
                <dl className="grid grid-cols-1 md:grid-cols-2 gap-x-4 gap-y-6">
                  <div>
                    <dt className="text-sm font-medium text-gray-500">Status</dt>
                    <dd className="mt-1 text-sm text-gray-900">
                      <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${getStatusBadgeClass(capture.status)}`}>
                        {capture.status.charAt(0).toUpperCase() + capture.status.slice(1)}
                      </span>
                    </dd>
                  </div>
                  
                  <div>
                    <dt className="text-sm font-medium text-gray-500">Duration</dt>
                    <dd className="mt-1 text-sm text-gray-900">{getCaptureDuration()}</dd>
                  </div>
                  
                  <div>
                    <dt className="text-sm font-medium text-gray-500">Started</dt>
                    <dd className="mt-1 text-sm text-gray-900">{formatDate(capture.start_time)}</dd>
                  </div>
                  
                  <div>
                    <dt className="text-sm font-medium text-gray-500">Ended</dt>
                    <dd className="mt-1 text-sm text-gray-900">{formatDate(capture.end_time)}</dd>
                  </div>
                  
                  {(capture.scheduled_start || capture.scheduled_end) && (
                    <>
                      <div>
                        <dt className="text-sm font-medium text-gray-500">Scheduled Start</dt>
                        <dd className="mt-1 text-sm text-gray-900">{formatDate(capture.scheduled_start)}</dd>
                      </div>
                      
                      <div>
                        <dt className="text-sm font-medium text-gray-500">Scheduled End</dt>
                        <dd className="mt-1 text-sm text-gray-900">{formatDate(capture.scheduled_end)}</dd>
                      </div>
                    </>
                  )}
                  
                  <div>
                    <dt className="text-sm font-medium text-gray-500">File Size</dt>
                    <dd className="mt-1 text-sm text-gray-900">{formatFileSize(capture.file_size)}</dd>
                  </div>
                  
                  <div>
                    <dt className="text-sm font-medium text-gray-500">Created By</dt>
                    <dd className="mt-1 text-sm text-gray-900">{capture.created_by?.name || 'Unknown'}</dd>
                  </div>
                  
                  <div className="md:col-span-2">
                    <dt className="text-sm font-medium text-gray-500">Source URL</dt>
                    <dd className="mt-1 text-sm text-gray-900 break-all">
                      <a
                        href={capture.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-primary hover:text-primary-dark"
                      >
                        {capture.source_url}
                      </a>
                    </dd>
                  </div>
                  
                  {capture.description && (
                    <div className="md:col-span-2">
                      <dt className="text-sm font-medium text-gray-500">Description</dt>
                      <dd className="mt-1 text-sm text-gray-900 whitespace-pre-line">{capture.description}</dd>
                    </div>
                  )}
                </dl>
              </div>
            </div>
            
            {/* Video preview for completed captures */}
            {capture.status === 'completed' && (
              <div className="bg-white rounded-lg shadow overflow-hidden mb-6">
                <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
                  <h2 className="text-lg font-medium text-gray-800">Video Preview</h2>
                  <div className="flex space-x-2">
                    <Link href={`/capture/${capture.id}/speakers`}>
                      <span className="text-sm text-primary hover:text-primary-dark cursor-pointer">
                        Speaker Identification
                      </span>
                    </Link>
                    <span className="text-gray-300">|</span>
                    <Link href={`/capture/${capture.id}/transcription`}>
                      <span className="text-sm text-primary hover:text-primary-dark cursor-pointer">
                        Transcription
                      </span>
                    </Link>
                  </div>
                </div>
                
                <div className="aspect-w-16 aspect-h-9 bg-black">
                  <video
                    ref={videoRef}
                    key={`video-${capture.id}-${capture.updated_at}`}
                    src={getVideoSourceUrl(capture)}
                    controls
                    className="w-full h-full object-contain"
                    onError={handleVideoError}
                    playsInline
                    preload="auto"
                    crossOrigin="anonymous"
                  />
                </div>
                <div className="p-4 text-sm">
                  <p>Having trouble playing the video? Try the direct link:</p>
                  <a 
                    href={getVideoSourceUrl(capture)} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="text-blue-600 hover:text-blue-800 underline"
                  >
                    Open video in new tab
                  </a>
                  
                  {/* Debug info - helps diagnose video playback issues */}
                  <details className="mt-4 border p-2 rounded">
                    <summary className="font-medium cursor-pointer">Debug Info</summary>
                    <div className="mt-2 space-y-1 text-xs font-mono bg-gray-100 p-2 rounded overflow-auto max-h-48">
                      <p key="debug-capture-id">Capture ID: {capture.id}</p>
                      <p key="debug-status">Status: {capture.status}</p>
                      <p key="debug-source-url">Source URL: {capture.source_url}</p>
                      <p key="debug-file-path">File Path: {capture.file_path || 'Not available'}</p>
                      <p key="debug-is-parliament">Is Parliament TV: {isParliamentTVCapture(capture) ? 'Yes' : 'No'}</p>
                      <p key="debug-video-source">Video Source: {getVideoSourceUrl(capture)}</p>
                      <p key="debug-metadata">Metadata: {JSON.stringify(capture.metadata || {}, null, 2)}</p>
                    </div>
                  </details>
                </div>
              </div>
            )}
          </div>
          
          {/* Right column - Capture logs */}
          <div>
            <div className="bg-white rounded-lg shadow overflow-hidden">
              <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
                <h2 className="text-lg font-medium text-gray-800">Capture Logs</h2>
                {(capture.status === 'active' || capture.status === 'processing') && (
                  <span className="text-xs text-gray-500">
                    {autoRefresh ? 'Auto-refreshing' : 'Auto-refresh off'}
                  </span>
                )}
              </div>
              
              <div className="h-96 overflow-y-auto p-4 bg-gray-50 font-mono text-sm">
                {logsLoading ? (
                  <div className="text-center text-gray-500 py-4">Loading logs...</div>
                ) : !logsData || !logsData.logs || logsData.logs.length === 0 ? (
                  <div className="text-center text-gray-500 py-4">No logs available</div>
                ) : (
                  <div className="space-y-2">
                    {logsData.logs.map((log: CaptureLog) => (
                      <div key={log.id} className="pb-2 border-b border-gray-200 last:border-0">
                        <div className="flex items-center justify-between mb-1">
                          <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${getLogLevelBadgeClass(log.level)}`}>
                            {log.level.toUpperCase()}
                          </span>
                          <span className="text-xs text-gray-500">
                            {new Date(log.timestamp).toLocaleTimeString()}
                          </span>
                        </div>
                        <div className="text-gray-800 break-words">{log.message}</div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
              
              {/* Logs pagination */}
              {logsData && logsData.logs && logsData.logs.length > 0 && (
                <div className="px-6 py-3 border-t border-gray-200 flex justify-between items-center">
                  <button
                    type="button"
                    onClick={() => setLogsPage(Math.max(1, logsPage - 1))}
                    disabled={logsPage === 1}
                    className="text-sm text-gray-700 hover:text-gray-900 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Previous
                  </button>
                  <span className="text-sm text-gray-500">Page {logsPage} of {logsData.total_pages || 1}</span>
                  <button
                    type="button"
                    onClick={() => setLogsPage(logsPage + 1)}
                    disabled={!logsData.total_pages || logsPage >= logsData.total_pages || logsData.logs.length < logsPerPage}
                    className="text-sm text-gray-700 hover:text-gray-900 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Next
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </MainLayout>
  );
};

export default withAuth(CaptureDetailPage, [UserRole.ADMIN, UserRole.MP, UserRole.STAFF]);
