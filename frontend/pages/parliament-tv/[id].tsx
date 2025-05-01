import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import axios from 'axios';
import { withAuth, useAuth } from '../../contexts/AuthContext';
import { UserRole } from '../../contexts/AuthContext';
import MainLayout from '../../components/layout/MainLayout';
import Link from 'next/link';

// API base URL
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api/v1';

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
  created_by: {
    id: number;
    name: string;
    email: string;
  };
}

const ParliamentTVVideoDetail: React.FC = () => {
  const router = useRouter();
  const { token } = useAuth();
  const { id } = router.query;
  
  const [video, setVideo] = useState<ParliamentTVVideo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [deleteInProgress, setDeleteInProgress] = useState(false);
  const videoUrl = video ? `${API_BASE_URL}/parliament-tv/${video.id}/stream` : '';

  useEffect(() => {
    if (id && token) {
      fetchVideo();
    }
  }, [id, token]);

  const fetchVideo = async () => {
    setLoading(true);
    try {
      const response = await axios.get<ParliamentTVVideo>(`${API_BASE_URL}/parliament-tv/${id}`, {
        headers: {
          Authorization: `Bearer ${token}`
        }
      });
      
      setVideo(response.data);
    } catch (err) {
      console.error('Error fetching video details:', err);
      setError('Failed to load video details');
    } finally {
      setLoading(false);
    }
  };

  const deleteVideo = async () => {
    if (!confirm('Are you sure you want to delete this video? This action cannot be undone.')) {
      return;
    }

    setDeleteInProgress(true);
    try {
      await axios.delete(`${API_BASE_URL}/parliament-tv/${id}`, {
        headers: {
          Authorization: `Bearer ${token}`
        }
      });
      
      // Redirect back to videos list
      router.push('/parliament-tv/videos');
    } catch (err) {
      console.error('Error deleting video:', err);
      alert('Failed to delete video. Please try again.');
      setDeleteInProgress(false);
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

  const formatDuration = (seconds: number) => {
    if (!seconds) return '--:--:--';
    
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    
    return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  if (loading) {
    return (
      <MainLayout>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="text-center py-8">Loading video details...</div>
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
            <div className="mt-4">
              <Link href="/parliament-tv/videos">
                <a className="text-red-700 underline">Back to videos</a>
              </Link>
            </div>
          </div>
        </div>
      </MainLayout>
    );
  }

  if (!video) {
    return (
      <MainLayout>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="text-center py-8">Video not found</div>
          <div className="mt-4 text-center">
            <Link href="/parliament-tv/videos">
              <a className="text-indigo-600 underline">Back to videos</a>
            </Link>
          </div>
        </div>
      </MainLayout>
    );
  }

  // Video URL is defined at the top of the component

  return (
    <MainLayout>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-6 flex justify-between items-center">
          <div>
            <Link href="/parliament-tv/videos">
              <a className="text-indigo-600 hover:text-indigo-900">← Back to videos</a>
            </Link>
            <h1 className="text-3xl font-bold text-gray-900 mt-2">{video.title}</h1>
          </div>
          <button
            onClick={deleteVideo}
            disabled={deleteInProgress}
            className="bg-red-600 hover:bg-red-700 text-white font-bold py-2 px-4 rounded disabled:opacity-50"
          >
            {deleteInProgress ? 'Deleting...' : 'Delete Video'}
          </button>
        </div>

        <div className="bg-white shadow overflow-hidden sm:rounded-lg mb-6">
          <div className="px-4 py-5 sm:px-6 bg-gray-50">
            <h3 className="text-lg leading-6 font-medium text-gray-900">Video Details</h3>
          </div>
          <div className="border-t border-gray-200">
            <dl>
              <div className="bg-gray-50 px-4 py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
                <dt className="text-sm font-medium text-gray-500">Status</dt>
                <dd className="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2">
                  <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                    video.status === 'active' ? 'bg-green-100 text-green-800' :
                    video.status === 'completed' ? 'bg-blue-100 text-blue-800' :
                    video.status === 'failed' ? 'bg-red-100 text-red-800' :
                    'bg-gray-100 text-gray-800'
                  }`}>
                    {video.status}
                  </span>
                </dd>
              </div>
              <div className="bg-white px-4 py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
                <dt className="text-sm font-medium text-gray-500">Duration</dt>
                <dd className="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2">{formatDuration(video.duration)}</dd>
              </div>
              <div className="bg-gray-50 px-4 py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
                <dt className="text-sm font-medium text-gray-500">File Size</dt>
                <dd className="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2">{formatFileSize(video.file_size)}</dd>
              </div>
              <div className="bg-white px-4 py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
                <dt className="text-sm font-medium text-gray-500">Created By</dt>
                <dd className="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2">{video.created_by?.name || 'Unknown'}</dd>
              </div>
              <div className="bg-gray-50 px-4 py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
                <dt className="text-sm font-medium text-gray-500">Created At</dt>
                <dd className="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2">{new Date(video.created_at).toLocaleString()}</dd>
              </div>
              <div className="bg-white px-4 py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
                <dt className="text-sm font-medium text-gray-500">Source URL</dt>
                <dd className="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2 break-all">{video.url}</dd>
              </div>
              <div className="bg-gray-50 px-4 py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
                <dt className="text-sm font-medium text-gray-500">Facial Recognition</dt>
                <dd className="mt-1 text-sm text-gray-900 sm:mt-0 sm:col-span-2">
                  {video.facial_recognition_enabled ? 'Enabled' : 'Disabled'}
                </dd>
              </div>
            </dl>
          </div>
        </div>

        <div className="bg-white shadow overflow-hidden sm:rounded-lg">
          <div className="px-4 py-5 sm:px-6 bg-gray-50">
            <h3 className="text-lg leading-6 font-medium text-gray-900">Video Player</h3>
          </div>
          <div className="border-t border-gray-200 p-4">
            <div className="aspect-w-16 aspect-h-9">
              <video 
                controls 
                className="w-full h-full object-cover rounded-lg"
                src={videoUrl}
                poster="/images/video-placeholder.jpg"
              >
                Your browser does not support the video tag.
              </video>
            </div>
            <div className="mt-4 text-sm text-gray-500">
              <p>Note: If the video doesn't play, it may be in a format not supported by your browser or the file may not be accessible.</p>
            </div>
          </div>
        </div>

        <div className="mt-8 flex justify-between">
          <Link href="/parliament-tv/videos">
            <a className="text-indigo-600 hover:text-indigo-900">Back to videos</a>
          </Link>
          <Link href={`/capture/create-clip?source=${id}`}>
            <a className="bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-2 px-4 rounded">
              Create Clip from This Video
            </a>
          </Link>
        </div>
      </div>
    </MainLayout>
  );
};

export default withAuth(ParliamentTVVideoDetail, [UserRole.ADMIN, UserRole.MP, UserRole.STAFF]);
