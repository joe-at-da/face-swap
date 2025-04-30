import React, { useState } from 'react';
import { useRouter } from 'next/router';
import axios from 'axios';

interface ParliamentTVCaptureProps {
  onSuccess?: (data: any) => void;
  onError?: (error: any) => void;
}

const ParliamentTVCapture: React.FC<ParliamentTVCaptureProps> = ({ onSuccess, onError }) => {
  const router = useRouter();
  const [url, setUrl] = useState('');
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [duration, setDuration] = useState(300);
  const [enableFacialRecognition, setEnableFacialRecognition] = useState(true);
  const [isCapturing, setIsCapturing] = useState(false);
  const [captureStatus, setCaptureStatus] = useState<any>(null);
  const [isValidating, setIsValidating] = useState(false);
  const [validationResult, setValidationResult] = useState<any>(null);

  const validateUrl = async () => {
    if (!url) return;

    setIsValidating(true);
    setValidationResult(null);

    try {
      // First extract the stream URL
      const extractResponse = await axios.get('/api/v1/parliament-tv/extract-url', {
        params: { url }
      });

      if (extractResponse.data?.direct_stream) {
        // Then test if the stream URL is valid
        const testResponse = await axios.get('/api/v1/parliament-tv/test-url', {
          params: { url: extractResponse.data.direct_stream }
        });

        setValidationResult({
          success: testResponse.data?.is_valid,
          message: testResponse.data?.is_valid 
            ? 'Stream URL is valid and ready for capture.' 
            : 'Stream URL was extracted but could not be validated. Capture may still work.',
          streamUrl: extractResponse.data.direct_stream,
          timeMarker: extractResponse.data.time_marker?.seconds
        });
      } else {
        setValidationResult({
          success: false,
          message: 'Could not extract stream URL from Parliament TV page.'
        });
      }
    } catch (error) {
      console.error('Error validating URL:', error);
      setValidationResult({
        success: false,
        message: 'Error validating URL. Please check the format and try again.'
      });
    } finally {
      setIsValidating(false);
    }
  };

  const startCapture = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!url || !title) return;
    
    setIsCapturing(true);
    setCaptureStatus(null);
    
    try {
      const response = await axios.post('/api/v1/parliament-tv', {
        url,
        title,
        description,
        duration,
        enable_facial_recognition: enableFacialRecognition
      });
      
      setCaptureStatus({
        success: true,
        message: 'Capture started successfully!',
        data: response.data
      });
      
      if (onSuccess) {
        onSuccess(response.data);
      }
      
      // Redirect to the captures page after a short delay
      setTimeout(() => {
        router.push('/captures');
      }, 2000);
    } catch (error: any) {
      console.error('Error starting capture:', error);
      
      setCaptureStatus({
        success: false,
        message: error.response?.data?.detail?.message || 'Error starting capture.',
        error: error.response?.data || error.message
      });
      
      if (onError) {
        onError(error);
      }
    } finally {
      setIsCapturing(false);
    }
  };
  
  return (
    <div className="bg-white shadow-md rounded-lg p-6 max-w-2xl mx-auto">
      <h2 className="text-2xl font-bold mb-6">Parliament TV Capture</h2>
      
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
        
        <div>
          <label htmlFor="duration" className="block text-sm font-medium text-gray-700 mb-1">
            Maximum Duration (seconds)
          </label>
          <input
            type="number"
            id="duration"
            value={duration}
            onChange={(e) => setDuration(parseInt(e.target.value))}
            min={10}
            max={3600}
            className="shadow-sm focus:ring-indigo-500 focus:border-indigo-500 block w-full sm:text-sm border-gray-300 rounded-md"
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
            disabled={isCapturing || (validationResult && !validationResult.success)}
            className="w-full inline-flex justify-center py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:bg-gray-400 disabled:cursor-not-allowed"
          >
            {isCapturing ? 'Starting Capture...' : 'Start Capture'}
          </button>
        </div>
      </form>
      
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
