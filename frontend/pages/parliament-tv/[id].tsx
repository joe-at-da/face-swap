import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import axios from 'axios';
import { withAuth, useAuth } from '../../contexts/AuthContext';
import { UserRole } from '../../contexts/AuthContext';
import DarkLayout from '../../components/layout/DarkLayout';
import Link from 'next/link';
import UnifiedRecognitionPanel from '../../components/recognition/UnifiedRecognitionPanel';
import { toast } from 'react-toastify';
import { Button, Card, Badge } from '../../components/ui';

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
  facial_recognition_status?: string;
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
  const [showAudioPlayer, setShowAudioPlayer] = useState(false);
  const [syncPlayback, setSyncPlayback] = useState(false);
  const videoUrl = video ? `${API_BASE_URL}/parliament-tv/${video.id}/stream` : '';
  const audioUrl = video ? `${API_BASE_URL}/videos/static/audio/capture_${video.id.toString().padStart(4, '0')}.audio.mp3` : '';

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
  
  const getFacialRecognitionStatusColor = (status: string) => {
    switch (status) {
      case 'not_started':
        return 'bg-gray-100 text-gray-800';
      case 'scheduled':
        return 'bg-blue-100 text-blue-800';
      case 'processing':
        return 'bg-yellow-100 text-yellow-800';
      case 'completed':
        return 'bg-green-100 text-green-800';
      case 'failed':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  if (loading) {
    return (
      <DarkLayout>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="text-center py-8 text-white">Loading video details...</div>
        </div>
      </DarkLayout>
    );
  }

  if (error) {
    return (
      <DarkLayout>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="bg-gray-800 border border-red-600 text-red-400 px-4 py-3 rounded relative mb-4" role="alert">
            <strong className="font-bold">Error: </strong>
            <span className="block sm:inline">{error}</span>
          </div>
          <div className="mt-4">
            <Link href="/parliament-tv/videos">
              <span className="text-blue-400 hover:text-blue-300">Back to videos</span>
            </Link>
          </div>
        </div>
      </DarkLayout>
    );
  }

  if (!video) {
    return (
      <DarkLayout>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="bg-gray-800 border border-yellow-600 text-yellow-400 px-4 py-3 rounded relative mb-4" role="alert">
            <strong className="font-bold">Notice: </strong>
            <span className="block sm:inline">Video not found or has been deleted.</span>
          </div>
          <div className="mt-4">
            <Link href="/parliament-tv/videos">
              <span className="text-blue-400 hover:text-blue-300">Back to videos</span>
            </Link>
          </div>
        </div>
      </DarkLayout>
    );
  }

  return (
    <DarkLayout>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-6 flex justify-between items-center">
          <div>
            <Link href="/parliament-tv/videos">
              <span className="text-blue-400 hover:text-blue-300">← Back to videos</span>
            </Link>
            <h1 className="text-3xl font-bold text-white mt-2">{video.title}</h1>
          </div>
          <Button
            onClick={deleteVideo}
            disabled={deleteInProgress}
            variant="danger"
          >
            {deleteInProgress ? 'Deleting...' : 'Delete Video'}
          </Button>
        </div>

        <Card className="overflow-hidden">
          <div className="px-4 py-5 sm:px-6 bg-gray-800">
            <h3 className="text-lg leading-6 font-medium text-white">Video Details</h3>
          </div>
          <div className="border-t border-gray-700">
            <dl>
              <div className="bg-gray-800 px-4 py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
                <dt className="text-sm font-medium text-gray-400">Status</dt>
                <dd className="mt-1 text-sm text-gray-300 sm:mt-0 sm:col-span-2">
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
              <div className="bg-gray-700 px-4 py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
                <dt className="text-sm font-medium text-gray-400">Duration</dt>
                <dd className="mt-1 text-sm text-gray-300 sm:mt-0 sm:col-span-2">{formatDuration(video.duration)}</dd>
              </div>
              <div className="bg-gray-800 px-4 py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
                <dt className="text-sm font-medium text-gray-400">File Size</dt>
                <dd className="mt-1 text-sm text-gray-300 sm:mt-0 sm:col-span-2">{formatFileSize(video.file_size)}</dd>
              </div>
              <div className="bg-gray-700 px-4 py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
                <dt className="text-sm font-medium text-gray-400">Created By</dt>
                <dd className="mt-1 text-sm text-gray-300 sm:mt-0 sm:col-span-2">{video.created_by?.name || 'Unknown'}</dd>
              </div>
              <div className="bg-gray-800 px-4 py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
                <dt className="text-sm font-medium text-gray-400">Created At</dt>
                <dd className="mt-1 text-sm text-gray-300 sm:mt-0 sm:col-span-2">{new Date(video.created_at).toLocaleString()}</dd>
              </div>
              <div className="bg-gray-700 px-4 py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
                <dt className="text-sm font-medium text-gray-400">Source URL</dt>
                <dd className="mt-1 text-sm text-gray-300 sm:mt-0 sm:col-span-2 break-all">{video.url}</dd>
              </div>
              <div className="bg-gray-800 px-4 py-5 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6">
                <dt className="text-sm font-medium text-gray-400">Facial Recognition</dt>
                <dd className="mt-1 text-sm text-gray-300 sm:mt-0 sm:col-span-2">
                  <div className="flex items-center">
                    <span className="mr-2">{video.facial_recognition_enabled ? 'Enabled' : 'Disabled'}</span>
                    {video.facial_recognition_status && (
                      <span className={`px-2 py-1 text-xs rounded-full ${getFacialRecognitionStatusColor(video.facial_recognition_status)}`}>
                        {video.facial_recognition_status.replace('_', ' ')}
                      </span>
                    )}
                  </div>
                </dd>
              </div>
            </dl>
          </div>
        </Card>

        <Card className="overflow-hidden mt-6">
          <div className="px-4 py-5 sm:px-6 bg-gray-800">
            <h3 className="text-lg leading-6 font-medium text-white">Video Player</h3>
          </div>
          <div className="border-t border-gray-700 p-4">
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
            
            {/* Audio Player Section */}
            <div className="mt-6">
              <h4 className="text-lg font-medium text-white mb-2">Audio Track</h4>
              <div className="flex items-center mb-2">
                <Button
                  onClick={() => setShowAudioPlayer(!showAudioPlayer)}
                  variant="primary"
                  className="mr-2"
                >
                  {showAudioPlayer ? 'Hide Audio Player' : 'Show Audio Player'}
                </Button>
                
                <label className="inline-flex items-center cursor-pointer ml-2">
                  <input 
                    type="checkbox" 
                    className="sr-only peer"
                    checked={syncPlayback}
                    onChange={() => setSyncPlayback(!syncPlayback)}
                  />
                  <div className="relative w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-500"></div>
                  <span className="ml-3 text-sm font-medium text-gray-300">Synchronize audio and video playback</span>
                </label>
              </div>
              
              {showAudioPlayer && (
                <div className="mt-2">
                  <audio 
                    controls 
                    className="w-full" 
                    src={audioUrl}
                  >
                    Your browser does not support the audio element.
                  </audio>
                  <div className="mt-2 text-xs text-gray-400">
                    <p>Audio URL: {audioUrl}</p>
                  </div>
                </div>
              )}
            </div>
            
            <div className="mt-4 text-sm text-gray-400">
              <p>Note: If the video or audio doesn't play, it may be in a format not supported by your browser or the file may not be accessible.</p>
              <p>For best results, play both the video and audio simultaneously.</p>
            </div>
          </div>
        </Card>

        {/* Unified Recognition Panel */}
        <div className="mt-8">
          <UnifiedRecognitionPanel 
            captureId={video.id} 
            onProcessingComplete={() => {
              toast.success('Recognition processing completed');
              fetchVideo(); // Refresh video data
            }}
          />
        </div>

        <div className="mt-8 flex justify-between">
          <Link href="/parliament-tv/videos">
            <span className="text-blue-400 hover:text-blue-300">Back to videos</span>
          </Link>
          <Link href={`/capture/create-clip?source=${id}`}>
            <Button variant="primary">
              Create Clip from This Video
            </Button>
          </Link>
        </div>
      </div>
    </DarkLayout>
  );
};

export default withAuth(ParliamentTVVideoDetail, [UserRole.ADMIN, UserRole.MP, UserRole.STAFF]);
