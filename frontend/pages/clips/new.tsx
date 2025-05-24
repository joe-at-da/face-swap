import React, { useState, useRef, useEffect } from 'react';
import { useRouter } from 'next/router';
import { useMutation, useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import DarkLayout from '../../components/layout/DarkLayout';
import { withAuth } from '../../contexts/AuthContext';
import { api } from '../../utils/api';

interface CaptureSession {
  id: number;
  title: string;
  status: string;
  start_time: string;
  end_time: string | null;
  file_path: string;
  created_at: string;
}

interface CreateClipFormData {
  title: string;
  description: string;
  source_id?: number;
  source_type: 'upload' | 'capture';
  start_time?: number;
  end_time?: number;
  generate_thumbnail: boolean;
  file?: File;
}

const NewVideoClipPage: React.FC = () => {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  
  // URL parameters from recognition results
  const { capture_id, start_time, end_time, title, speaker_ids, segment_ids } = router.query;
  
  // Form state
  const [formData, setFormData] = useState<CreateClipFormData>({
    title: (title as string) || '',
    description: '',
    source_type: capture_id ? 'capture' : 'upload',
    source_id: capture_id ? parseInt(capture_id as string) : undefined,
    start_time: start_time ? parseFloat(start_time as string) : undefined,
    end_time: end_time ? parseFloat(end_time as string) : undefined,
    generate_thumbnail: true,
  });
  
  // Video player state
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  
  // Error state
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isUploading, setIsUploading] = useState(false);
  
  // The URL parameters are now extracted above

  // Fetch active capture sessions
  const { data: captureSessions, isLoading: capturesLoading } = useQuery({
    queryKey: ['activeCapturesSessions'],
    queryFn: async () => {
      return await api.get('/capture', { status: 'completed' });
    },
  });
  
  // Fetch speaker profiles if speaker_ids are provided
  const { data: speakerProfiles } = useQuery({
    queryKey: ['speakerProfiles', speaker_ids],
    queryFn: async () => {
      if (!speaker_ids) return [];
      const ids = (speaker_ids as string).split(',');
      const profiles = await Promise.all(
        ids.map(async (id) => {
          try {
            return await api.get(`/profiles/voice/${id}`);
          } catch (error) {
            console.error(`Failed to fetch profile for speaker ${id}:`, error);
            return null;
          }
        })
      );
      return profiles.filter(Boolean);
    },
    enabled: !!speaker_ids,
  });

  // Create clip mutation
  const createClipMutation = useMutation({
    mutationFn: async (data: FormData) => {
      return await api.post('/clips', data);
    },
    onSuccess: (data) => {
      router.push(`/clips/${data.id}`);
    },
    onError: (error: any) => {
      setErrors({
        form: error.message || 'Failed to create video clip',
      });
      setIsUploading(false);
    },
  });

  // Handle source type change
  const handleSourceTypeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const sourceType = e.target.value as 'upload' | 'capture';
    
    // Reset video-related state when changing source type
    setVideoUrl(null);
    setCurrentTime(0);
    setDuration(0);
    setIsPlaying(false);
    
    setFormData((prev) => ({
      ...prev,
      source_type: sourceType,
      source_id: undefined,
      file: undefined,
      start_time: undefined,
      end_time: undefined,
    }));
  };

  // Handle form input changes
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    
    if (name === 'source_id' && value) {
      // When selecting a capture session, load its video
      const selectedCapture = captureSessions?.find((session: CaptureSession) => session.id === parseInt(value));
      if (selectedCapture) {
        setVideoUrl(selectedCapture.file_path);
        
        // Suggest a title based on the capture session
        if (!formData.title) {
          setFormData((prev) => ({
            ...prev,
            title: `Clip from ${selectedCapture.title}`,
            source_id: parseInt(value),
          }));
        } else {
          setFormData((prev) => ({
            ...prev,
            source_id: parseInt(value),
          }));
        }
      }
    } else {
      setFormData((prev) => ({ ...prev, [name]: value }));
    }
    
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

  // Handle file selection
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    // Check file type
    if (!file.type.startsWith('video/')) {
      setErrors({
        file: 'Please select a valid video file',
      });
      return;
    }
    
    // Create object URL for preview
    const objectUrl = URL.createObjectURL(file);
    setVideoUrl(objectUrl);
    
    // Suggest a title based on the filename
    const fileName = file.name.replace(/\.[^/.]+$/, ''); // Remove extension
    if (!formData.title) {
      setFormData((prev) => ({
        ...prev,
        title: fileName,
        file,
      }));
    } else {
      setFormData((prev) => ({
        ...prev,
        file,
      }));
    }
    
    // Clean up previous object URL if any
    return () => {
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  };

  useEffect(() => {
    // Clean up video URL object when component unmounts
    return () => {
      if (videoUrl && videoUrl.startsWith('blob:')) {
        URL.revokeObjectURL(videoUrl);
      }
    };
  }, [videoUrl]);

  // Load capture video when component mounts or capture_id changes
  useEffect(() => {
    if (capture_id && formData.source_type === 'capture') {
      const loadCaptureVideo = async () => {
        try {
          const captureData = await api.get(`/capture/${capture_id}`);
          if (captureData && captureData.file_path) {
            setVideoUrl(captureData.file_path);
          }
        } catch (error) {
          console.error('Failed to load capture video:', error);
        }
      };
      
      loadCaptureVideo();
    }
  }, [capture_id, formData.source_type]);

  // Update description with speaker information when speaker profiles are loaded
  useEffect(() => {
    if (speakerProfiles && speakerProfiles.length > 0) {
      const speakerNames = speakerProfiles
        .map((profile: any) => profile.name)
        .join(', ');
      
      setFormData(prev => ({
        ...prev,
        description: prev.description || `Clip featuring ${speakerNames}. Created from recognition results.`
      }));
    }
  }, [speakerProfiles]);

  // Handle video player events
  const handleTimeUpdate = (e: React.SyntheticEvent<HTMLVideoElement>) => {
    setCurrentTime(e.currentTarget.currentTime);
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

  // Reset trimming
  const resetTrimming = () => {
    setFormData((prev) => ({
      ...prev,
      start_time: undefined,
      end_time: undefined,
    }));
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
    
    if (formData.source_type === 'upload' && !formData.file) {
      newErrors.file = 'Please select a video file';
    }
    
    if (formData.source_type === 'capture' && !formData.source_id) {
      newErrors.source_id = 'Please select a capture session';
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
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) return;
    
    setIsUploading(true);
    
    // Create FormData object for file upload
    const formDataObj = new FormData();
    formDataObj.append('title', formData.title);
    formDataObj.append('description', formData.description || '');
    formDataObj.append('source_type', formData.source_type);
    formDataObj.append('generate_thumbnail', String(formData.generate_thumbnail));
    
    if (formData.source_type === 'upload' && formData.file) {
      formDataObj.append('file', formData.file);
    } else if (formData.source_type === 'capture' && formData.source_id) {
      formDataObj.append('source_id', String(formData.source_id));
    }
    
    if (formData.start_time !== undefined) {
      formDataObj.append('start_time', String(formData.start_time));
    }
    
    if (formData.end_time !== undefined) {
      formDataObj.append('end_time', String(formData.end_time));
    }
    
    createClipMutation.mutate(formDataObj);
  };

  return (
    <DarkLayout>
      <div className="page-container">
        {/* Header */}
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-3xl font-bold text-gray-900">Create New Video Clip</h1>
          <Link href="/clips">
            <span className="text-gray-600 hover:text-gray-900 px-4 py-2 border border-gray-300 rounded-md cursor-pointer inline-block">
              Cancel
            </span>
          </Link>
        </div>

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

        <form onSubmit={handleSubmit}>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Left column - Video source */}
            <div>
              <div className="bg-white rounded-lg shadow overflow-hidden mb-6">
                <div className="px-6 py-4 border-b border-gray-200">
                  <h2 className="text-lg font-medium text-gray-800">Video Source</h2>
                </div>
                <div className="p-6">
                  <div className="space-y-6">
                    {/* Source type selection */}
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Select Source
                      </label>
                      <div className="flex space-x-4">
                        <div className="flex items-center">
                          <input
                            id="upload"
                            name="source_type"
                            type="radio"
                            value="upload"
                            checked={formData.source_type === 'upload'}
                            onChange={handleSourceTypeChange}
                            className="h-4 w-4 text-primary focus:ring-primary border-gray-300"
                          />
                          <label htmlFor="upload" className="ml-2 block text-sm text-gray-900">
                            Upload Video
                          </label>
                        </div>
                        <div className="flex items-center">
                          <input
                            id="capture"
                            name="source_type"
                            type="radio"
                            value="capture"
                            checked={formData.source_type === 'capture'}
                            onChange={handleSourceTypeChange}
                            className="h-4 w-4 text-primary focus:ring-primary border-gray-300"
                          />
                          <label htmlFor="capture" className="ml-2 block text-sm text-gray-900">
                            From Capture Session
                          </label>
                        </div>
                      </div>
                    </div>

                    {/* Upload file input */}
                    {formData.source_type === 'upload' && (
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Upload Video File
                        </label>
                        <div className="mt-1 flex justify-center px-6 pt-5 pb-6 border-2 border-gray-300 border-dashed rounded-md">
                          <div className="space-y-1 text-center">
                            <svg
                              className="mx-auto h-12 w-12 text-gray-400"
                              stroke="currentColor"
                              fill="none"
                              viewBox="0 0 48 48"
                              aria-hidden="true"
                            >
                              <path
                                d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02"
                                strokeWidth={2}
                                strokeLinecap="round"
                                strokeLinejoin="round"
                              />
                            </svg>
                            <div className="flex text-sm text-gray-600">
                              <label
                                htmlFor="file-upload"
                                className="relative cursor-pointer bg-white rounded-md font-medium text-primary hover:text-primary-dark focus-within:outline-none"
                              >
                                <span>Upload a video file</span>
                                <input
                                  id="file-upload"
                                  name="file-upload"
                                  type="file"
                                  accept="video/*"
                                  ref={fileInputRef}
                                  onChange={handleFileChange}
                                  className="sr-only"
                                />
                              </label>
                              <p className="pl-1">or drag and drop</p>
                            </div>
                            <p className="text-xs text-gray-500">MP4, MOV, AVI up to 500MB</p>
                          </div>
                        </div>
                        {errors.file && (
                          <p className="mt-1 text-sm text-red-600">{errors.file}</p>
                        )}
                        {formData.file && (
                          <p className="mt-2 text-sm text-gray-500">
                            Selected: {formData.file.name} ({(formData.file.size / (1024 * 1024)).toFixed(2)} MB)
                          </p>
                        )}
                      </div>
                    )}

                    {/* Capture session selection */}
                    {formData.source_type === 'capture' && (
                      <div>
                        <label htmlFor="source_id" className="block text-sm font-medium text-gray-700 mb-2">
                          Select Capture Session
                        </label>
                        <select
                          id="source_id"
                          name="source_id"
                          value={formData.source_id || ''}
                          onChange={handleInputChange}
                          className={`form-input ${errors.source_id ? 'border-red-300 focus:ring-red-500 focus:border-red-500' : ''}`}
                        >
                          <option value="">Select a capture session</option>
                          {capturesLoading ? (
                            <option disabled>Loading capture sessions...</option>
                          ) : captureSessions && captureSessions.length > 0 ? (
                            captureSessions.map((session: CaptureSession) => (
                              <option key={session.id} value={session.id}>
                                {session.title} ({new Date(session.created_at).toLocaleDateString()})
                              </option>
                            ))
                          ) : (
                            <option disabled>No completed capture sessions available</option>
                          )}
                        </select>
                        {errors.source_id && (
                          <p className="mt-1 text-sm text-red-600">{errors.source_id}</p>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Video preview */}
              {videoUrl && (
                <div className="bg-white rounded-lg shadow overflow-hidden">
                  <div className="px-6 py-4 border-b border-gray-200">
                    <h2 className="text-lg font-medium text-gray-800">Video Preview</h2>
                  </div>
                  <div className="aspect-w-16 aspect-h-9 bg-black">
                    <video
                      ref={videoRef}
                      src={videoUrl}
                      controls
                      onTimeUpdate={handleTimeUpdate}
                      onLoadedMetadata={handleVideoLoaded}
                      onPlay={() => setIsPlaying(true)}
                      onPause={() => setIsPlaying(false)}
                      className="w-full h-full object-contain"
                    />
                  </div>
                  
                  {/* Trimming controls */}
                  <div className="p-6">
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-sm text-gray-500">{formatTime(currentTime)}</span>
                      <span className="text-sm text-gray-500">{formatTime(duration)}</span>
                    </div>
                    
                    <div className="mt-4">
                      <h3 className="text-sm font-medium text-gray-700 mb-2">Trim Video (Optional)</h3>
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
                        
                        <button
                          type="button"
                          onClick={resetTrimming}
                          className="px-3 py-1 text-sm bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
                        >
                          Reset Trim Points
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Right column - Clip details */}
            <div className="bg-white rounded-lg shadow overflow-hidden">
              <div className="px-6 py-4 border-b border-gray-200">
                <h2 className="text-lg font-medium text-gray-800">Clip Details</h2>
              </div>
              <div className="p-6">
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
                      Generate thumbnail automatically
                    </label>
                  </div>
                  
                  <div className="pt-4">
                    <button
                      type="submit"
                      disabled={isUploading || createClipMutation.isPending}
                      className="w-full btn-primary rounded-md px-4 py-2 text-center cursor-pointer inline-block disabled:opacity-50"
                    >
                      {isUploading || createClipMutation.isPending ? 'Creating Clip...' : 'Create Video Clip'}
                    </button>
                  </div>
                  
                  {/* Speaker information if available */}
                  {speakerProfiles && speakerProfiles.length > 0 && (
                    <div className="mt-6 border-t border-gray-200 pt-4">
                      <h3 className="text-sm font-medium text-gray-700 mb-2">Featured Speakers</h3>
                      <div className="space-y-2">
                        {speakerProfiles.map((profile: any) => (
                          <div key={profile.id} className="flex items-center p-2 bg-gray-50 rounded">
                            {profile.image_url ? (
                              <img 
                                src={profile.image_url} 
                                alt={profile.name} 
                                className="w-8 h-8 rounded-full mr-2 object-cover"
                              />
                            ) : (
                              <div className="w-8 h-8 rounded-full bg-gray-300 flex items-center justify-center mr-2">
                                <span className="text-xs text-gray-600">
                                  {profile.name.charAt(0)}
                                </span>
                              </div>
                            )}
                            <div>
                              <p className="text-sm font-medium">{profile.name}</p>
                              {profile.role && (
                                <p className="text-xs text-gray-500">{profile.role}</p>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                      <p className="text-xs text-gray-500 mt-2">
                        Speaker information will be included with the clip for social media sharing.
                      </p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </form>
      </div>
    </DarkLayout>
  );
};

export default withAuth(NewVideoClipPage);
