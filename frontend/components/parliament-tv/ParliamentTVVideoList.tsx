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

  // Mock data for Parliament TV videos
  const mockVideos: ParliamentTVVideo[] = [
    {
      id: 1,
      title: 'Prime Minister Questions - May 22, 2025',
      status: 'completed',
      file_path: '/videos/pmq-20250522.mp4',
      file_size: 1258291200, // 1.2 GB
      created_at: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(), // Yesterday
      updated_at: new Date(Date.now() - 23 * 60 * 60 * 1000).toISOString(),
      duration: 3600, // 1 hour
      created_by: {
        id: 1,
        name: 'Admin User',
        email: 'admin@example.com',
      },
    },
    {
      id: 2,
      title: 'Budget Debate - May 20, 2025',
      status: 'active',
      file_path: '/videos/budget-20250520.mp4',
      file_size: 2516582400, // 2.4 GB
      created_at: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString(), // 3 days ago
      updated_at: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString(),
      duration: 7200, // 2 hours
      created_by: {
        id: 2,
        name: 'Staff User',
        email: 'staff@example.com',
      },
    },
    {
      id: 3,
      title: 'Foreign Affairs Committee - May 18, 2025',
      status: 'completed',
      file_path: '/videos/foreign-affairs-20250518.mp4',
      file_size: 1677721600, // 1.6 GB
      created_at: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000).toISOString(), // 5 days ago
      updated_at: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000).toISOString(),
      duration: 5400, // 1.5 hours
      created_by: {
        id: 3,
        name: 'MP User',
        email: 'mp@example.com',
      },
    },
  ];

  const fetchVideos = async () => {
    if (!token) return;

    setLoading(true);
    try {
      // Try to fetch from API first
      const response = await axios.get<ParliamentTVVideo[]>(`${API_BASE_URL}/parliament-tv`, {
        headers: {
          Authorization: `Bearer ${token}`
        }
      });
      
      // Check if response.data is an array
      if (Array.isArray(response.data)) {
        setVideos(response.data);
      } else {
        console.warn('API returned non-array data, using mock data instead');
        setVideos(mockVideos);
      }
    } catch (err) {
      console.error('Error fetching Parliament TV videos:', err);
      // Use mock data on error
      setVideos(mockVideos);
      setError('Using demo data - API endpoint not available');
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
    return <div className="text-center py-8 text-white">Loading Parliament TV videos...</div>;
  }

  if (error) {
    return (
      <div className="bg-gray-800 border border-red-600 text-red-400 px-4 py-3 rounded relative mb-4" role="alert">
        <strong className="font-bold">Note: </strong>
        <span className="block sm:inline">{error}</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-white">Parliament TV Videos</h2>
        <Link href="/capture">
          <span className="btn-primary px-4 py-2 rounded-md cursor-pointer inline-block">Capture New Video</span>
        </Link>
      </div>
      
      {videos.length === 0 ? (
        <div className="text-center py-8 bg-gray-800 rounded-lg">
          <p className="text-gray-300">No Parliament TV videos found.</p>
          <p className="mt-2">
            <Link href="/capture">
              <span className="text-blue-400 hover:text-blue-300 cursor-pointer">Capture a new video</span>
            </Link>
          </p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-700">
            <thead className="bg-gray-900">
              <tr>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                  Title
                </th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                  Duration
                </th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                  Size
                </th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                  Status
                </th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                  Created
                </th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-gray-800 divide-y divide-gray-700">
              {videos.map((video) => (
                <tr key={video.id} className="hover:bg-gray-700">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm font-medium text-white">{video.title}</div>
                    <div className="text-sm text-gray-300">ID: {video.id}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-white">{formatDuration(video.duration)}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-white">{formatFileSize(video.file_size)}</div>
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
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">
                    {new Date(video.created_at).toLocaleString()}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                    <div className="flex space-x-2">
                      <Link href={`/parliament-tv/${video.id}`}>
                        <span className="text-blue-400 hover:text-blue-300 cursor-pointer">View</span>
                      </Link>
                      <button
                        onClick={() => deleteVideo(video.id)}
                        disabled={deleteInProgress === video.id}
                        className="text-red-400 hover:text-red-300 disabled:opacity-50"
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
      
      <div className="mt-4 p-4 bg-gray-700 border-l-4 border-yellow-400 rounded-md">
        <div className="flex">
          <div className="flex-shrink-0">
            <svg className="h-5 w-5 text-yellow-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
          </div>
          <div className="ml-3">
            <h3 className="text-sm font-medium text-yellow-300">Storage Management</h3>
            <div className="mt-2 text-sm text-gray-300">
              <p>Videos are stored in the system's temporary directory. To free up space, delete videos you no longer need.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ParliamentTVVideoList;
