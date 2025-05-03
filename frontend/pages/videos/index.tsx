import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import axios from 'axios';
import Link from 'next/link';
import MainLayout from '../../components/layout/MainLayout';
import { withAuth, useAuth } from '../../contexts/AuthContext';
import { UserRole } from '../../contexts/AuthContext';

// API base URL
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api/v1';

interface VideoFile {
  path: string;
  relative_path: string;
  filename: string;
  size: number;
  modified_time: number;
  capture_id: number | null;
  title: string;
  status: string;
  duration: number | null;
  created_by: string;
  stream_url: string;
}

const VideoGalleryPage: React.FC = () => {
  const router = useRouter();
  const { token } = useAuth();
  const [videos, setVideos] = useState<VideoFile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedVideo, setSelectedVideo] = useState<VideoFile | null>(null);

  useEffect(() => {
    fetchVideos();
  }, [token]);

  const fetchVideos = async () => {
    if (!token) return;

    setLoading(true);
    try {
      const response = await axios.get<VideoFile[]>(`${API_BASE_URL}/videos`, {
        headers: {
          Authorization: `Bearer ${token}`
        }
      });
      
      setVideos(response.data);
    } catch (err) {
      console.error('Error fetching videos:', err);
      setError('Failed to load videos');
    } finally {
      setLoading(false);
    }
  };

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

  const formatDuration = (seconds: number | null) => {
    if (!seconds) return '--:--:--';
    
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    
    return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const formatDate = (timestamp: number) => {
    return new Date(timestamp * 1000).toLocaleString();
  };

  const handleVideoClick = (video: VideoFile) => {
    setSelectedVideo(video);
  };

  const closeVideoModal = () => {
    setSelectedVideo(null);
  };

  if (loading) {
    return (
      <MainLayout>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="text-center py-8">Loading videos...</div>
        </div>
      </MainLayout>
    );
  }

  if (error) {
    return (
      <MainLayout>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative mb-4" role="alert">
            <strong className="font-bold">Error: </strong>
            <span className="block sm:inline">{error}</span>
          </div>
        </div>
      </MainLayout>
    );
  }

  return (
    <MainLayout>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-2xl font-bold text-gray-900">Video Gallery</h1>
          <Link href="/capture/new">
            <a className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded">Capture New Video</a>
          </Link>
        </div>

        {videos.length === 0 ? (
          <div className="text-center py-8 bg-gray-50 rounded-lg">
            <p className="text-gray-500">No videos found.</p>
            <p className="mt-2">
              <Link href="/capture/new">
                <a className="text-blue-600 hover:text-blue-800">Capture a new video</a>
              </Link>
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {videos.map((video) => (
              <div 
                key={video.path} 
                className="bg-white rounded-lg shadow overflow-hidden hover:shadow-lg transition-shadow duration-300 cursor-pointer"
                onClick={() => handleVideoClick(video)}
              >
                <div className="aspect-w-16 aspect-h-9 bg-gray-200">
                  <div className="flex items-center justify-center">
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-16 w-16 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                </div>
                <div className="p-4">
                  <h3 className="text-lg font-medium text-gray-900 truncate" title={video.title}>{video.title}</h3>
                  <div className="mt-2 grid grid-cols-2 gap-2 text-sm text-gray-500">
                    <div>
                      <span className="font-medium">Duration:</span> {formatDuration(video.duration)}
                    </div>
                    <div>
                      <span className="font-medium">Size:</span> {formatFileSize(video.size)}
                    </div>
                    <div>
                      <span className="font-medium">Status:</span> {video.status}
                    </div>
                    <div>
                      <span className="font-medium">Created by:</span> {video.created_by}
                    </div>
                  </div>
                  {video.capture_id && (
                    <div className="mt-3">
                      <Link href={`/capture/${video.capture_id}`}>
                        <a className="text-blue-600 hover:text-blue-800 text-sm">View Capture Details</a>
                      </Link>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Video Modal */}
        {selectedVideo && (
          <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-lg max-w-4xl w-full max-h-screen overflow-auto">
              <div className="p-4 border-b flex justify-between items-center">
                <h3 className="text-lg font-medium">{selectedVideo.title}</h3>
                <button 
                  onClick={closeVideoModal}
                  className="text-gray-500 hover:text-gray-700"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
              <div className="aspect-w-16 aspect-h-9">
                <video 
                  src={`${API_BASE_URL}${selectedVideo.stream_url}`} 
                  controls 
                  className="w-full h-full object-contain"
                  autoPlay
                />
              </div>
              <div className="p-4 grid grid-cols-2 gap-4 text-sm">
                <div>
                  <p><span className="font-medium">Filename:</span> {selectedVideo.filename}</p>
                  <p><span className="font-medium">Path:</span> {selectedVideo.relative_path}</p>
                  <p><span className="font-medium">Size:</span> {formatFileSize(selectedVideo.size)}</p>
                  <p><span className="font-medium">Duration:</span> {formatDuration(selectedVideo.duration)}</p>
                </div>
                <div>
                  <p><span className="font-medium">Status:</span> {selectedVideo.status}</p>
                  <p><span className="font-medium">Created by:</span> {selectedVideo.created_by}</p>
                  <p><span className="font-medium">Modified:</span> {formatDate(selectedVideo.modified_time)}</p>
                  {selectedVideo.capture_id && (
                    <p>
                      <span className="font-medium">Capture ID:</span>{' '}
                      <Link href={`/capture/${selectedVideo.capture_id}`}>
                        <a className="text-blue-600 hover:text-blue-800">{selectedVideo.capture_id}</a>
                      </Link>
                    </p>
                  )}
                </div>
              </div>
              <div className="p-4 border-t flex justify-end space-x-2">
                <a 
                  href={`${API_BASE_URL}${selectedVideo.stream_url}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded"
                >
                  Download Video
                </a>
                <button 
                  onClick={closeVideoModal}
                  className="bg-gray-200 hover:bg-gray-300 text-gray-800 px-4 py-2 rounded"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </MainLayout>
  );
};

export default withAuth(VideoGalleryPage, [UserRole.ADMIN, UserRole.MP, UserRole.STAFF]);
