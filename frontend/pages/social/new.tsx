import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import { useQuery, useMutation } from '@tanstack/react-query';
import Link from 'next/link';
import MainLayout from '../../components/layout/MainLayout';
import { withAuth } from '../../contexts/AuthContext';
import { UserRole } from '../../contexts/AuthContext';
import { api } from '../../utils/api';

interface VideoClip {
  id: number;
  title: string;
  description: string;
  duration: number;
  thumbnail_url: string | null;
  file_url: string;
  created_at: string;
}

interface SocialPostFormData {
  title: string;
  content: string;
  platform: 'twitter' | 'facebook' | 'instagram';
  clip_id: number | null;
  scheduled_time: string | null;
  status: 'draft' | 'scheduled';
}

const NewSocialPostPage: React.FC = () => {
  const router = useRouter();
  const { clip_id } = router.query;
  
  // Form state
  const [formData, setFormData] = useState<SocialPostFormData>({
    title: '',
    content: '',
    platform: 'twitter',
    clip_id: null,
    scheduled_time: null,
    status: 'draft',
  });
  
  // UI state
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isScheduled, setIsScheduled] = useState(false);
  const [selectedClip, setSelectedClip] = useState<VideoClip | null>(null);
  const [characterCount, setCharacterCount] = useState(0);
  
  // Platform character limits
  const characterLimits = {
    twitter: 280,
    facebook: 2000,
    instagram: 2200,
  };
  
  // Fetch video clips
  const { data: videoClips, isLoading: clipsLoading } = useQuery({
    queryKey: ['videoClips'],
    queryFn: async () => {
      return await api.get('/clips', { status: 'completed' });
    },
  });
  
  // Create social post mutation
  const createPostMutation = useMutation({
    mutationFn: async (data: SocialPostFormData) => {
      return await api.post('/social/posts', data);
    },
    onSuccess: (data) => {
      router.push(`/social/${data.id}`);
    },
    onError: (error: any) => {
      setErrors({
        form: error.message || 'Failed to create social media post',
      });
    },
  });
  
  // Set initial clip_id from query params
  useEffect(() => {
    if (clip_id && !formData.clip_id) {
      setFormData((prev) => ({ ...prev, clip_id: Number(clip_id) }));
    }
  }, [clip_id]);
  
  // Update selected clip when clip_id changes
  useEffect(() => {
    if (formData.clip_id && videoClips) {
      const clip = videoClips.find((c: VideoClip) => c.id === formData.clip_id);
      if (clip) {
        setSelectedClip(clip);
        
        // Suggest a title based on the clip
        if (!formData.title) {
          setFormData((prev) => ({
            ...prev,
            title: `Watch: ${clip.title}`,
          }));
        }
      }
    }
  }, [formData.clip_id, videoClips]);
  
  // Update character count when content changes
  useEffect(() => {
    setCharacterCount(formData.content.length);
  }, [formData.content]);
  
  // Handle form input changes
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
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
  
  // Handle clip selection
  const handleClipChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const clipId = e.target.value ? Number(e.target.value) : null;
    setFormData((prev) => ({ ...prev, clip_id: clipId }));
  };
  
  // Toggle scheduling option
  const handleScheduleToggle = (e: React.ChangeEvent<HTMLInputElement>) => {
    setIsScheduled(e.target.checked);
    
    // Update status based on scheduling
    setFormData((prev) => ({
      ...prev,
      status: e.target.checked ? 'scheduled' : 'draft',
      scheduled_time: e.target.checked ? prev.scheduled_time : null,
    }));
  };
  
  // Validate form before submission
  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {};
    
    if (!formData.title.trim()) {
      newErrors.title = 'Title is required';
    }
    
    if (!formData.content.trim()) {
      newErrors.content = 'Content is required';
    } else if (formData.content.length > characterLimits[formData.platform]) {
      newErrors.content = `Content exceeds the ${formData.platform} character limit of ${characterLimits[formData.platform]}`;
    }
    
    if (!formData.clip_id) {
      newErrors.clip_id = 'Please select a video clip';
    }
    
    if (isScheduled && !formData.scheduled_time) {
      newErrors.scheduled_time = 'Scheduled time is required';
    }
    
    if (isScheduled && formData.scheduled_time) {
      const scheduledDate = new Date(formData.scheduled_time);
      const now = new Date();
      
      if (scheduledDate <= now) {
        newErrors.scheduled_time = 'Scheduled time must be in the future';
      }
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };
  
  // Handle form submission
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) return;
    
    createPostMutation.mutate(formData);
  };
  
  // Get current date-time in ISO format for datetime-local input
  const getCurrentDateTime = (): string => {
    const now = new Date();
    now.setMinutes(now.getMinutes() + 5); // Add 5 minutes to current time
    return now.toISOString().slice(0, 16); // Format as YYYY-MM-DDTHH:MM
  };
  
  // Get platform icon
  const getPlatformIcon = (platform: string): JSX.Element => {
    switch (platform) {
      case 'twitter':
        return (
          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
            <path d="M23.953 4.57a10 10 0 01-2.825.775 4.958 4.958 0 002.163-2.723c-.951.555-2.005.959-3.127 1.184a4.92 4.92 0 00-8.384 4.482C7.69 8.095 4.067 6.13 1.64 3.162a4.822 4.822 0 00-.666 2.475c0 1.71.87 3.213 2.188 4.096a4.904 4.904 0 01-2.228-.616v.06a4.923 4.923 0 003.946 4.827 4.996 4.996 0 01-2.212.085 4.936 4.936 0 004.604 3.417 9.867 9.867 0 01-6.102 2.105c-.39 0-.779-.023-1.17-.067a13.995 13.995 0 007.557 2.209c9.053 0 13.998-7.496 13.998-13.985 0-.21 0-.42-.015-.63A9.935 9.935 0 0024 4.59z" />
          </svg>
        );
      case 'facebook':
        return (
          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
            <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z" />
          </svg>
        );
      case 'instagram':
        return (
          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
            <path d="M12 0C8.74 0 8.333.015 7.053.072 5.775.132 4.905.333 4.14.63c-.789.306-1.459.717-2.126 1.384S.935 3.35.63 4.14C.333 4.905.131 5.775.072 7.053.012 8.333 0 8.74 0 12s.015 3.667.072 4.947c.06 1.277.261 2.148.558 2.913.306.788.717 1.459 1.384 2.126.667.666 1.336 1.079 2.126 1.384.766.296 1.636.499 2.913.558C8.333 23.988 8.74 24 12 24s3.667-.015 4.947-.072c1.277-.06 2.148-.262 2.913-.558.788-.306 1.459-.718 2.126-1.384.666-.667 1.079-1.335 1.384-2.126.296-.765.499-1.636.558-2.913.06-1.28.072-1.687.072-4.947s-.015-3.667-.072-4.947c-.06-1.277-.262-2.149-.558-2.913-.306-.789-.718-1.459-1.384-2.126C21.319 1.347 20.651.935 19.86.63c-.765-.297-1.636-.499-2.913-.558C15.667.012 15.26 0 12 0zm0 2.16c3.203 0 3.585.016 4.85.071 1.17.055 1.805.249 2.227.415.562.217.96.477 1.382.896.419.42.679.819.896 1.381.164.422.36 1.057.413 2.227.057 1.266.07 1.646.07 4.85s-.015 3.585-.074 4.85c-.061 1.17-.256 1.805-.421 2.227-.224.562-.479.96-.897 1.382-.419.419-.824.679-1.38.896-.42.164-1.065.36-2.235.413-1.274.057-1.649.07-4.859.07-3.211 0-3.586-.015-4.859-.074-1.171-.061-1.816-.256-2.236-.421-.569-.224-.96-.479-1.379-.897-.421-.419-.69-.824-.9-1.38-.165-.42-.359-1.065-.42-2.235-.045-1.26-.061-1.649-.061-4.844 0-3.196.016-3.586.061-4.861.061-1.17.255-1.814.42-2.234.21-.57.479-.96.9-1.381.419-.419.81-.689 1.379-.898.42-.166 1.051-.361 2.221-.421 1.275-.045 1.65-.06 4.859-.06l.045.03zm0 3.678c-3.405 0-6.162 2.76-6.162 6.162 0 3.405 2.76 6.162 6.162 6.162 3.405 0 6.162-2.76 6.162-6.162 0-3.405-2.76-6.162-6.162-6.162zM12 16c-2.21 0-4-1.79-4-4s1.79-4 4-4 4 1.79 4 4-1.79 4-4 4zm7.846-10.405c0 .795-.646 1.44-1.44 1.44-.795 0-1.44-.646-1.44-1.44 0-.794.646-1.439 1.44-1.439.793-.001 1.44.645 1.44 1.439z" />
          </svg>
        );
      default:
        return <span className="w-5 h-5"></span>;
    }
  };
  
  return (
    <MainLayout title="Create Social Media Post | Parliament Video Clip Manager">
      <div className="page-container">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-3xl font-bold text-gray-900">Create Social Media Post</h1>
          <Link href="/social">
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
        
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left column - Post details */}
          <div className="lg:col-span-2">
            <form onSubmit={handleSubmit}>
              <div className="bg-white rounded-lg shadow overflow-hidden mb-6">
                <div className="px-6 py-4 border-b border-gray-200">
                  <h2 className="text-lg font-medium text-gray-800">Post Details</h2>
                </div>
                
                <div className="p-6 space-y-6">
                  {/* Platform selection */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Platform *
                    </label>
                    <div className="grid grid-cols-3 gap-4">
                      {['twitter', 'facebook', 'instagram'].map((platform) => (
                        <div key={platform}>
                          <label
                            htmlFor={platform}
                            className={`flex flex-col items-center justify-center p-4 border rounded-lg cursor-pointer ${
                              formData.platform === platform
                                ? 'border-primary bg-primary-50 text-primary'
                                : 'border-gray-300 hover:bg-gray-50'
                            }`}
                          >
                            <div className="mb-2">{getPlatformIcon(platform)}</div>
                            <div className="text-sm font-medium capitalize">{platform}</div>
                            <input
                              type="radio"
                              id={platform}
                              name="platform"
                              value={platform}
                              checked={formData.platform === platform}
                              onChange={handleInputChange}
                              className="sr-only"
                            />
                          </label>
                        </div>
                      ))}
                    </div>
                  </div>
                  
                  {/* Video clip selection */}
                  <div>
                    <label htmlFor="clip_id" className="block text-sm font-medium text-gray-700 mb-2">
                      Video Clip *
                    </label>
                    <select
                      id="clip_id"
                      name="clip_id"
                      value={formData.clip_id || ''}
                      onChange={handleClipChange}
                      className={`form-input ${errors.clip_id ? 'border-red-300 focus:ring-red-500 focus:border-red-500' : ''}`}
                    >
                      <option value="">Select a video clip</option>
                      {clipsLoading ? (
                        <option disabled>Loading video clips...</option>
                      ) : videoClips && videoClips.length > 0 ? (
                        videoClips.map((clip: VideoClip) => (
                          <option key={clip.id} value={clip.id}>
                            {clip.title} ({Math.floor(clip.duration / 60)}:{(clip.duration % 60).toString().padStart(2, '0')})
                          </option>
                        ))
                      ) : (
                        <option disabled>No video clips available</option>
                      )}
                    </select>
                    {errors.clip_id && (
                      <p className="mt-1 text-sm text-red-600">{errors.clip_id}</p>
                    )}
                  </div>
                  
                  {/* Title */}
                  <div>
                    <label htmlFor="title" className="block text-sm font-medium text-gray-700 mb-2">
                      Post Title *
                    </label>
                    <input
                      type="text"
                      id="title"
                      name="title"
                      value={formData.title}
                      onChange={handleInputChange}
                      className={`form-input ${errors.title ? 'border-red-300 focus:ring-red-500 focus:border-red-500' : ''}`}
                      placeholder="Enter post title"
                    />
                    {errors.title && (
                      <p className="mt-1 text-sm text-red-600">{errors.title}</p>
                    )}
                  </div>
                  
                  {/* Content */}
                  <div>
                    <label htmlFor="content" className="block text-sm font-medium text-gray-700 mb-2">
                      Post Content *
                    </label>
                    <textarea
                      id="content"
                      name="content"
                      rows={5}
                      value={formData.content}
                      onChange={handleInputChange}
                      className={`form-input ${errors.content ? 'border-red-300 focus:ring-red-500 focus:border-red-500' : ''}`}
                      placeholder={`Write your ${formData.platform} post...`}
                    />
                    <div className="mt-1 flex justify-between items-center">
                      {errors.content ? (
                        <p className="text-sm text-red-600">{errors.content}</p>
                      ) : (
                        <p className="text-sm text-gray-500">
                          Include hashtags and mentions as needed
                        </p>
                      )}
                      <p className={`text-sm ${
                        characterCount > characterLimits[formData.platform]
                          ? 'text-red-600'
                          : characterCount > characterLimits[formData.platform] * 0.8
                          ? 'text-yellow-600'
                          : 'text-gray-500'
                      }`}>
                        {characterCount}/{characterLimits[formData.platform]}
                      </p>
                    </div>
                  </div>
                  
                  {/* Schedule toggle */}
                  <div className="pt-4">
                    <div className="flex items-start">
                      <div className="flex items-center h-5">
                        <input
                          id="schedule"
                          name="schedule"
                          type="checkbox"
                          checked={isScheduled}
                          onChange={handleScheduleToggle}
                          className="h-4 w-4 text-primary focus:ring-primary border-gray-300 rounded"
                        />
                      </div>
                      <div className="ml-3 text-sm">
                        <label htmlFor="schedule" className="font-medium text-gray-700">
                          Schedule for later
                        </label>
                        <p className="text-gray-500">
                          Set a specific time to publish this post
                        </p>
                      </div>
                    </div>
                  </div>
                  
                  {/* Scheduled time */}
                  {isScheduled && (
                    <div>
                      <label htmlFor="scheduled_time" className="block text-sm font-medium text-gray-700 mb-2">
                        Scheduled Time *
                      </label>
                      <input
                        type="datetime-local"
                        id="scheduled_time"
                        name="scheduled_time"
                        value={formData.scheduled_time || ''}
                        onChange={handleInputChange}
                        min={getCurrentDateTime()}
                        className={`form-input ${errors.scheduled_time ? 'border-red-300 focus:ring-red-500 focus:border-red-500' : ''}`}
                      />
                      {errors.scheduled_time && (
                        <p className="mt-1 text-sm text-red-600">{errors.scheduled_time}</p>
                      )}
                    </div>
                  )}
                  
                  {/* Submit button */}
                  <div className="pt-4">
                    <button
                      type="submit"
                      disabled={createPostMutation.isPending}
                      className="w-full btn-primary rounded-md px-4 py-2 text-center cursor-pointer inline-block disabled:opacity-50"
                    >
                      {createPostMutation.isPending
                        ? 'Creating Post...'
                        : isScheduled
                        ? 'Schedule Post'
                        : 'Save as Draft'}
                    </button>
                  </div>
                </div>
              </div>
            </form>
          </div>
          
          {/* Right column - Preview */}
          <div>
            <div className="bg-white rounded-lg shadow overflow-hidden sticky top-6">
              <div className="px-6 py-4 border-b border-gray-200">
                <h2 className="text-lg font-medium text-gray-800">Post Preview</h2>
              </div>
              
              <div className="p-6">
                {selectedClip ? (
                  <div className="space-y-4">
                    {/* Platform header */}
                    <div className="flex items-center">
                      <div className={`mr-2 text-${formData.platform === 'twitter' ? 'blue' : formData.platform === 'facebook' ? 'indigo' : 'pink'}-500`}>
                        {getPlatformIcon(formData.platform)}
                      </div>
                      <span className="text-sm font-medium capitalize">
                        {formData.platform} {isScheduled ? 'Post Preview (Scheduled)' : 'Post Preview'}
                      </span>
                    </div>
                    
                    {/* Video thumbnail */}
                    <div className="aspect-w-16 aspect-h-9 bg-gray-100 rounded overflow-hidden">
                      {selectedClip.thumbnail_url ? (
                        <img
                          src={selectedClip.thumbnail_url}
                          alt={selectedClip.title}
                          className="w-full h-full object-cover"
                        />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center text-gray-500">
                          No thumbnail available
                        </div>
                      )}
                      <div className="absolute inset-0 flex items-center justify-center">
                        <div className="bg-black bg-opacity-50 rounded-full p-3">
                          <svg className="w-8 h-8 text-white" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clipRule="evenodd" />
                          </svg>
                        </div>
                      </div>
                    </div>
                    
                    {/* Post content */}
                    <div>
                      <h3 className="font-bold text-gray-900">{formData.title || 'Post Title'}</h3>
                      <p className="mt-1 text-gray-700 whitespace-pre-line">
                        {formData.content || `Your ${formData.platform} post content will appear here...`}
                      </p>
                    </div>
                    
                    {/* Video info */}
                    <div className="pt-2 text-sm text-gray-500">
                      <p>Video: {selectedClip.title}</p>
                      <p>Duration: {Math.floor(selectedClip.duration / 60)}:{(selectedClip.duration % 60).toString().padStart(2, '0')}</p>
                    </div>
                    
                    {/* Scheduled time */}
                    {isScheduled && formData.scheduled_time && (
                      <div className="pt-2 text-sm text-purple-600">
                        Scheduled for: {new Date(formData.scheduled_time).toLocaleString()}
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="text-center py-10 text-gray-500">
                    <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                    </svg>
                    <p className="mt-2">Select a video clip to see preview</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </MainLayout>
  );
};

export default withAuth(NewSocialPostPage, [UserRole.ADMIN, UserRole.MP, UserRole.STAFF]);
