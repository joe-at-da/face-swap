import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../../contexts/AuthContext';
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
  created_by: {
    id: number;
    name: string;
    email: string;
  };
}

const ParliamentTVVideoList: React.FC = () => {
  const { token } = useAuth();
  const [videos, setVideos] = useState<ParliamentTVVideo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [deleteInProgress, setDeleteInProgress] = useState<number | null>(null);

  useEffect(() => {
    fetchVideos();
  }, [token]);

  const fetchVideos = async () => {
    if (!token) return;

    setLoading(true);
    try {
      const response = await axios.get<ParliamentTVVideo[]>(`${API_BASE_URL}/parliament-tv`, {
        headers: {
          Authorization: `Bearer ${token}`
        }
      });
      
      setVideos(response.data);
    } catch (err) {
      console.error('Error fetching Parliament TV videos:', err);
      setError('Failed to load Parliament TV videos');
    } finally {
      setLoading(false);
    }
  };

  const deleteVideo = async (id: number) => {
    if (!confirm('Are you sure you want to delete this video? This action cannot be undone.')) {
      return;
    }

    setDeleteInProgress(id);
    try {
      await axios.delete(`${API_BASE_URL}/parliament-tv/${id}`, {
        headers: {
          Authorization: `Bearer ${token}`
        }
      });
      
      // Remove the deleted video from the list
      setVideos(videos.filter(video => video.id !== id));
    } catch (err) {
      console.error('Error deleting video:', err);
      alert('Failed to delete video. Please try again.');
    } finally {
      setDeleteInProgress(null);
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
    return <div className="text-center py-8">Loading Parliament TV videos...</div>;
  }

  if (error) {
    return (
      <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative mb-4" role="alert">
        <strong className="font-bold">Error: </strong>
        <span className="block sm:inline">{error}</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-gray-900">Parliament TV Videos</h2>
        <Link href="/capture">
          <a className="btn-primary px-4 py-2 rounded-md">Capture New Video</a>
        </Link>
      </div>
      
      {videos.length === 0 ? (
        <div className="text-center py-8 bg-gray-50 rounded-lg">
          <p className="text-gray-500">No Parliament TV videos found.</p>
          <p className="mt-2">
            <Link href="/capture">
              <a className="text-indigo-600 hover:text-indigo-800">Capture a new video</a>
            </Link>
          </p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Title
                </th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Duration
                </th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Size
                </th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Created
                </th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {videos.map((video) => (
                <tr key={video.id}>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm font-medium text-gray-900">{video.title}</div>
                    <div className="text-sm text-gray-500">ID: {video.id}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-900">{formatDuration(video.duration)}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-900">{formatFileSize(video.file_size)}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                      video.status === 'active' ? 'bg-green-100 text-green-800' :
                      video.status === 'completed' ? 'bg-blue-100 text-blue-800' :
                      video.status === 'failed' ? 'bg-red-100 text-red-800' :
                      'bg-gray-100 text-gray-800'
                    }`}>
                      {video.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {new Date(video.created_at).toLocaleString()}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                    <div className="flex space-x-2">
                      <Link href={`/parliament-tv/${video.id}`}>
                        <a className="text-indigo-600 hover:text-indigo-900">View</a>
                      </Link>
                      <button
                        onClick={() => deleteVideo(video.id)}
                        disabled={deleteInProgress === video.id}
                        className="text-red-600 hover:text-red-900 disabled:opacity-50"
                      >
                        {deleteInProgress === video.id ? 'Deleting...' : 'Delete'}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      
      <div className="mt-4 p-4 bg-yellow-50 border-l-4 border-yellow-400 rounded-md">
        <div className="flex">
          <div className="flex-shrink-0">
            <svg className="h-5 w-5 text-yellow-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
          </div>
          <div className="ml-3">
            <h3 className="text-sm font-medium text-yellow-800">Storage Management</h3>
            <div className="mt-2 text-sm text-yellow-700">
              <p>Videos are stored in the system's temporary directory. To free up space, delete videos you no longer need.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ParliamentTVVideoList;
