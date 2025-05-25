import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import axios from 'axios';
import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import DarkLayout from '../../components/layout/DarkLayout';
import { withAuth, useAuth } from '../../contexts/AuthContext';
import { UserRole } from '../../contexts/AuthContext';
import { toast } from 'react-toastify';
import { api } from '../../utils/api';
import { Button, Card, Badge, Input, Select } from '../../components/ui';

// API base URL
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api/v1';

// File types - use string literals instead of enum for better type compatibility
type FileTypeValue = 'video' | 'audio' | 'transcription' | 'recognition' | 'clip';

// Constants for file types
const FILE_TYPES = {
  VIDEO: 'video' as FileTypeValue,
  AUDIO: 'audio' as FileTypeValue,
  TRANSCRIPTION: 'transcription' as FileTypeValue,
  RECOGNITION: 'recognition' as FileTypeValue,
  CLIP: 'clip' as FileTypeValue
};

// File interface
interface FileItem {
  id: string;
  type: FileTypeValue;
  path: string;
  filename: string;
  size: number;
  capture_id?: string;
  title: string;
  status: string;
  created_at: string;
  description?: string;
  details?: any; // Additional details specific to file type
}

const FileGalleryPage = () => {
  const router = useRouter();
  const { token, user } = useAuth();
  const [files, setFiles] = useState<FileItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedFile, setSelectedFile] = useState<FileItem | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedType, setSelectedType] = useState<string>('all');
  const [selectedStatus, setSelectedStatus] = useState<string>('all');
  
  // Check for type parameter in URL and set filter accordingly
  useEffect(() => {
    const { type } = router.query;
    if (type && typeof type === 'string') {
      if (type === 'clip') {
        setSelectedType(FILE_TYPES.CLIP);
      } else if (type === 'video') {
        setSelectedType(FILE_TYPES.VIDEO);
      } else if (type === 'audio') {
        setSelectedType(FILE_TYPES.AUDIO);
      }
    }
  }, [router.query]);
  
  // Fetch videos
  const { data: videos, isLoading: isLoadingVideos } = useQuery({
    queryKey: ['videos'],
    queryFn: async () => {
      if (!token) return [];
      const response = await axios.get(`${API_BASE_URL}/videos`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      return response.data;
    },
    enabled: !!token
  });
  
  // Fetch clips
  const { data: clips, isLoading: isLoadingClips } = useQuery({
    queryKey: ['clips'],
    queryFn: async () => {
      if (!token) return { items: [] };
      return await api.get('/clips', { size: 100 });
    },
    enabled: !!token
  });
  
  // Fetch transcriptions
  const { data: transcriptions, isLoading: isLoadingTranscriptions } = useQuery({
    queryKey: ['transcriptions'],
    queryFn: async () => {
      const response = await api.get('/transcription/list/parliament-tv');
      return response.transcriptions || [];
    },
    enabled: !!token
  });
  
  // Fetch recognitions
  const { data: recognitions, isLoading: isLoadingRecognitions } = useQuery({
    queryKey: ['recognitions'],
    queryFn: async () => {
      const response = await api.get('/recognition/list/parliament-tv');
      return response.recognitions || [];
    },
    enabled: !!token
  });
  
  // Combine all files into a single array
  useEffect(() => {
    if (!videos && !transcriptions && !recognitions && !clips) return;
    
    const allFiles: FileItem[] = [];
    
    // Add videos
    if (videos && Array.isArray(videos)) {
      videos.forEach((video: any) => {
        allFiles.push({
          id: `video-${video.path}`,
          type: FILE_TYPES.VIDEO,
          path: video.path,
          filename: video.filename,
          size: video.size,
          capture_id: video.capture_id,
          title: video.title || video.filename,
          status: video.status || 'READY',
          created_at: video.created_at || new Date().toISOString(),
          description: video.description || '',
          details: {
            duration: video.duration,
            description: video.description,
            has_audio: video.has_audio,
            has_transcription: video.has_transcription,
            has_recognition: video.has_recognition
          }
        });
        
        // Check if there's an associated audio file
        if (video.filename.endsWith('.mp4')) {
          const audioFilename = video.filename.replace('.mp4', '.audio.mp3');
          allFiles.push({
            id: `audio-${video.path.replace('.mp4', '.audio.mp3')}`,
            type: FILE_TYPES.AUDIO,
            path: video.path.replace('.mp4', '.audio.mp3'),
            filename: audioFilename,
            size: 0, // Size unknown
            capture_id: video.capture_id,
            title: `Audio: ${video.title || video.filename}`,
            status: video.status || 'READY',
            created_at: video.created_at || new Date().toISOString(),
            description: `Audio track for ${video.title || video.filename}`,
            details: {
              related_video: video.path,
              duration: video.duration
            }
          });
        }
      });
    }
    
    // Add clips
    if (clips && clips.items) {
      clips.items.forEach((clip: any) => {
        allFiles.push({
          id: `clip-${clip.id}`,
          type: FILE_TYPES.CLIP,
          path: clip.file_path || '',
          filename: clip.file_path ? clip.file_path.split('/').pop() : `clip_${clip.id}.mp4`,
          size: clip.size || 0,
          created_at: clip.created_at || new Date().toISOString(),
          status: clip.status || 'READY',
          title: clip.title || `Clip ${clip.id}`,
          description: clip.description || '',
          capture_id: clip.capture_id || '',
          details: clip
        });
      });
    }
    
    // Add transcriptions
    if (transcriptions) {
      transcriptions.forEach((transcription: any) => {
        allFiles.push({
          id: `transcription-${transcription.id}`,
          type: FILE_TYPES.TRANSCRIPTION,
          path: `/transcription/${transcription.id}`,
          filename: `transcription_${transcription.capture_id}.json`,
          size: 0, // Size unknown
          created_at: transcription.created_at || new Date().toISOString(),
          status: transcription.status,
          title: `Transcription: Capture ${transcription.capture_id}`,
          description: '',
          capture_id: transcription.capture_id,
          details: {
            language: transcription.language,
            text_preview: transcription.text?.substring(0, 100) + '...',
            error_message: transcription.error_message
          }
        });
      });
    }
    
    // Add recognitions
    if (recognitions) {
      recognitions.forEach((recognition: any) => {
        allFiles.push({
          id: `recognition-${recognition.id}`,
          type: FILE_TYPES.RECOGNITION,
          path: `/recognition/${recognition.id}`,
          filename: `recognition_${recognition.capture_id}.json`,
          size: 0, // Size unknown
          created_at: recognition.created_at || new Date().toISOString(),
          status: recognition.status,
          title: `Recognition: ${recognition.type} (Capture ${recognition.capture_id})`,
          description: '',
          capture_id: recognition.capture_id,
          details: {
            type: recognition.type,
            confidence: recognition.confidence,
            error_message: recognition.error_message
          }
        });
      });
    }
    
    // Sort by created time (newest first)
    allFiles.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
    
    setFiles(allFiles);
    setLoading(false);
  }, [videos, transcriptions, recognitions, clips]);
  
  // Filter files based on search query and selected type
  const filteredFiles = files.filter(file => {
    // Match search query
    const matchesSearch = searchQuery === '' || 
      (file.filename && file.filename.toLowerCase().includes(searchQuery.toLowerCase())) || 
      (file.title && file.title.toLowerCase().includes(searchQuery.toLowerCase())) || 
      (file.details?.description && file.details.description.toLowerCase().includes(searchQuery.toLowerCase()));
    
    // Match file type
    const matchesType = selectedType === 'all' ? true : file.type === selectedType;
    
    // Match status
    const matchesStatus = selectedStatus === 'all' ? true : file.status === selectedStatus;
    
    return matchesSearch && matchesType && matchesStatus;
  });
  
  // Utility functions
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
  
  const formatDate = (timestamp: string) => {
    return new Date(timestamp).toLocaleString();
  };
  
  const getFileTypeIcon = (type: FileTypeValue) => {
    switch (type) {
      case FILE_TYPES.VIDEO:
        return (
          <svg className="w-8 h-8 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"></path>
          </svg>
        );
      case FILE_TYPES.AUDIO:
        return (
          <svg className="w-8 h-8 text-purple-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3"></path>
          </svg>
        );
      case FILE_TYPES.TRANSCRIPTION:
        return (
          <svg className="w-8 h-8 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
          </svg>
        );
      case FILE_TYPES.RECOGNITION:
        return (
          <svg className="w-8 h-8 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z"></path>
          </svg>
        );
      case FILE_TYPES.CLIP:
        return (
          <svg className="w-8 h-8 text-orange-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 4v1a2 2 0 00-2 2h2.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V18a2 2 0 01-2 2h-2.586a1 1 0 01-.707-.293l-5.414-5.414a1 1 0 01-.293-.707V6H2a2 2 0 00-2 2v12a2 2 0 002 2h12a2 2 0 002-2V6"></path>
          </svg>
        );
    }
  };
  
  const getStatusBadgeColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'completed':
      case 'ready':
        return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300';
      case 'processing':
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300';
      case 'failed':
        return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300';
      case 'pending':
        return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300';
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300';
    }
  };
  
  // Close file modal
  const closeFileModal = () => {
    setSelectedFile(null);
  };
  
  // Handle file click
  const handleFileClick = (file: FileItem) => {
    if (file.type === FILE_TYPES.VIDEO || file.type === FILE_TYPES.AUDIO || file.type === FILE_TYPES.CLIP) {
      setSelectedFile(file);
    } else {
      viewFileDetails(file);
    }
  };
  // Navigate to appropriate view page
  const viewFileDetails = (file: FileItem) => {
    // Navigate to appropriate view page
    if (file.type === FILE_TYPES.VIDEO) {
      if (file.capture_id) {
        router.push(`/files/view/${file.capture_id}?type=video`);
      } else {
        toast.error('Unable to view this video. Missing capture ID.');
      }
    } else if (file.type === FILE_TYPES.CLIP) {
      // Extract the clip ID from the file ID (format: 'clip-123')
      const clipId = file.id.split('-')[1];
      if (clipId) {
        router.push(`/files/view/${clipId}?type=clip`);
      } else {
        toast.error('Unable to view this clip. Invalid clip ID.');
      }
    } else if (file.type === FILE_TYPES.AUDIO) {
      // For audio files, open the modal
      setSelectedFile(file);
    } else if (file.type === FILE_TYPES.TRANSCRIPTION) {
      if (file.capture_id) {
        router.push(`/files/view/${file.capture_id}?type=video&tab=transcription`);
      } else {
        toast.error('Unable to view this transcription. Missing capture ID.');
      }
    } else if (file.type === FILE_TYPES.RECOGNITION) {
      if (file.capture_id) {
        router.push(`/files/view/${file.capture_id}?type=video&tab=recognition`);
      } else {
        toast.error('Unable to view this recognition data. Missing capture ID.');
      }
    }
  };
  
  return (
    <DarkLayout>
      <div className="container mx-auto px-4 py-8">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-2xl font-bold text-white">Media Library</h1>
          <div className="flex space-x-4">
            <Link href="/capture/new">
              <Button variant="secondary">Capture New Video</Button>
            </Link>
            <Link href="/capture/create-clip">
              <Button variant="primary">Create New Clip</Button>
            </Link>
          </div>
        </div>
        
        {/* Search and filters */}
        <div className="mb-6 bg-white dark:bg-gray-800 p-4 rounded-lg shadow">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex-grow">
              <input
                type="text"
                placeholder="Search files..."
                className="w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>
            <div className="flex gap-2">
              <select
                id="typeFilter"
                value={selectedType}
                onChange={(e) => setSelectedType(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="all">All Types</option>
                <option value={FILE_TYPES.VIDEO}>Videos</option>
                <option value={FILE_TYPES.CLIP}>Clips</option>
                <option value={FILE_TYPES.AUDIO}>Audio</option>
                <option value={FILE_TYPES.TRANSCRIPTION}>Transcriptions</option>
                <option value={FILE_TYPES.RECOGNITION}>Recognition Data</option>
              </select>
              <select
                id="statusFilter"
                value={selectedStatus}
                onChange={(e) => setSelectedStatus(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="all">All Statuses</option>
                <option value="READY">Ready</option>
                <option value="PROCESSING">Processing</option>
                <option value="ERROR">Error</option>
              </select>
            </div>
          </div>
        </div>
        
        {/* Loading state */}
        {loading && (
          <div className="flex justify-center items-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
          </div>
        )}
        
        {/* Error state */}
        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
            <p>{error}</p>
          </div>
        )}
        
        {/* File grid */}
        {!loading && !error && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {filteredFiles.map((file) => (
              <div
                key={file.id}
                className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden cursor-pointer transform transition hover:scale-105"
                onClick={() => viewFileDetails(file)}
              >
                <div className="p-4">
                  <div className="flex items-center mb-3">
                    {getFileTypeIcon(file.type)}
                    <span className={`ml-2 px-2 py-1 text-xs rounded-full ${getStatusBadgeColor(file.status)}`}>
                      {file.status}
                    </span>
                  </div>
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white truncate" title={file.title}>
                    {file.title}
                  </h3>
                  <p className="text-sm text-gray-500 dark:text-gray-400 truncate" title={file.filename}>
                    {file.filename}
                  </p>
                  <div className="mt-2 flex justify-between text-xs text-gray-500 dark:text-gray-400">
                    <span>{file.type}</span>
                    <span>{file.size ? formatFileSize(file.size) : 'N/A'}</span>
                  </div>
                  <div className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                    {formatDate(file.created_at)}
                  </div>
                  
                  {/* Additional details based on file type */}
                  {file.type === FILE_TYPES.TRANSCRIPTION && file.details?.text_preview && (
                    <div className="mt-2 text-xs text-gray-600 dark:text-gray-300 line-clamp-2">
                      {file.details.text_preview}
                    </div>
                  )}
                  
                  {file.type === FILE_TYPES.RECOGNITION && file.details?.type && (
                    <div className="mt-2 text-xs text-gray-600 dark:text-gray-300">
                      Type: {file.details.type}
                      {file.details.confidence !== undefined && (
                        <span className="ml-2">
                          ({Math.round(file.details.confidence * 100)}% confidence)
                        </span>
                      )}
                    </div>
                  )}
                  
                  {/* Error messages */}
                  {file.details?.error_message && (
                    <div className="mt-2 text-xs text-red-500 line-clamp-1" title={file.details.error_message}>
                      Error: {file.details.error_message}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
        
        {/* Empty state */}
        {!loading && !error && filteredFiles.length === 0 && (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-8 text-center">
            <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
            </svg>
            <h3 className="mt-2 text-lg font-medium text-gray-900 dark:text-white">No files found</h3>
            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
              {searchQuery || selectedType !== 'all' || selectedStatus !== 'all'
                ? 'Try adjusting your search filters'
                : 'Start by capturing a new video or uploading files'}
            </p>
          </div>
        )}
        
        {/* File modal for video/audio playback */}
        {selectedFile && (selectedFile.type === FILE_TYPES.VIDEO || selectedFile.type === FILE_TYPES.AUDIO || selectedFile.type === FILE_TYPES.CLIP) && (
          <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50">
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg w-full max-w-4xl max-h-[90vh] overflow-auto">
              <div className="p-4 border-b">
                <h2 className="text-xl font-semibold text-gray-900 dark:text-white">{selectedFile?.title}</h2>
                <p className="text-sm text-gray-500 dark:text-gray-400">{selectedFile?.filename}</p>
              </div>
              
              <div className="p-4">
                {/* Video player based on file type */}
                {selectedFile && selectedFile.type === FILE_TYPES.VIDEO && (
                  <video 
                    src={`${API_BASE_URL}/videos/stream-with-token/${selectedFile.filename}?token=${token}`}
                    controls
                    className="w-full"
                    autoPlay
                  />
                )}
                
                {selectedFile && selectedFile.type === FILE_TYPES.CLIP && (
                  <video 
                    src={selectedFile.details?.stream_url || ''}
                    controls
                    className="w-full"
                    autoPlay
                    poster={selectedFile.details?.thumbnail_url || ''}
                  />
                )}
                
                {selectedFile && selectedFile.type === FILE_TYPES.AUDIO && (
                  <audio 
                    src={`${API_BASE_URL}/videos/stream-audio-with-token/${selectedFile.details?.related_video || ''}?token=${token}`}
                    controls
                    className="w-full"
                    autoPlay
                  />
                )}
              </div>
              
              <div className="p-4 border-t flex justify-end">
                <button
                  onClick={closeFileModal}
                  className="px-4 py-2 bg-gray-200 text-gray-800 rounded hover:bg-gray-300 dark:bg-gray-700 dark:text-white dark:hover:bg-gray-600"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </DarkLayout>
  );
};

export default withAuth(FileGalleryPage, [UserRole.ADMIN, UserRole.MP, UserRole.STAFF]);
