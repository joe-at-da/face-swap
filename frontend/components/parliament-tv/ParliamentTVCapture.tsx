import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import axios from 'axios';
import { useAuth } from '../../contexts/AuthContext';
import { extractAudioForCapture } from '../../utils/extractAudio';
import CaptureStatusIndicator from './CaptureStatusIndicator';
import { CombinedStatus } from '../../utils/captureStatus';
import { toast } from 'react-toastify';

// API base URL
const API_BASE_URL = 'http://localhost:8000/api/v1';

// Define types for API responses
interface ExtractUrlResponse {
  video_url: string;
  audio_url?: string;
  event_id?: string;
  time_marker?: {
    seconds: number;
  };
  seconds: number;
  original_url?: string;
  direct_stream?: string;
}

interface TestStreamResponse {
  url: string;
  is_valid: boolean;
}

interface ParliamentTVCaptureProps {
  onSuccess?: (data: any) => void;
  onError?: (error: any) => void;
}

interface CaptureStatus {
  success: boolean;
  message: string;
  data?: any;
  error?: any;
}

interface ValidationResult {
  success: boolean;
  message: string;
  streamUrl?: string;
  originalUrl?: string; // Add originalUrl to store the original Parliament TV URL
  timeMarker?: number;
  error?: string;
}

// Define a type for our stop capture result
interface StopCaptureResult {
  success: boolean;
  message: string;
  data?: any;
}

const ParliamentTVCapture: React.FC<ParliamentTVCaptureProps> = ({ onSuccess, onError }) => {
  const router = useRouter();
  const { token } = useAuth();
  const [url, setUrl] = useState('https://parliamentlive.tv/event/index/c63e4bed-0da2-4d85-a742-e5d247a7aceb?in=12:23:30');
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [duration, setDuration] = useState(300); // Default 5 minutes
  const [enableFacialRecognition, setEnableFacialRecognition] = useState(true);
  const [isCapturing, setIsCapturing] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isValidating, setIsValidating] = useState(false);
  const [captureStatus, setCaptureStatus] = useState<CaptureStatus | null>(null);
  const [validationResult, setValidationResult] = useState<ValidationResult | null>(null);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [activeCapture, setActiveCapture] = useState<{id: number, started_by: string, started_at: string} | null>(null);
  const [isStoppingCapture, setIsStoppingCapture] = useState(false);
  const [currentCaptureId, setCurrentCaptureId] = useState<number | null>(null);
  const [showStatusIndicator, setShowStatusIndicator] = useState(false);
  const [timeMarker, setTimeMarker] = useState<number | null>(null);
  const [scheduledStart, setScheduledStart] = useState<string>('');
  const [scheduledEnd, setScheduledEnd] = useState<string>('');

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
          {
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${token}`
            }
          }
        );
        
        console.log('Active captures:', response.data);
        
        if (Array.isArray(response.data) && response.data.length > 0) {
          const activeCapture = response.data[0];
          const user = activeCapture.created_by;
          
          setError(`A capture session is already in progress. Started by ${user.name} at ${new Date(activeCapture.created_at).toLocaleString()}.`);
          
          setActiveCapture({
            id: activeCapture.id,
            started_by: user.name,
            started_at: activeCapture.created_at
          });
        }
      } catch (err) {
        console.error('Error checking for active captures:', err);
      }
    };
    
    checkActiveCaptures();
  }, [token]);
  
  const validateUrl = async () => {
    if (!url) {
      setValidationResult({
        success: false,
        message: 'Please enter a Parliament TV URL'
      });
      return;
    }
    
    setIsValidating(true);
    setValidationResult(null);
    
    try {
      // First, extract the URL components
      const extractResponse = await axios.post<ExtractUrlResponse>(
        `${API_BASE_URL}/parliament-tv/extract-url`,
        { url },
        getAuthHeaders()
      );
      
      console.log('Extract URL response:', extractResponse.data);
      
      const { video_url, time_marker } = extractResponse.data;
      
      if (!video_url) {
        setValidationResult({
          success: false,
          message: 'Could not extract video URL from the provided link'
        });
        return;
      }
      
      // If we have a time marker, update the state
      if (time_marker && time_marker.seconds) {
        setTimeMarker(time_marker.seconds);
      }
      
      // Now test if the stream is valid
      const params = {
        url: video_url
      };
      
      console.log('Sending test request with params:', params);
      
      const testResponse = await axios.get<TestStreamResponse>(
        `${API_BASE_URL}/parliament-tv/test-url`, 
        {
          params,
          headers: {
            Authorization: `Bearer ${token}`
          }
        }
      );
      
      console.log('Test URL response:', testResponse.data);
      
      if (testResponse.data.is_valid) {
        // If valid, update the validation result
        setValidationResult({
          success: true,
          message: 'URL is valid and ready for capture',
          streamUrl: video_url,
          originalUrl: url, // Store the original URL with time marker
          timeMarker: time_marker?.seconds
        });
        
        // If we don't have a title yet, try to generate one from the URL
        if (!title) {
          // Extract a title from the URL if possible
          try {
            const urlObj = new URL(url);
            const eventId = urlObj.pathname.split('/').pop() || '';
            if (eventId) {
              setTitle(`Parliament TV Capture - ${eventId}`);
            }
          } catch (e) {
            console.error('Error parsing URL for title:', e);
          }
        }
        
        // Set default scheduled start/end times if not already set
        if (!scheduledStart) {
          const now = new Date();
          setScheduledStart(formatDateForInput(now));
          
          // Default end time is 30 minutes from now
          const endTime = new Date(now.getTime() + 30 * 60 * 1000);
          setScheduledEnd(formatDateForInput(endTime));
        }
      } else {
        setValidationResult({
          success: false,
          message: 'The provided URL does not point to a valid stream'
        });
      }
    } catch (error: any) {
      console.error('Error validating URL:', error);
      
      // Check for specific error messages
      const errorMessage = error.response?.data?.detail || error.message || 'Error validating URL';
      let userMessage = 'Error validating URL. Please check the format and try again.';
      
      // Check if it's a yt-dlp not found error
      if (errorMessage.includes && errorMessage.includes('yt-dlp not found')) {
        userMessage = 'The server is missing yt-dlp, which is required for extracting Parliament TV streams. Please contact the administrator to install it.';
      }
      
      setValidationResult({
        success: false,
        message: userMessage,
        error: errorMessage
      });
    } finally {
      setIsValidating(false);
    }
  };
  
  // Format dates for datetime-local input
  const formatDateForInput = (date: Date) => {
    return date.toISOString().slice(0, 16);
  };
  
  // Improved stopActiveCapture function with timeouts and better error handling
  const stopActiveCapture = async () => {
    if (!activeCapture) return;
    
    setIsStoppingCapture(true);
    
    // Create a timeout promise that will resolve after 10 seconds
    const timeoutPromise = new Promise<StopCaptureResult>((resolve) => {
      setTimeout(() => {
        resolve({
          success: true,
          message: 'Capture stop request sent. The process may still be stopping in the background.'
        });
      }, 10000); // 10 second timeout
    });
    
    try {
      const authHeaders = getAuthHeaders();
      const token = authHeaders.headers.Authorization.split(' ')[1];
      
      // Create the API request promise
      const apiRequestPromise = axios.post(
        `${API_BASE_URL}/capture/${activeCapture.id}/stop`,
        {},
        {
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
          },
          timeout: 8000 // 8 second timeout for the axios request itself
        }
      );
      
      // Race between the API request and the timeout
      const result = await Promise.race([
        apiRequestPromise.then(response => ({
          success: true,
          message: 'Capture stopped successfully!',
          data: response.data
        })),
        timeoutPromise
      ]);
      
      console.log('Stop capture result:', result);
      
      // Clear the error and active capture
      setError('');
      setActiveCapture(null);
      setSuccess(true);
      
      // Show success message
      setCaptureStatus({
        success: true,
        message: result.message,
        data: result.data || { id: activeCapture.id }
      });
      
      // Continue the API request in the background if it was the timeout that resolved
      if (result.message === 'Capture stop request sent. The process may still be stopping in the background.') {
        toast.info('Stopping capture in the background. The UI will remain responsive.');
        
        // Let the API request continue in the background
        apiRequestPromise.then(() => {
          console.log('Background capture stop completed successfully');
        }).catch(err => {
          console.error('Background capture stop failed:', err);
        });
      }
    } catch (err: any) {
      console.error('Error stopping capture:', err);
      
      let errorMessage = 'Failed to stop capture. Please try again.';
      
      if (err.response) {
        console.error('Error response data:', err.response.data);
        errorMessage = err.response.data?.detail || errorMessage;
      } else if (err.code === 'ECONNABORTED') {
        errorMessage = 'Request timed out. The capture may still be stopping in the background.';
      }
      
      setError(errorMessage);
    } finally {
      setIsStoppingCapture(false);
    }
  };
  
  const startCapture = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validationResult || !validationResult.success) {
      setError('Please validate the URL before starting capture');
      return;
    }
    
    setIsSubmitting(true);
    setError('');
    
    try {
      // Use the original URL with time marker instead of the extracted direct stream URL
      const payload: Record<string, any> = {
        url: validationResult.originalUrl || validationResult.streamUrl, // Prefer original URL
        title,
        description,
        duration,
        enable_facial_recognition: enableFacialRecognition,
        scheduled_start: scheduledStart ? new Date(scheduledStart).toISOString() : null,
        scheduled_end: scheduledEnd ? new Date(scheduledEnd).toISOString() : null,
      };
      
      // If we have a time marker, add it to the payload
      if (timeMarker !== null) {
        payload.time_marker = timeMarker;
      }
      
      console.log('Starting capture with payload:', payload);
      
      // Define the expected response type
      interface CaptureResponse {
        id: number;
        status: string;
        [key: string]: any; // Allow for other properties
      }
      
      const response = await axios.post<CaptureResponse>(
        `${API_BASE_URL}/parliament-tv`,
        payload,
        getAuthHeaders()
      );
      
      console.log('Capture started successfully:', response.data);
      
      // Update state to show success
      setSuccess(true);
      
      // Reset form
      setUrl('');
      setTitle('');
      setDescription('');
      setDuration(300);
      setEnableFacialRecognition(true);
      setScheduledStart('');
      setScheduledEnd('');
      setTimeMarker(null);
      
      // Show success message
      setCaptureStatus({
        success: true,
        message: 'Capture started successfully!',
        data: response.data
      });
      
      // Store the capture ID for status checking
      if (response.data && response.data.id) {
        setCurrentCaptureId(response.data.id);
        setShowStatusIndicator(true);
      }
      
      // Redirect to the captures page after a short delay
      setTimeout(() => {
        router.push('/capture');
      }, 3000);
      
      // Call onSuccess callback if provided
      if (onSuccess) {
        onSuccess(response.data);
      }
    } catch (error: any) {
      console.error('Error starting capture:', error);
      
      let errorMessage = 'Failed to start capture. Please try again.';
      
      if (error.response && error.response.data) {
        console.error('Error response data:', error.response.data);
        
        if (error.response.data.detail) {
          errorMessage = typeof error.response.data.detail === 'string'
            ? error.response.data.detail
            : JSON.stringify(error.response.data.detail);
        }
      }
      
      setError(errorMessage);
      
      // Call onError callback if provided
      if (onError) {
        onError(error);
      }
    } finally {
      setIsSubmitting(false);
    }
  };
  
  // Handle when both video and audio are ready
  const handleCaptureComplete = (status: CombinedStatus) => {
    console.log('Capture complete:', status);
    // Additional handling can be added here
  };
  
  return (
    <div className="bg-white shadow overflow-hidden sm:rounded-lg p-6">
      <h2 className="text-2xl font-bold mb-6">Parliament TV Capture</h2>
      
      {showStatusIndicator && currentCaptureId && (
        <div className="mb-6">
          <CaptureStatusIndicator 
            captureId={currentCaptureId} 
            onComplete={handleCaptureComplete}
          />
        </div>
      )}
      
      <form onSubmit={startCapture} className="space-y-6">
        <div>
          <label htmlFor="url" className="block text-sm font-medium text-gray-700">
            Parliament TV URL
          </label>
          <div className="mt-1 flex rounded-md shadow-sm">
            <input
              type="text"
              name="url"
              id="url"
              className="flex-1 min-w-0 block w-full px-3 py-2 rounded-md border border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
              placeholder="https://parliamentlive.tv/event/index/..."
              value={url}
              onChange={(e) => setUrl(e.target.value)}
            />
            <button
              type="button"
              onClick={validateUrl}
              disabled={isValidating || !url}
              className="ml-3 inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:bg-gray-400 disabled:cursor-not-allowed"
            >
              {isValidating ? 'Validating...' : 'Validate URL'}
            </button>
          </div>
          
          {validationResult && (
            <div className={`mt-2 text-sm ${validationResult.success ? 'text-green-600' : 'text-red-600'}`}>
              {validationResult.message}
            </div>
          )}
          
          <p className="mt-2 text-xs text-gray-500">
            Enter a URL from parliamentlive.tv, e.g. https://parliamentlive.tv/event/index/c63e4bed-0da2-4d85-a742-e5d247a7aceb
          </p>
        </div>
        
        <div>
          <label htmlFor="title" className="block text-sm font-medium text-gray-700">
            Title
          </label>
          <div className="mt-1">
            <input
              type="text"
              name="title"
              id="title"
              className="block w-full px-3 py-2 rounded-md border border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
              placeholder="Capture Title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
          </div>
        </div>
        
        <div>
          <label htmlFor="description" className="block text-sm font-medium text-gray-700">
            Description
          </label>
          <div className="mt-1">
            <textarea
              name="description"
              id="description"
              rows={3}
              className="block w-full px-3 py-2 rounded-md border border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
              placeholder="Capture Description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>
        </div>
        
        <div>
          <label htmlFor="duration" className="block text-sm font-medium text-gray-700">
            Duration (seconds)
          </label>
          <div className="mt-1">
            <input
              type="number"
              name="duration"
              id="duration"
              min="10"
              max="3600"
              className="block w-full px-3 py-2 rounded-md border border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
              value={duration}
              onChange={(e) => setDuration(parseInt(e.target.value))}
            />
          </div>
          <p className="mt-2 text-xs text-gray-500">
            Maximum duration: 3600 seconds (1 hour)
          </p>
        </div>
        
        <div>
          <label htmlFor="scheduledStart" className="block text-sm font-medium text-gray-700">
            Scheduled Start (optional)
          </label>
          <div className="mt-1">
            <input
              type="datetime-local"
              name="scheduledStart"
              id="scheduledStart"
              className="block w-full px-3 py-2 rounded-md border border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
              value={scheduledStart}
              onChange={(e) => setScheduledStart(e.target.value)}
            />
          </div>
        </div>
        
        <div>
          <label htmlFor="scheduledEnd" className="block text-sm font-medium text-gray-700">
            Scheduled End (optional)
          </label>
          <div className="mt-1">
            <input
              type="datetime-local"
              name="scheduledEnd"
              id="scheduledEnd"
              className="block w-full px-3 py-2 rounded-md border border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
              value={scheduledEnd}
              onChange={(e) => setScheduledEnd(e.target.value)}
            />
          </div>
        </div>
        
        <div className="relative flex items-start">
          <div className="flex items-center h-5">
            <input
              id="enableFacialRecognition"
              name="enableFacialRecognition"
              type="checkbox"
              className="focus:ring-indigo-500 h-4 w-4 text-indigo-600 border-gray-300 rounded"
              checked={enableFacialRecognition}
              onChange={(e) => setEnableFacialRecognition(e.target.checked)}
            />
          </div>
          <div className="ml-3 text-sm">
            <label htmlFor="enableFacialRecognition" className="font-medium text-gray-700">
              Enable Facial Recognition
            </label>
            <p className="text-gray-500">
              Automatically stop capturing when the speaker is no longer present.
            </p>
          </div>
        </div>
        
        <div className="pt-4">
          <button
            type="submit"
            disabled={isCapturing || (validationResult && !validationResult.success) || isSubmitting}
            className="w-full inline-flex justify-center py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:bg-gray-400 disabled:cursor-not-allowed"
          >
            {isSubmitting ? 'Starting Capture...' : 'Start Capture'}
          </button>
        </div>
      </form>
      
      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative mb-4" role="alert">
          <strong className="font-bold">Error: </strong>
          <span className="block sm:inline whitespace-pre-line">{error}</span>
          
          {activeCapture && (
            <div className="mt-3">
              <button 
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
      
      {captureStatus && (
        <div className={`mt-6 p-4 rounded-md ${captureStatus.success ? 'bg-green-50' : 'bg-red-50'}`}>
          <div className="flex">
            <div className="flex-shrink-0">
              {captureStatus.success ? (
                <svg className="h-5 w-5 text-green-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
              ) : (
                <svg className="h-5 w-5 text-red-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
              )}
            </div>
            <div className="ml-3">
              <h3 className={`text-sm font-medium ${captureStatus.success ? 'text-green-800' : 'text-red-800'}`}>
                {captureStatus.message}
              </h3>
              {captureStatus.success && captureStatus.data && (
                <div className="mt-2 text-sm text-green-700">
                  <p>Capture ID: {captureStatus.data.id}</p>
                  <p>Status: {captureStatus.data.status}</p>
                  <p>Redirecting to captures page...</p>
                </div>
              )}
              {!captureStatus.success && captureStatus.error && (
                <div className="mt-2 text-sm text-red-700">
                  {captureStatus.error.detail && (
                    <p>
                      {typeof captureStatus.error.detail === 'string'
                        ? captureStatus.error.detail
                        : JSON.stringify(captureStatus.error.detail)}
                    </p>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ParliamentTVCapture;
