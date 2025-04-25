import React, { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/router';
import { useQuery, useMutation } from '@tanstack/react-query';
import Link from 'next/link';
import MainLayout from '../../../components/layout/MainLayout';
import { withAuth } from '../../../contexts/AuthContext';
import { api } from '../../../utils/api';

interface VideoClip {
  id: number;
  title: string;
  description: string;
  duration: number;
  file_path: string;
  thumbnail_url: string;
  created_at: string;
  updated_at: string;
  created_by_id: number;
  status: string;
}

interface EditClipFormData {
  title: string;
  description: string;
  start_time?: number;
  end_time?: number;
  generate_thumbnail?: boolean;
}

const VideoClipEditPage: React.FC = () => {
  const router = useRouter();
  const { id } = router.query;
  const videoRef = useRef<HTMLVideoElement>(null);
  
  // Form state
  const [formData, setFormData] = useState<EditClipFormData>({
    title: '',
    description: '',
    start_time: undefined,
    end_time: undefined,
    generate_thumbnail: false,
  });
  
  // Video player state
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isTrimming, setIsTrimming] = useState(false);
  const [previewMode, setPreviewMode] = useState(false);
  
  // Error state
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [successMessage, setSuccessMessage] = useState('');

  // Fetch video clip details
  const { data: clip, isLoading, isError } = useQuery<VideoClip>({
    queryKey: ['videoClip', id],
    queryFn: async () => {
      if (!id) throw new Error('No clip ID provided');
      return await api.get(`/clips/${id}`);
    },
    enabled: !!id,
  });

  // Update video clip mutation
  const updateClipMutation = useMutation({
    mutationFn: async (data: EditClipFormData) => {
      if (!id) throw new Error('No clip ID provided');
      return await api.put(`/clips/${id}`, data);
    },
    onSuccess: () => {
      setSuccessMessage('Video clip updated successfully');
      setTimeout(() => {
        setSuccessMessage('');
      }, 5000);
    },
    onError: (error: any) => {
      setErrors({
        form: error.message || 'Failed to update video clip',
      });
    },
  });

  // Initialize form data when clip is loaded
  useEffect(() => {
    if (clip) {
      setFormData({
        title: clip.title,
        description: clip.description || '',
      });
      setDuration(clip.duration);
    }
  }, [clip]);

  // Handle form input changes
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    
    // Clear error for this field
    if (errors[name]) {
      setErrors((prev) => {
        const newErrors = { ...prev };
        delete newErrors[name];
        return newErrors;
      });
    }
  };

  // Handle checkbox changes
  const handleCheckboxChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, checked } = e.target;
    setFormData((prev) => ({ ...prev, [name]: checked }));
  };

  // Handle video player events
  const handleTimeUpdate = (e: React.SyntheticEvent<HTMLVideoElement>) => {
    setCurrentTime(e.currentTarget.currentTime);
    
    // In preview mode, if we reach the end time, pause and go back to start time
    if (previewMode && formData.end_time && currentTime >= formData.end_time) {
      if (videoRef.current) {
        videoRef.current.pause();
        videoRef.current.currentTime = formData.start_time || 0;
        setIsPlaying(false);
        setPreviewMode(false);
      }
    }
  };

  const handleVideoLoaded = (e: React.SyntheticEvent<HTMLVideoElement>) => {
    setDuration(e.currentTarget.duration);
  };

  // Set start/end time for trimming
  const setStartTime = () => {
    setFormData((prev) => ({ 
      ...prev, 
      start_time: currentTime,
      // If end time is before new start time, reset it
      end_time: prev.end_time && prev.end_time <= currentTime ? undefined : prev.end_time
    }));
  };

  const setEndTime = () => {
    setFormData((prev) => ({ 
      ...prev, 
      end_time: currentTime,
      // If start time is after new end time, reset it
      start_time: prev.start_time && prev.start_time >= currentTime ? undefined : prev.start_time
    }));
  };

  // Preview trimmed clip
  const previewTrimmedClip = () => {
    if (!videoRef.current) return;
    
    const startTime = formData.start_time || 0;
    videoRef.current.currentTime = startTime;
    videoRef.current.play();
    setIsPlaying(true);
    setPreviewMode(true);
  };

  // Reset trimming
  const resetTrimming = () => {
    setFormData((prev) => ({
      ...prev,
      start_time: undefined,
      end_time: undefined,
    }));
    setIsTrimming(false);
    setPreviewMode(false);
  };

  // Format time in seconds to MM:SS
  const formatTime = (seconds: number): string => {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.floor(seconds % 60);
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
  };

  // Validate form before submission
  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {};
    
    if (!formData.title.trim()) {
      newErrors.title = 'Title is required';
    }
    
    if (formData.start_time !== undefined && formData.end_time !== undefined) {
      if (formData.start_time >= formData.end_time) {
        newErrors.trim = 'End time must be after start time';
      }
    } else if (formData.start_time !== undefined && formData.end_time === undefined) {
      newErrors.trim = 'End time is required when start time is set';
    } else if (formData.start_time === undefined && formData.end_time !== undefined) {
      newErrors.trim = 'Start time is required when end time is set';
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // Handle form submission
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) return;
    
    updateClipMutation.mutate(formData);
  };

  if (isLoading) {
    return (
      <MainLayout title="Loading... | Parliament Video Clip Manager">
        <div className="page-container flex items-center justify-center min-h-screen">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
            <p className="mt-4 text-gray-600">Loading video clip...</p>
          </div>
        </div>
      </MainLayout>
    );
  }

  if (isError || !clip) {
    return (
      <MainLayout title="Error | Parliament Video Clip Manager">
        <div className="page-container">
          <div className="bg-red-50 border-l-4 border-red-500 p-4 mb-6">
            <div className="flex">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
              </div>
              <div className="ml-3">
                <p className="text-sm text-red-700">
                  Error loading video clip. Please try again later.
                </p>
              </div>
            </div>
          </div>
          <div className="flex justify-center">
            <Link href="/clips">
              <span className="btn-primary rounded-md px-4 py-2 text-center cursor-pointer inline-block">
                Back to Video Clips
              </span>
            </Link>
          </div>
        </div>
      </MainLayout>
    );
  }

  return (
    <MainLayout title={`Edit ${clip.title} | Parliament Video Clip Manager`}>
      <div className="page-container">
        {/* Header */}
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-3xl font-bold text-gray-900">Edit Video Clip</h1>
          <div className="flex space-x-3">
            <Link href={`/clips/${clip.id}`}>
              <span className="text-gray-600 hover:text-gray-900 px-4 py-2 border border-gray-300 rounded-md cursor-pointer inline-block">
                Cancel
              </span>
            </Link>
            <button
              type="button"
              onClick={handleSubmit}
              disabled={updateClipMutation.isPending}
              className="btn-primary rounded-md px-4 py-2 text-center cursor-pointer inline-block disabled:opacity-50"
            >
              {updateClipMutation.isPending ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </div>

        {/* Success message */}
        {successMessage && (
          <div className="bg-green-50 border-l-4 border-green-500 p-4 mb-6">
            <div className="flex">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <div className="ml-3">
                <p className="text-sm text-green-700">{successMessage}</p>
              </div>
            </div>
          </div>
        )}

        {/* Form error */}
        {errors.form && (
          <div className="bg-red-50 border-l-4 border-red-500 p-4 mb-6">
            <div className="flex">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
              </div>
              <div className="ml-3">
                <p className="text-sm text-red-700">{errors.form}</p>
              </div>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Video preview */}
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <div className="aspect-w-16 aspect-h-9 bg-black">
              {clip.file_path && (
                <video
                  ref={videoRef}
                  src={clip.file_path}
                  poster={clip.thumbnail_url}
                  controls
                  onTimeUpdate={handleTimeUpdate}
                  onLoadedMetadata={handleVideoLoaded}
                  onPlay={() => setIsPlaying(true)}
                  onPause={() => setIsPlaying(false)}
                  className="w-full h-full object-contain"
                />
              )}
            </div>
            
            {/* Video controls */}
            <div className="p-4">
              <div className="flex justify-between items-center mb-2">
                <span className="text-sm text-gray-500">{formatTime(currentTime)}</span>
                <span className="text-sm text-gray-500">{formatTime(duration)}</span>
              </div>
              
              {/* Trimming controls */}
              <div className="mt-4">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-sm font-medium text-gray-700">Trim Video</h3>
                  <button
                    type="button"
                    onClick={() => setIsTrimming(!isTrimming)}
                    className="text-primary text-sm hover:text-primary-dark"
                  >
                    {isTrimming ? 'Cancel Trimming' : 'Trim Video'}
                  </button>
                </div>
                
                {isTrimming && (
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <span className="block text-xs text-gray-500 mb-1">Start Time</span>
                        <div className="flex items-center">
                          <span className="text-sm font-medium">
                            {formData.start_time !== undefined ? formatTime(formData.start_time) : '--:--'}
                          </span>
                          <button
                            type="button"
                            onClick={setStartTime}
                            className="ml-2 px-2 py-1 text-xs bg-primary text-white rounded hover:bg-primary-dark"
                          >
                            Set
                          </button>
                        </div>
                      </div>
                      
                      <div>
                        <span className="block text-xs text-gray-500 mb-1">End Time</span>
                        <div className="flex items-center">
                          <span className="text-sm font-medium">
                            {formData.end_time !== undefined ? formatTime(formData.end_time) : '--:--'}
                          </span>
                          <button
                            type="button"
                            onClick={setEndTime}
                            className="ml-2 px-2 py-1 text-xs bg-primary text-white rounded hover:bg-primary-dark"
                          >
                            Set
                          </button>
                        </div>
                      </div>
                    </div>
                    
                    {errors.trim && (
                      <p className="text-sm text-red-600">{errors.trim}</p>
                    )}
                    
                    <div className="flex space-x-2">
                      <button
                        type="button"
                        onClick={previewTrimmedClip}
                        disabled={formData.start_time === undefined || formData.end_time === undefined}
                        className="px-3 py-1 text-sm bg-primary text-white rounded hover:bg-primary-dark disabled:opacity-50"
                      >
                        Preview Trim
                      </button>
                      <button
                        type="button"
                        onClick={resetTrimming}
                        className="px-3 py-1 text-sm bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
                      >
                        Reset
                      </button>
                    </div>
                    
                    <div className="flex items-center">
                      <input
                        type="checkbox"
                        id="generate_thumbnail"
                        name="generate_thumbnail"
                        checked={formData.generate_thumbnail}
                        onChange={handleCheckboxChange}
                        className="h-4 w-4 text-primary focus:ring-primary border-gray-300 rounded"
                      />
                      <label htmlFor="generate_thumbnail" className="ml-2 block text-sm text-gray-900">
                        Generate new thumbnail from trimmed clip
                      </label>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Edit form */}
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <div className="p-6">
              <form onSubmit={handleSubmit}>
                <div className="space-y-6">
                  <div>
                    <label htmlFor="title" className="block text-sm font-medium text-gray-700">
                      Title *
                    </label>
                    <input
                      type="text"
                      id="title"
                      name="title"
                      value={formData.title}
                      onChange={handleInputChange}
                      className={`mt-1 form-input ${errors.title ? 'border-red-300 focus:ring-red-500 focus:border-red-500' : ''}`}
                      placeholder="Enter clip title"
                    />
                    {errors.title && (
                      <p className="mt-1 text-sm text-red-600">{errors.title}</p>
                    )}
                  </div>
                  
                  <div>
                    <label htmlFor="description" className="block text-sm font-medium text-gray-700">
                      Description
                    </label>
                    <textarea
                      id="description"
                      name="description"
                      rows={4}
                      value={formData.description}
                      onChange={handleInputChange}
                      className="mt-1 form-input"
                      placeholder="Enter clip description"
                    />
                  </div>
                  
                  <div>
                    <h3 className="text-sm font-medium text-gray-700 mb-2">Clip Information</h3>
                    <div className="bg-gray-50 p-4 rounded-md">
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <span className="block text-xs text-gray-500">Duration</span>
                          <span className="text-sm font-medium">
                            {formatTime(duration)}
                          </span>
                        </div>
                        <div>
                          <span className="block text-xs text-gray-500">Status</span>
                          <span className={`px-2 py-0.5 inline-flex text-xs leading-5 font-semibold rounded-full ${
                            clip.status === 'ready'
                              ? 'bg-green-100 text-green-800'
                              : clip.status === 'processing'
                              ? 'bg-yellow-100 text-yellow-800'
                              : 'bg-red-100 text-red-800'
                          }`}>
                            {clip.status.charAt(0).toUpperCase() + clip.status.slice(1)}
                          </span>
                        </div>
                        <div>
                          <span className="block text-xs text-gray-500">Created</span>
                          <span className="text-sm font-medium">
                            {new Date(clip.created_at).toLocaleDateString()}
                          </span>
                        </div>
                        <div>
                          <span className="block text-xs text-gray-500">Last Updated</span>
                          <span className="text-sm font-medium">
                            {new Date(clip.updated_at).toLocaleDateString()}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                  
                  <div className="flex justify-end pt-4">
                    <Link href={`/clips/${clip.id}`}>
                      <span className="mr-3 text-gray-600 hover:text-gray-900 px-4 py-2 border border-gray-300 rounded-md cursor-pointer inline-block">
                        Cancel
                      </span>
                    </Link>
                    <button
                      type="submit"
                      disabled={updateClipMutation.isPending}
                      className="btn-primary rounded-md px-4 py-2 text-center cursor-pointer inline-block disabled:opacity-50"
                    >
                      {updateClipMutation.isPending ? 'Saving...' : 'Save Changes'}
                    </button>
                  </div>
                </div>
              </form>
            </div>
          </div>
        </div>
      </div>
    </MainLayout>
  );
};

export default withAuth(VideoClipEditPage);
