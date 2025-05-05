import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import axios from 'axios';
import { useAuth } from '../../contexts/AuthContext';
import { extractAudioForCapture } from '../../utils/extractAudio';
import CaptureStatusIndicator from './CaptureStatusIndicator';
import { CombinedStatus } from '../../utils/captureStatus';

// API base URL
const API_BASE_URL = 'http://localhost:8000/api/v1';

// Define types for API responses
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
  timeMarker?: number;
  error?: string;
}

const ParliamentTVCapture: React.FC<ParliamentTVCaptureProps> = ({ onSuccess, onError }) => {
  const router = useRouter();
  const { token } = useAuth();
  const [url, setUrl] = useState('');
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
        console.error('Error checking active captures:', err);
        // Don't show error to user, just log it
      }
    };
    
    checkActiveCaptures();
  }, [token]);

  const validateUrl = async () => {
    if (!url) return;

    setIsValidating(true);
    setValidationResult(null);
    
    // Validate that the URL is a Parliament TV URL
    const validDomains = ["parliamentlive.tv", "parliament.tv"];
    let isValidDomain = false;
    
    for (const domain of validDomains) {
      if (url.includes(domain)) {
        isValidDomain = true;
        break;
      }
    }
    
    if (!isValidDomain) {
      setValidationResult({
        success: false,
        message: 'Invalid URL. Please enter a valid Parliament TV URL.',
        error: 'URL must be from parliamentlive.tv or parliament.tv'
      });
      setIsValidating(false);
      return;
    }

    try {
      // First extract the stream URL - direct API call with detailed error logging
      console.log(`Calling extract-url API with URL: ${url}`);
      console.log(`Full API URL: ${API_BASE_URL}/parliament-tv/extract-url?url=${encodeURIComponent(url)}`);
      console.log('Auth headers:', getAuthHeaders());
      
      const extractResponse = await axios.get<ExtractUrlResponse>(
        `${API_BASE_URL}/parliament-tv/extract-url`, 
        {
          params: { url },
          headers: {
            Authorization: `Bearer ${token}`
          }
        }
      );
      
      console.log('Extract response status:', extractResponse.status);
      console.log('Extract response data:', extractResponse.data);

      if (extractResponse.data?.direct_stream) {
      // Then test if the stream URL is valid
      console.log('Extract URL response:', extractResponse.data);
      
      let videoUrl = '';
      let audioUrl = '';
      let params = {};
      
      // Handle both string and object formats for direct_stream
      if (typeof extractResponse.data.direct_stream === 'string') {
        // If it's a string, use it as the video URL
        videoUrl = extractResponse.data.direct_stream;
        console.log(`Testing stream URL (string format): ${videoUrl}`);
        params = { url: videoUrl };
      } else if (typeof extractResponse.data.direct_stream === 'object') {
        // If it's an object with video_url and audio_url, use those
        videoUrl = extractResponse.data.direct_stream.video_url;
        audioUrl = extractResponse.data.direct_stream.audio_url || '';
        console.log(`Testing stream URL (object format):\nVideo URL: ${videoUrl}\nAudio URL: ${audioUrl}`);
        params = { video_url: videoUrl };
        if (audioUrl) {
          params = { ...params, audio_url: audioUrl };
        }
      }
      
      if (!videoUrl) {
        setValidationResult({
          success: false,
          message: 'Could not extract a valid stream URL from Parliament TV page.'
        });
        return;
      }
      
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
      
      console.log('Test response status:', testResponse.status);
      console.log('Test response data:', testResponse.data);

      // Get the time marker from the response
      const extractedTimeMarker = extractResponse.data.time_marker?.seconds || 0;
      setTimeMarker(extractedTimeMarker);
      
      // Calculate scheduled start and end times based on the time marker
      const startDate = new Date();
      if (extractedTimeMarker > 0) {
        // If we have a time marker, set the start time to that point in the video
        startDate.setSeconds(startDate.getSeconds() - extractedTimeMarker);
      }
      
      // Calculate end time (10 minutes from now by default)
      const endDate = new Date();
      endDate.setMinutes(endDate.getMinutes() + 10);
      
      // Format dates for datetime-local input
      const formatDateForInput = (date: Date) => {
        return date.toISOString().slice(0, 16);
      };
      
      setScheduledStart(formatDateForInput(startDate));
      setScheduledEnd(formatDateForInput(endDate));
      
      setValidationResult({
        success: testResponse.data?.is_valid,
        message: testResponse.data?.is_valid 
          ? `Stream URL is valid and ready for capture. Time marker: ${extractedTimeMarker} seconds` 
          : 'Stream URL was extracted but could not be validated. Capture may still work.',
        streamUrl: videoUrl,
        timeMarker: extractedTimeMarker
      });
      } else {
        setValidationResult({
          success: false,
          message: 'Could not extract stream URL from Parliament TV page.'
        });
      }
    } catch (error: any) {
      console.error('Error validating URL:', error);
      console.error('Error response:', error.response);
      console.error('Error request:', error.request);
      console.error('Error config:', error.config);
      
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

  const stopActiveCapture = async () => {
    if (!activeCapture) return;
    
    setIsStoppingCapture(true);
    try {
      const authHeaders = getAuthHeaders();
      const token = authHeaders.headers.Authorization.split(' ')[1];
      
      const response = await axios.post(
        `${API_BASE_URL}/parliament-tv/${activeCapture.id}/stop`,
        {},
        {
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
          }
        }
      );
      
      console.log('Capture stopped successfully:', response.data);
      
      // Clear the error and active capture
      setError('');
      setActiveCapture(null);
      setSuccess(true);
      
      // Show success message
      setCaptureStatus({
        success: true,
        message: 'Capture stopped successfully!',
        data: response.data
      });
      
    } catch (err: any) {
      console.error('Error stopping capture:', err);
      
      let errorMessage = 'Failed to stop capture. Please try again.';
      
      if (err.response) {
        console.error('Error response data:', err.response.data);
        errorMessage = err.response.data?.detail || errorMessage;
      }
      
      setError(errorMessage);
    } finally {
      setIsStoppingCapture(false);
    }
  };
  
  const startCapture = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError('');

    try {
      // First, extract the direct stream URL to get the latest format
      const authHeaders = getAuthHeaders();
      const authToken = authHeaders.headers.Authorization.split(' ')[1];
      
      // Extract the direct stream URL
      const extractResponse = await axios.get<ExtractUrlResponse>(
        `${API_BASE_URL}/parliament-tv/extract-url`, 
        {
          params: { url },
          headers: {
            Authorization: `Bearer ${authToken}`
          }
        }
      );
        
      console.log('Extract response for capture:', extractResponse.data);
      
      // Prepare the capture request with the latest stream URL format
      let captureData: any = {
        url,
        title,
        description,
        duration,
        enable_facial_recognition: enableFacialRecognition,
        scheduled_start: scheduledStart ? new Date(scheduledStart).toISOString() : null,
        scheduled_end: scheduledEnd ? new Date(scheduledEnd).toISOString() : null,
        // Pass the time marker to the backend
        time_marker_seconds: timeMarker || 0
      };
      
      console.log(`Including time marker in capture request: ${timeMarker} seconds`);
      
      // Add the direct_stream data if available
      if (extractResponse.data?.direct_stream) {
        captureData.direct_stream = extractResponse.data.direct_stream;
      }
      
      console.log('Starting capture with data:', captureData);

      const response = await axios.post(
        `${API_BASE_URL}/parliament-tv`, 
        captureData,
        {
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
          }
        }
      );

      console.log('Capture started successfully:', response.data);
      
      setIsSubmitting(false);
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
      
      // Extract audio for this capture and show status indicator
      if (response.data && typeof response.data === 'object' && 'id' in response.data) {
        const captureId = response.data.id as number;
        console.log('Starting audio extraction for capture ID:', captureId);
        
        // Set the current capture ID and show the status indicator
        setCurrentCaptureId(captureId);
        setShowStatusIndicator(true);
        
        // Start audio extraction
        extractAudioForCapture(captureId)
          .then(success => {
            console.log('Audio extraction initiated:', success ? 'success' : 'failed');
          })
          .catch(err => {
            console.error('Error initiating audio extraction:', err);
          });
      }
      
      // Call onSuccess callback if provided
      if (onSuccess) {
        onSuccess(response.data);
      }
      
    } catch (err: any) {
      console.error('Error starting capture:', err);
      setIsSubmitting(false);
      
      let errorMessage = 'Failed to start capture. Please try again.';
      let errorDetails = '';
      
      if (err.response) {
        // The request was made and the server responded with a status code
        // that falls out of the range of 2xx
        console.error('Error response data:', err.response.data);
        console.error('Error response status:', err.response.status);
        console.error('Error response headers:', err.response.headers);
        
        // Handle specific error status codes
        if (err.response.status === 409) {
          console.log('Full conflict response:', JSON.stringify(err.response.data));
          
          // Try to extract the conflict data from different possible structures
          let conflictData;
          if (typeof err.response.data.detail === 'object') {
            conflictData = err.response.data.detail;
          } else if (typeof err.response.data === 'object') {
            conflictData = err.response.data;
          } else {
            conflictData = {};
          }
          
          console.log('Conflict data extracted:', JSON.stringify(conflictData));
          
          errorMessage = conflictData.message || 'A capture session is already in progress';
          
          // Check for capture ID in different possible locations
          const captureId = conflictData.capture_id || conflictData.id;
          const startedBy = conflictData.started_by || conflictData.user || 'another user';
          const startedAt = conflictData.started_at || conflictData.created_at;
          
          if (captureId && startedAt) {
            const startTime = new Date(startedAt).toLocaleString();
            errorDetails = `Started by ${startedBy} at ${startTime}`;
            
            // Store active capture info for the stop button
            setActiveCapture({
              id: captureId,
              started_by: startedBy,
              started_at: startedAt
            });
            
            // Automatically check for active captures to get more details
            try {
              axios.get<any[]>(
                `${API_BASE_URL}/parliament-tv?status=active`,
                {
                  headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                  }
                }
              ).then(response => {
                if (Array.isArray(response.data) && response.data.length > 0) {
                  const activeCapture = response.data[0];
                  const user = activeCapture.created_by;
                  
                  setActiveCapture({
                    id: activeCapture.id,
                    started_by: user.name,
                    started_at: activeCapture.created_at
                  });
                }
              }).catch(e => console.error('Failed to get active captures:', e));
            } catch (e) {
              console.error('Error in secondary active capture check:', e);
            }
          } else {
            console.log('Missing required conflict data fields. Available fields:', Object.keys(conflictData).join(', '));
          }
        } else {
          errorMessage = err.response.data?.detail?.message || err.response.data?.detail || errorMessage;
        }
      } else if (err.request) {
        // The request was made but no response was received
        console.error('Error request:', err.request);
        errorMessage = 'No response received from server. Please check your connection.';
      } else {
        // Something happened in setting up the request that triggered an Error
        console.error('Error message:', err.message);
        errorMessage = err.message || errorMessage;
      }
      
      setError(errorMessage + (errorDetails ? `\n${errorDetails}` : ''));
      
      // Call onError callback if provided
      if (onError) {
        onError(err);
      }
    }
  };

  // Handle when both video and audio are ready
  const handleCaptureComplete = (status: CombinedStatus) => {
    console.log('Capture complete!', status);
    // You could show a notification or redirect to the capture page
  };

  return (
    <div className="bg-white shadow-md rounded-lg p-6 max-w-2xl mx-auto">
      <h2 className="text-2xl font-bold mb-6">Parliament TV Capture</h2>
      
      {/* Show status indicator when a capture is in progress */}
      {showStatusIndicator && currentCaptureId && (
        <div className="mb-6">
          <CaptureStatusIndicator 
            captureId={currentCaptureId} 
            onComplete={handleCaptureComplete} 
          />
          <button
            onClick={() => setShowStatusIndicator(false)}
            className="mt-2 text-sm text-gray-500 hover:text-gray-700"
          >
            Hide Status
          </button>
        </div>
      )}
      
      <form onSubmit={startCapture} className="space-y-4">
        <div>
          <label htmlFor="url" className="block text-sm font-medium text-gray-700 mb-1">
            Parliament TV URL
          </label>
          <div className="flex">
            <input
              type="text"
              id="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://parliamentlive.tv/event/index/EVENT_ID?in=HH:MM:SS"
              className="flex-grow shadow-sm focus:ring-indigo-500 focus:border-indigo-500 block w-full sm:text-sm border-gray-300 rounded-md"
              required
            />
            <button
              type="button"
              onClick={validateUrl}
              disabled={isValidating || !url}
              className="ml-2 inline-flex items-center px-3 py-2 border border-transparent text-sm leading-4 font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
            >
              {isValidating ? 'Validating...' : 'Validate'}
            </button>
          </div>
          
          {validationResult && (
            <div className={`mt-2 text-sm ${validationResult.success ? 'text-green-600' : 'text-red-600'}`}>
              {validationResult.message}
              {validationResult.timeMarker && (
                <p className="mt-1">Time marker detected: {validationResult.timeMarker} seconds</p>
              )}
              {validationResult.error && !validationResult.success && (
                <div className="mt-2 p-2 bg-red-50 rounded text-xs">
                  <p className="font-semibold">Technical details:</p>
                  <p className="font-mono">{validationResult.error}</p>
                </div>
              )}
            </div>
          )}
        </div>
        
        <div>
          <label htmlFor="title" className="block text-sm font-medium text-gray-700 mb-1">
            Title
          </label>
          <input
            type="text"
            id="title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Enter a title for this capture"
            className="shadow-sm focus:ring-indigo-500 focus:border-indigo-500 block w-full sm:text-sm border-gray-300 rounded-md"
            required
          />
        </div>
        
        <div>
          <label htmlFor="description" className="block text-sm font-medium text-gray-700 mb-1">
            Description (Optional)
          </label>
          <textarea
            id="description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Enter a description"
            rows={3}
            className="shadow-sm focus:ring-indigo-500 focus:border-indigo-500 block w-full sm:text-sm border-gray-300 rounded-md"
          />
        </div>
        
        <div className="mb-4">
          <label htmlFor="scheduledStart" className="block text-sm font-medium text-gray-700">Scheduled Start Time</label>
          <input
            type="datetime-local"
            id="scheduledStart"
            name="scheduledStart"
            value={scheduledStart}
            onChange={(e) => setScheduledStart(e.target.value)}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
          />
          <p className="mt-1 text-sm text-gray-500">
            {timeMarker && timeMarker > 0 ? 
              `Automatically set to ${timeMarker} seconds into the stream based on the URL` : 
              'Start time for the capture'}
          </p>
        </div>

        <div className="mb-4">
          <label htmlFor="scheduledEnd" className="block text-sm font-medium text-gray-700">Scheduled End Time</label>
          <input
            type="datetime-local"
            id="scheduledEnd"
            name="scheduledEnd"
            value={scheduledEnd}
            onChange={(e) => setScheduledEnd(e.target.value)}
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
          />
          <p className="mt-1 text-sm text-gray-500">End time for the capture (defaults to 10 minutes from now)</p>
        </div>

        <div className="mb-4">
          <label htmlFor="duration" className="block text-sm font-medium text-gray-700">Max Duration (seconds)</label>
          <input
            type="number"
            id="duration"
            name="duration"
            value={duration}
            onChange={(e) => setDuration(parseInt(e.target.value) || 300)}
            min="60"
            max="3600"
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
            required
          />
          <p className="mt-1 text-sm text-gray-500">
            Capture will stop after this duration or when facial recognition detects the speaker is no longer present.
          </p>
        </div>
        
        <div className="flex items-start">
          <div className="flex items-center h-5">
            <input
              id="enableFacialRecognition"
              type="checkbox"
              checked={enableFacialRecognition}
              onChange={(e) => setEnableFacialRecognition(e.target.checked)}
              className="focus:ring-indigo-500 h-4 w-4 text-indigo-600 border-gray-300 rounded"
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
