import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import { useMutation } from '@tanstack/react-query';
import axios from 'axios';
import Link from 'next/link';
import MainLayout from '../../components/layout/MainLayout';
import { withAuth, useAuth } from '../../contexts/AuthContext';
import { UserRole } from '../../contexts/AuthContext';
import { api } from '../../utils/api';

// API base URL
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api/v1';

// Helper function to check if source_url includes a string
const sourceUrlIncludes = (url: string | { video_url: string; audio_url?: string }, searchString: string): boolean => {
  if (typeof url === 'string') {
    return url.includes(searchString);
  } else if (url && typeof url === 'object' && 'video_url' in url) {
    return url.video_url.includes(searchString);
  }
  return false;
};

// Helper function to get a string representation of source_url
const getSourceUrlString = (url: string | { video_url: string; audio_url?: string }): string => {
  if (typeof url === 'string') {
    return url;
  } else if (url && typeof url === 'object' && 'video_url' in url) {
    return url.video_url;
  }
  return '';
};

interface CaptureFormData {
  title: string;
  description: string;
  source_url: string | {
    video_url: string;
    audio_url?: string;
  };
  scheduled_start?: string;
  scheduled_end?: string;
  enable_facial_recognition?: boolean;
  duration?: number;
}

interface ValidationResult {
  success: boolean;
  message: string;
  streamUrl?: string;
  timeMarker?: number;
  error?: string;
}

interface ExtractUrlResponse {
  direct_stream: {
    video_url: string;
    audio_url?: string;
  } | string;
  event_id?: string;
  time_marker?: {
    seconds: number;
  };
}

interface TestStreamResponse {
  url: string | {
    video_url: string;
    audio_url?: string;
  };
  is_valid: boolean;
  message?: string;
}

const NewCapturePage: React.FC = () => {
  const router = useRouter();
  const { token } = useAuth();
  const [formData, setFormData] = useState<CaptureFormData>({
    title: '',
    description: '',
    source_url: 'https://parliamentlive.tv/event/index/263b4186-393c-49ce-aa55-68b9accd7a4e?in=13:25:38',
    enable_facial_recognition: true,
    duration: 300, // Default 5 minutes
  });
  
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [scheduleCapture, setScheduleCapture] = useState(false);
  const [isValidating, setIsValidating] = useState(false);
  const [validationResult, setValidationResult] = useState<ValidationResult | null>(null);
  const [activeCapture, setActiveCapture] = useState<{id: number, started_by: string, started_at: string} | null>(null);
  const [isStoppingCapture, setIsStoppingCapture] = useState(false);
  
  // Configure axios with authentication headers
  const getAuthHeaders = () => {
    return {
      headers: {
        Authorization: `Bearer ${token}`
      }
    };
  };

  // Check for active captures when component loads
  useEffect(() => {
    // Only check for active captures if we have a token
    if (!token) return;
    
    const checkActiveCaptures = async () => {
      try {
        // Wait a bit to ensure auth context is fully initialized
        await new Promise(resolve => setTimeout(resolve, 500));
        
        const response = await axios.get<any[]>(
          `${API_BASE_URL}/parliament-tv?status=active`,
          getAuthHeaders()
        );
        
        console.log('Active captures:', response.data);
        
        if (Array.isArray(response.data) && response.data.length > 0) {
          const activeCapture = response.data[0];
          const user = activeCapture.created_by;
          
          setErrors({
            form: `A capture session is already in progress. Started by ${user.name} at ${new Date(activeCapture.created_at).toLocaleString()}.`
          });
          
          setActiveCapture({
            id: activeCapture.id,
            started_by: user.name,
            started_at: activeCapture.created_at
          });
        }
      } catch (err) {
        console.error('Error checking active captures:', err);
        // Don't show error to user, just log it
      }
    };
    
    checkActiveCaptures();
  }, [token]);

  // Stop active capture
  const stopActiveCapture = async () => {
    if (!activeCapture) return;
    
    setIsStoppingCapture(true);
    
    try {
      const response = await axios.post(
        `${API_BASE_URL}/parliament-tv/${activeCapture.id}/stop`,
        {},
        getAuthHeaders()
      );
      
      console.log('Stop capture response:', response.data);
      
      // Clear active capture and error
      setActiveCapture(null);
      setErrors({});
      
      // Show success message
      alert('Capture stopped successfully');
      
      // Refresh the page
      window.location.reload();
    } catch (err) {
      console.error('Error stopping capture:', err);
      alert('Failed to stop capture. Please try again.');
    } finally {
      setIsStoppingCapture(false);
    }
  };

  // Validate Parliament TV URL
  const validateUrl = async () => {
    if (!formData.source_url) return;

    setIsValidating(true);
    setValidationResult(null);

    try {
      // First extract the stream URL
      const extractResponse = await axios.get<ExtractUrlResponse>(
        `${API_BASE_URL}/parliament-tv/extract-url`, 
        {
          params: { url: formData.source_url },
          ...getAuthHeaders()
        }
      );
      
      console.log('Extract URL response:', extractResponse.data);
      
      if (!extractResponse.data.direct_stream) {
        setValidationResult({
          success: false,
          message: 'Failed to extract stream URL from Parliament TV page',
          error: 'No direct stream URL found'
        });
        setIsValidating(false);
        return;
      }
      
      // Prepare parameters for testing the stream URL
      let params = {};
      let streamUrl = '';
      
      // Handle both string and object formats for direct_stream
      if (typeof extractResponse.data.direct_stream === 'string') {
        streamUrl = extractResponse.data.direct_stream;
        params = { url: streamUrl };
      } else if (typeof extractResponse.data.direct_stream === 'object') {
        // If it's an object with video_url and audio_url
        streamUrl = extractResponse.data.direct_stream.video_url;
        const audioUrl = extractResponse.data.direct_stream.audio_url || '';
        
        params = { video_url: streamUrl };
        if (audioUrl) {
          params = { ...params, audio_url: audioUrl };
        }
      }
      
      // Now test if the stream URL is valid
      const testResponse = await axios.get<TestStreamResponse>(
        `${API_BASE_URL}/parliament-tv/test-url`,
        {
          params,
          ...getAuthHeaders()
        }
      );
      
      console.log('Test URL response:', testResponse.data);
      
      if (testResponse.data.is_valid) {
        // Stream is valid
        setValidationResult({
          success: true,
          message: 'Stream URL is valid and ready for capture.',
          streamUrl: streamUrl,
          timeMarker: extractResponse.data.time_marker?.seconds || 0
        });
        
        // Update form data with direct stream URL - keep the original object structure
        setFormData(prev => ({
          ...prev,
          source_url: extractResponse.data.direct_stream
        }));
      } else {
        // Stream is not valid
        setValidationResult({
          success: false,
          message: 'Stream URL is not valid or cannot be played.',
          error: 'Stream validation failed'
        });
      }
    } catch (error: any) {
      console.error('URL validation error:', error);
      
      setValidationResult({
        success: false,
        message: 'Failed to validate stream URL',
        error: error.response?.data?.detail || error.message || 'Unknown error'
      });
    } finally {
      setIsValidating(false);
    }
  };

  // Start capture mutation
  const startCaptureMutation = useMutation({
    mutationFn: async (data: CaptureFormData) => {
    // For Parliament TV captures, use the parliament-tv endpoint
    if (sourceUrlIncludes(data.source_url, 'parliamentlive.tv')) {
      // The backend expects url to be a string, so we need to handle the different formats
      let urlParam: string;
      
      if (typeof data.source_url === 'string') {
        // If it's already a string, use it directly
        urlParam = data.source_url;
      } else if (typeof data.source_url === 'object') {
        // If it's an object with video_url and audio_url, use the video_url
        // The backend will extract both video and audio streams from the Parliament TV page
        urlParam = data.source_url.video_url;
        
        // Log what we're doing for debugging
        console.log('Using video_url from source_url object:', urlParam);
      } else {
        // Fallback to an empty string if somehow we have an invalid type
        urlParam = '';
      }
      
      const payload = {
        url: urlParam, // This must be a string as per the backend schema
        title: data.title,
        description: data.description,
        duration: data.duration,
        enable_facial_recognition: data.enable_facial_recognition,
        scheduled_start: data.scheduled_start,
        scheduled_end: data.scheduled_end
      };
      
      // Use axios directly to call the parliament-tv endpoint
      console.log('[CAPTURE DEBUG] POST request to /parliament-tv with data', payload);
      const response = await axios.post(
        `${API_BASE_URL}/parliament-tv`,
        payload,
        getAuthHeaders()
      );
      
      return response.data;
    } else {
      // For other captures, we need to ensure source_url is a string
      const modifiedData = { ...data };
      
      if (typeof modifiedData.source_url === 'object') {
        modifiedData.source_url = modifiedData.source_url.video_url;
      }
      
      // For other captures, use the regular capture endpoint
      console.log('[CAPTURE DEBUG] POST request to /capture with data', modifiedData);
      return await api.post('/capture', modifiedData);
    }
  },
    onSuccess: (data) => {
      router.push(`/capture/${data.id}`);
    },
    onError: (error: any) => {
      console.error('Capture error:', error);
      
      // Check if it's a conflict error (409)
      if (error.response?.status === 409) {
        const conflictData = error.response.data.detail;
        
        setErrors({
          form: `A capture session is already in progress. Started by ${conflictData.started_by} at ${new Date(conflictData.started_at).toLocaleString()}.`
        });
        
        setActiveCapture({
          id: conflictData.capture_id,
          started_by: conflictData.started_by,
          started_at: conflictData.started_at
        });
      } else {
        setErrors({
          form: error.response?.data?.detail || error.message || 'Failed to start capture session'
        });
      }
    },
  });

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

  // Toggle scheduling option
  const handleScheduleToggle = (e: React.ChangeEvent<HTMLInputElement>) => {
    setScheduleCapture(e.target.checked);
    
    // Clear scheduled times if scheduling is disabled
    if (!e.target.checked) {
      setFormData((prev) => ({
        ...prev,
        scheduled_start: undefined,
        scheduled_end: undefined,
      }));
    }
  };

  // Validate form before submission
  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {};
    
    if (!formData.title.trim()) {
      newErrors.title = 'Title is required';
    }
    
    if (!getSourceUrlString(formData.source_url).trim()) {
      newErrors.source_url = 'Source URL is required';
    } else if (sourceUrlIncludes(formData.source_url, 'parliamentlive.tv') && !validationResult?.success) {
      newErrors.source_url = 'Please validate the Parliament TV URL first';
    }
    
    if (scheduleCapture) {
      if (!formData.scheduled_start) {
        newErrors.scheduled_start = 'Scheduled start time is required';
      }
      
      if (formData.scheduled_start && formData.scheduled_end) {
        const startDate = new Date(formData.scheduled_start);
        const endDate = new Date(formData.scheduled_end);
        
        if (startDate >= endDate) {
          newErrors.scheduled_end = 'End time must be after start time';
        }
      }
      
      // Ensure scheduled start is in the future
      if (formData.scheduled_start) {
        const startDate = new Date(formData.scheduled_start);
        const now = new Date();
        
        if (startDate <= now) {
          newErrors.scheduled_start = 'Scheduled start time must be in the future';
        }
      }
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // Handle form submission
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) return;
    
    const submitData = { ...formData };
    
    // Only include scheduled times if scheduling is enabled
    if (!scheduleCapture) {
      delete submitData.scheduled_start;
      delete submitData.scheduled_end;
    }
    
    startCaptureMutation.mutate(submitData);
  };

  // Get current date-time in ISO format for datetime-local input
  const getCurrentDateTime = (): string => {
    const now = new Date();
    now.setMinutes(now.getMinutes() + 5); // Add 5 minutes to current time
    return now.toISOString().slice(0, 16); // Format as YYYY-MM-DDTHH:MM
  };

  // Get default end time (current time + 2 hours)
  const getDefaultEndTime = (): string => {
    const now = new Date();
    now.setHours(now.getHours() + 2); // Add 2 hours to current time
    return now.toISOString().slice(0, 16); // Format as YYYY-MM-DDTHH:MM
  };

  return (
    <MainLayout title="Start New Capture | Parliament Video Clip Manager">
      <div className="page-container">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-3xl font-bold text-gray-900">Start New Capture</h1>
          <Link href="/capture">
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

        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-medium text-gray-800">Capture Details</h2>
          </div>
          
          <form onSubmit={handleSubmit} className="p-6">
            <div className="space-y-6">
              <div className="grid grid-cols-1 gap-6">
                {/* Title */}
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
                    placeholder="Enter capture session title"
                  />
                  {errors.title && (
                    <p className="mt-1 text-sm text-red-600">{errors.title}</p>
                  )}
                </div>
                
                {/* Description */}
                <div>
                  <label htmlFor="description" className="block text-sm font-medium text-gray-700">
                    Description
                  </label>
                  <textarea
                    id="description"
                    name="description"
                    rows={3}
                    value={formData.description}
                    onChange={handleInputChange}
                    className="mt-1 w-200 form-input"
                    placeholder="Enter capture session description"
                  />
                </div>
                
                {/* Source URL */}
                <div>
                  <label htmlFor="source_url" className="block text-sm font-medium text-gray-700">
                    Source URL
                  </label>
                  <div className="mt-1 flex rounded-md shadow-sm">
                    <input
                      type="url"
                      id="source_url"
                      name="source_url"
                      placeholder="https://www.parliamentlive.tv/Event/Index/..."
                      value={getSourceUrlString(formData.source_url)}
                      onChange={handleInputChange}
                      className={`flex-1 form-input rounded-none rounded-l-md ${errors.source_url ? 'border-red-300 focus:ring-red-500 focus:border-red-500' : ''}`}
                    />
                    <button
                      type="button"
                      onClick={validateUrl}
                      disabled={isValidating || !sourceUrlIncludes(formData.source_url, 'parliamentlive.tv')}
                      className="inline-flex items-center px-3 py-2 border border-l-0 border-gray-300 rounded-r-md bg-indigo-600 text-white hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:bg-gray-400 disabled:cursor-not-allowed"
                    >
                      {isValidating ? 'Validating...' : 'Validate'}
                    </button>
                  </div>
                  {errors.source_url && (
                    <p className="mt-1 text-sm text-red-600">{errors.source_url}</p>
                  )}
                  {validationResult && (
                    <div className={`mt-2 text-sm ${validationResult.success ? 'text-green-600' : 'text-red-600'}`}>
                      {validationResult.message}
                      {validationResult.timeMarker && validationResult.success && (
                        <p className="text-green-600">Time marker detected: {validationResult.timeMarker} seconds</p>
                      )}
                    </div>
                  )}
                </div>
                
                {/* Parliament TV specific options - only show if URL is from parliamentlive.tv */}
                {sourceUrlIncludes(formData.source_url, 'parliamentlive.tv') && (
                  <div className="space-y-4 border-t border-gray-200 pt-4">
                    <h3 className="text-lg font-medium text-gray-900">Parliament TV Options</h3>
                    
                    {/* Duration */}
                    <div>
                      <label htmlFor="duration" className="block text-sm font-medium text-gray-700">
                        Maximum Duration (seconds)
                      </label>
                      <input
                        type="number"
                        id="duration"
                        name="duration"
                        min="60"
                        max="7200"
                        value={formData.duration || 300}
                        onChange={(e) => setFormData(prev => ({ ...prev, duration: parseInt(e.target.value) }))}
                        className="mt-1 form-input"
                      />
                      <p className="mt-1 text-sm text-gray-500">
                        Capture will stop after this duration or when facial recognition detects the speaker is no longer present.
                      </p>
                    </div>
                    
                    {/* Facial Recognition */}
                    <div className="relative flex items-start">
                      <div className="flex items-center h-5">
                        <input
                          id="enable_facial_recognition"
                          name="enable_facial_recognition"
                          type="checkbox"
                          checked={formData.enable_facial_recognition}
                          onChange={(e) => setFormData(prev => ({ ...prev, enable_facial_recognition: e.target.checked }))}
                          className="h-4 w-4 text-indigo-600 border-gray-300 rounded"
                        />
                      </div>
                      <div className="ml-3 text-sm">
                        <label htmlFor="enable_facial_recognition" className="font-medium text-gray-700">
                          Enable Facial Recognition
                        </label>
                        <p className="text-gray-500">
                          Automatically stop capturing when the speaker is no longer present.
                        </p>
                      </div>
                    </div>
                  </div>
                )}
                
                {/* Schedule toggle */}
                <div className="pt-4">
                  <div className="flex items-start">
                    <div className="flex items-center h-5">
                      <input
                        id="schedule"
                        name="schedule"
                        type="checkbox"
                        checked={scheduleCapture}
                        onChange={handleScheduleToggle}
                        className="h-4 w-4 text-primary focus:ring-primary border-gray-300 rounded"
                      />
                    </div>
                    <div className="ml-3 text-sm">
                      <label htmlFor="schedule" className="font-medium text-gray-700">
                        Schedule for later
                      </label>
                      <p className="text-gray-500">
                        Set a specific start and end time for the capture session
                      </p>
                    </div>
                  </div>
                </div>
                
                {/* Scheduled times */}
                {scheduleCapture && (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-2">
                    <div>
                      <label htmlFor="scheduled_start" className="block text-sm font-medium text-gray-700">
                        Scheduled Start Time *
                      </label>
                      <input
                        type="datetime-local"
                        id="scheduled_start"
                        name="scheduled_start"
                        value={formData.scheduled_start || ''}
                        onChange={handleInputChange}
                        min={getCurrentDateTime()}
                        className={`mt-1 form-input ${errors.scheduled_start ? 'border-red-300 focus:ring-red-500 focus:border-red-500' : ''}`}
                      />
                      {errors.scheduled_start && (
                        <p className="mt-1 text-sm text-red-600">{errors.scheduled_start}</p>
                      )}
                    </div>
                    
                    <div>
                      <label htmlFor="scheduled_end" className="block text-sm font-medium text-gray-700">
                        Scheduled End Time
                      </label>
                      <input
                        type="datetime-local"
                        id="scheduled_end"
                        name="scheduled_end"
                        value={formData.scheduled_end || ''}
                        onChange={handleInputChange}
                        min={formData.scheduled_start || getDefaultEndTime()}
                        className={`mt-1 form-input ${errors.scheduled_end ? 'border-red-300 focus:ring-red-500 focus:border-red-500' : ''}`}
                      />
                      {errors.scheduled_end ? (
                        <p className="mt-1 text-sm text-red-600">{errors.scheduled_end}</p>
                      ) : (
                        <p className="mt-1 text-sm text-gray-500">
                          Optional. If not set, capture will continue until manually stopped.
                        </p>
                      )}
                    </div>
                  </div>
                )}
              </div>
              
              {/* Important notes */}
              <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4">
                <div className="flex">
                  <div className="flex-shrink-0">
                    <svg className="h-5 w-5 text-yellow-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                    </svg>
                  </div>
                  <div className="ml-3">
                    <h3 className="text-sm font-medium text-yellow-800">Important Notes</h3>
                    <div className="mt-2 text-sm text-yellow-700">
                      <ul className="list-disc pl-5 space-y-1">
                        <li>Ensure the Parliament TV stream is active before starting capture</li>
                        <li>Capture sessions require sufficient storage space</li>
                        <li>Active captures will continue until manually stopped or scheduled end time</li>
                        <li>You can create multiple clips from a single capture session</li>
                      </ul>
                    </div>
                  </div>
                </div>
              </div>
              
              {/* Error message and active capture */}
              {errors.form && (
                <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative mb-4" role="alert">
                  <strong className="font-bold">Error: </strong>
                  <span className="block sm:inline whitespace-pre-line">{errors.form}</span>
                  
                  {activeCapture && (
                    <div className="mt-3">
                      <button 
                        type="button"
                        onClick={stopActiveCapture}
                        disabled={isStoppingCapture}
                        className="bg-red-500 hover:bg-red-700 text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline disabled:bg-red-300 disabled:cursor-not-allowed"
                      >
                        {isStoppingCapture ? 'Stopping Capture...' : 'Stop Active Capture'}
                      </button>
                    </div>
                  )}
                </div>
              )}
              
              {/* Submit button */}
              <div className="pt-4">
                <button
                  type="submit"
                  disabled={startCaptureMutation.isPending || (sourceUrlIncludes(formData.source_url, 'parliamentlive.tv') && !validationResult?.success)}
                  className="w-full btn-primary rounded-md px-4 py-2 text-center cursor-pointer inline-block disabled:opacity-50"
                >
                  {startCaptureMutation.isPending ? 'Starting Capture...' : scheduleCapture ? 'Schedule Capture' : 'Start Capture Now'}
                </button>
              </div>
            </div>
          </form>
        </div>
      </div>
    </MainLayout>
  );
};

export default withAuth(NewCapturePage, [UserRole.ADMIN, UserRole.MP, UserRole.STAFF]);
