import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import axios from 'axios';
import Link from 'next/link';
import MainLayout from '../../components/layout/MainLayout';
import { withAuth, useAuth } from '../../contexts/AuthContext';
import { UserRole } from '../../contexts/AuthContext';
import { toast } from 'react-toastify';

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
  const { token, user } = useAuth();
  const [videos, setVideos] = useState<VideoFile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedVideo, setSelectedVideo] = useState<VideoFile | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [showDeleteAllConfirm, setShowDeleteAllConfirm] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [videoToDelete, setVideoToDelete] = useState<VideoFile | null>(null);
  
  // State variables for audio/video combination
  const [showCombineModal, setShowCombineModal] = useState(false);
  const [selectedAudioFile, setSelectedAudioFile] = useState<string>('');
  const [selectedVideoFile, setSelectedVideoFile] = useState<string>('');
  const [isCombining, setIsCombining] = useState(false);
  const [combinedVideoFilename, setCombinedVideoFilename] = useState<string | null>(null);

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

  const handleDeleteClick = (e: React.MouseEvent, video: VideoFile) => {
    e.stopPropagation(); // Prevent video modal from opening
    setVideoToDelete(video);
    setShowDeleteConfirm(true);
  };

  const handleDeleteAllClick = () => {
    setShowDeleteAllConfirm(true);
  };

  const closeDeleteConfirm = () => {
    setShowDeleteConfirm(false);
    setVideoToDelete(null);
  };

  const closeDeleteAllConfirm = () => {
    setShowDeleteAllConfirm(false);
  };

  const deleteVideo = async (video: VideoFile) => {
    if (!token) return;
    
    setIsDeleting(true);
    try {
      await axios.delete(`${API_BASE_URL}/videos/delete/${encodeURIComponent(video.filename)}`, {
        headers: {
          Authorization: `Bearer ${token}`
        }
      });
      
      // Remove the video from the list
      setVideos(videos.filter(v => v.filename !== video.filename));
      toast.success(`Video ${video.filename} deleted successfully`);
      
      // Close the confirmation dialog
      closeDeleteConfirm();
      
      // If the deleted video is currently selected, close the modal
      if (selectedVideo && selectedVideo.filename === video.filename) {
        closeVideoModal();
      }
    } catch (err) {
      console.error('Error deleting video:', err);
      toast.error('Failed to delete video');
    } finally {
      setIsDeleting(false);
    }
  };

  const deleteAllVideos = async () => {
    if (!token) return;
    
    setIsDeleting(true);
    try {
      await axios.delete(`${API_BASE_URL}/videos/delete-all`, {
        headers: {
          Authorization: `Bearer ${token}`
        }
      });
      
      // Clear the videos list
      setVideos([]);
      toast.success('All videos deleted successfully');
      
      // Close the confirmation dialog
      closeDeleteAllConfirm();
      
      // If a video is currently selected, close the modal
      if (selectedVideo) {
        closeVideoModal();
      }
    } catch (err) {
      console.error('Error deleting all videos:', err);
      toast.error('Failed to delete all videos');
    } finally {
      setIsDeleting(false);
    }
  };
  
  // Function to handle combining audio and video files
  const handleCombineAudioVideo = async () => {
    if (!selectedVideoFile || !selectedAudioFile) {
      toast.error('Please select both video and audio files');
      return;
    }
    
    setIsCombining(true);
    
    try {
      console.log('Combining files:', selectedVideoFile, selectedAudioFile);
      
      // Create form data
      const formData = new FormData();
      formData.append('video_filename', selectedVideoFile);
      formData.append('audio_filename', selectedAudioFile);
      
      // Log the form data for debugging
      for (let [key, value] of formData.entries()) {
        console.log(`${key}: ${value}`);
      }
      
      // Make the request to combine the files
      const response = await axios.post(
        `${API_BASE_URL}/videos/combine-audio-video`,
        formData,
        {
          headers: {
            'Authorization': `Bearer ${token}`
            // Let axios set the Content-Type with boundary automatically
          },
          responseType: 'blob'
        }
      );
      
      // Get the filename from the Content-Disposition header if available
      const contentDisposition = response.headers['content-disposition'];
      let filename = 'combined_video.mp4';
      
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="(.+)"/i);
        if (filenameMatch && filenameMatch[1]) {
          filename = filenameMatch[1];
        }
      }
      
      // Create a URL for the blob
      const url = window.URL.createObjectURL(new Blob([response.data as BlobPart]));
      
      // Create a temporary link and trigger download
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      
      // Clean up
      window.URL.revokeObjectURL(url);
      document.body.removeChild(link);
      
      // Store the combined filename for streaming
      setCombinedVideoFilename(filename);
      
      toast.success('Audio and video combined successfully');
      setShowCombineModal(false);
      
      // Refresh the video list
      fetchVideos();
    } catch (error) {
      console.error('Error combining audio and video:', error);
      toast.error('Failed to combine audio and video');
    } finally {
      setIsCombining(false);
    }
  };

  if (loading) {
    return (
      <MainLayout>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="flex justify-center items-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
          </div>
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
          <div className="flex space-x-2">
            {user?.role === UserRole.ADMIN && videos.length > 0 && (
              <button 
                onClick={handleDeleteAllClick}
                className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded"
                disabled={isDeleting}
              >
                {isDeleting ? 'Deleting...' : 'Delete All Videos'}
              </button>
            )}
            <Link href="/capture/new" className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded">
              New Capture
            </Link>
          </div>
        </div>

        {videos.length === 0 ? (
          <div className="bg-white rounded-lg shadow p-6 text-center">
            <p className="text-gray-500">No videos available.</p>
            <Link href="/capture/new" className="text-blue-600 hover:text-blue-800 mt-2 inline-block">
              Start a new capture
            </Link>
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
                  <div className="flex justify-between items-start">
                    <h3 className="font-semibold text-lg mb-2 truncate">{video.title || video.filename}</h3>
                    {user?.role === UserRole.ADMIN && (
                      <button 
                        onClick={(e) => handleDeleteClick(e, video)}
                        className="text-red-600 hover:text-red-800"
                        title="Delete video"
                      >
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                    )}
                  </div>
                  <div className="text-sm text-gray-600 space-y-1">
                    <div>
                      <span className="font-medium">Size:</span> {formatFileSize(video.size)}
                    </div>
                    <div>
                      <span className="font-medium">Duration:</span> {formatDuration(video.duration)}
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
                      <Link href={`/capture/${video.capture_id}`} className="text-blue-600 hover:text-blue-800 text-sm">
                        View Capture Details
                      </Link>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Delete Confirmation Modal */}
        {showDeleteConfirm && videoToDelete && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-lg max-w-md w-full p-6">
              <h3 className="text-lg font-medium mb-4">Confirm Deletion</h3>
              <p className="mb-4">Are you sure you want to delete the video "{videoToDelete.title || videoToDelete.filename}"?</p>
              <div className="flex justify-end space-x-2">
                <button 
                  onClick={closeDeleteConfirm}
                  className="bg-gray-200 hover:bg-gray-300 text-gray-800 px-4 py-2 rounded"
                >
                  Cancel
                </button>
                <button 
                  onClick={() => deleteVideo(videoToDelete)}
                  className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded"
                  disabled={isDeleting}
                >
                  {isDeleting ? 'Deleting...' : 'Delete'}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Delete All Confirmation Modal */}
        {showDeleteAllConfirm && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-lg max-w-md w-full p-6">
              <h3 className="text-lg font-medium mb-4">Confirm Delete All</h3>
              <p className="mb-4">Are you sure you want to delete all videos? This action cannot be undone.</p>
              <div className="flex justify-end space-x-2">
                <button 
                  onClick={closeDeleteAllConfirm}
                  className="bg-gray-200 hover:bg-gray-300 text-gray-800 px-4 py-2 rounded"
                >
                  Cancel
                </button>
                <button 
                  onClick={deleteAllVideos}
                  className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded"
                  disabled={isDeleting}
                >
                  {isDeleting ? 'Deleting...' : 'Delete All'}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Audio/Video Combination Modal */}
        {showCombineModal && (
          <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-[100] p-4">
            <div className="bg-white rounded-lg shadow-xl max-w-md w-full">
              <div className="flex justify-between items-center p-4 border-b">
                <h2 className="text-xl font-semibold">Combine Audio and Video</h2>
                <button 
                  onClick={() => setShowCombineModal(false)}
                  className="text-gray-500 hover:text-gray-700"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
              <div className="p-4">
                <div className="mb-4">
                  <label className="block text-gray-700 text-sm font-bold mb-2">
                    Video File
                  </label>
                  <select
                    className="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline"
                    value={selectedVideoFile}
                    onChange={(e) => setSelectedVideoFile(e.target.value)}
                  >
                    <option value="">Select a video file</option>
                    {videos.map((video) => (
                      <option key={video.filename} value={video.filename}>
                        {video.filename}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="mb-4">
                  <label className="block text-gray-700 text-sm font-bold mb-2">
                    Audio File
                  </label>
                  <select
                    className="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline"
                    value={selectedAudioFile}
                    onChange={(e) => setSelectedAudioFile(e.target.value)}
                  >
                    <option value="">Select an audio file</option>
                    {videos.map((video) => (
                      <option key={video.filename} value={video.filename}>
                        {video.filename}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="flex justify-end">
                  <button
                    onClick={() => setShowCombineModal(false)}
                    className="bg-gray-300 hover:bg-gray-400 text-gray-800 font-bold py-2 px-4 rounded mr-2"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleCombineAudioVideo}
                    disabled={isCombining || !selectedVideoFile || !selectedAudioFile}
                    className={`${isCombining ? 'bg-green-400' : 'bg-green-600 hover:bg-green-700'} text-white font-bold py-2 px-4 rounded flex items-center`}
                  >
                    {isCombining ? (
                      <>
                        <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                        Processing...
                      </>
                    ) : (
                      'Combine Files'
                    )}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Video Modal */}
        {selectedVideo && (
          <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-lg max-w-4xl w-full max-h-screen overflow-auto">
              <div className="p-4 border-b flex justify-between items-center">
                <h3 className="text-lg font-medium">{selectedVideo.title || selectedVideo.filename}</h3>
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
                {combinedVideoFilename ? (
                  <video 
                    src={`${API_BASE_URL}/videos/stream-combined-with-token/${combinedVideoFilename}?token=${token}`} 
                    controls 
                    className="w-full h-full object-contain"
                    autoPlay
                  />
                ) : (
                  <video 
                    src={`${API_BASE_URL}/videos/stream-with-token/${selectedVideo.filename}?token=${token}`} 
                    controls 
                    className="w-full h-full object-contain"
                    autoPlay
                  />
                )}
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
                      <Link href={`/capture/${selectedVideo.capture_id}`} className="text-blue-600 hover:text-blue-800">
                        {selectedVideo.capture_id}
                      </Link>
                    </p>
                  )}
                </div>
              </div>
              <div className="p-4 border-t flex justify-end space-x-2">
                {user?.role === UserRole.ADMIN && (
                  <button 
                    onClick={() => {
                      setVideoToDelete(selectedVideo);
                      setShowDeleteConfirm(true);
                      closeVideoModal();
                    }}
                    className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded"
                    disabled={isDeleting}
                  >
                    {isDeleting ? 'Deleting...' : 'Delete Video'}
                  </button>
                )}
                <a 
                  href={`${API_BASE_URL}/videos/stream-with-token/${selectedVideo.filename}?token=${token}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded"
                >
                  Download Video
                </a>
                <button
                  onClick={() => {
                    setSelectedVideoFile(selectedVideo.filename);
                    setShowCombineModal(true);
                  }}
                  className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded"
                >
                  Combine Audio/Video
                </button>
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
