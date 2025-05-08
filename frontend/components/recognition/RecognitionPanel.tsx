import React, { useState, useEffect } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { api } from '../../utils/api';
import RecognitionProgress from './RecognitionProgress';

interface RecognitionPanelProps {
  captureId: number;
  videoElement: HTMLVideoElement | null;
}

interface SpeakerResult {
  name: string;
  confidence: number;
  start_time: number;
  end_time: number;
  duration: number;
}

interface CaptureData {
  id: number;
  recognition_status: string;
  facial_recognition_path: string | null;
  speaker_identification_path: string | null;
  speaker_identification_results: string | null;
  recognition_completed_at: string | null;
}

const RecognitionPanel: React.FC<RecognitionPanelProps> = ({ captureId, videoElement }) => {
  const [isProcessing, setIsProcessing] = useState(false);
  const [showProgress, setShowProgress] = useState(false);

  console.log('RecognitionPanel render state:', { isProcessing, showProgress });
  
  // Process recognition mutation
  const processMutation = useMutation({
    mutationFn: async () => {
      try {
        console.log('Starting recognition processing for capture ID:', captureId);
        
        // Set processing state
        setIsProcessing(true);
        setShowProgress(true);
        
        // Determine API URL based on environment
        const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        console.log('Using API URL for recognition:', apiBaseUrl);
        
        // Get auth token
        const token = localStorage.getItem('token');
        console.log('Auth token available:', !!token);
        
        // First try using the API client
        try {
          console.log('Making request to combined recognition endpoint');
          const response = await api.post('/recognition/combined-recognition', {
            video_id: captureId
          });
          
          console.log('Recognition processing response:', response);
          return response;
        } catch (apiError) {
          console.error('API client error, trying direct fetch:', apiError);
          
          // Fallback to direct fetch if API client fails
          const directUrl = `${apiBaseUrl}/api/v1/recognition/combined-recognition`;
          console.log('Trying direct fetch to:', directUrl);
          
          const authToken = localStorage.getItem('token') || sessionStorage.getItem('token');
          const directResponse = await fetch(directUrl, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': authToken ? `Bearer ${authToken}` : ''
            },
            body: JSON.stringify({
              video_id: captureId
            })
          });
          
          if (!directResponse.ok) {
            const errorText = await directResponse.text();
            console.error(`HTTP error! status: ${directResponse.status}, body: ${errorText}`);
            throw new Error(`HTTP error! status: ${directResponse.status}`);
          }
          
          const data = await directResponse.json();
          console.log('Direct fetch response:', data);
          return data;
        }
      } catch (error) {
        console.error('Error in recognition processing:', error);
        throw error;
      }
    },
    onSuccess: () => {
      console.log('Recognition processing started successfully');
      // We'll keep the processing state true until the progress component signals completion
    },
    onError: (error: any) => {
      console.error('Error processing recognition:', error);
      setIsProcessing(false);
      // Show error message
    }
  });

  // Fetch capture data to get recognition status
  const { data: capture, isLoading, isError, error, refetch } = useQuery<CaptureData>({
    queryKey: ['captureRecognition', captureId],
    queryFn: async () => {
      return await api.get(`/capture/${captureId}`);
    },
    enabled: !!captureId
  });
  
  // Check if recognition is already in progress when component mounts
  useEffect(() => {
    console.log('Capture data changed:', capture);
    if (capture?.recognition_status === 'processing') {
      console.log('Recognition is already in progress, updating state');
      setIsProcessing(true);
      setShowProgress(true);
    } else if (capture?.recognition_status === 'completed') {
      console.log('Recognition is completed');
      setIsProcessing(false);
      setShowProgress(true); // Still show progress to display completion
    } else if (capture?.recognition_status === 'error') {
      console.log('Recognition has error');
      setIsProcessing(false);
      setShowProgress(true); // Still show progress to display error
    } else if (capture?.recognition_status) {
      console.log('Recognition status:', capture.recognition_status);
    }
    
    // Log additional debug info
    console.log('RecognitionPanel component state:', {
      captureId,
      recognitionStatus: capture?.recognition_status,
      isProcessing,
      showProgress,
      isMutationLoading: processMutation.isPending,
      hasRecognitionResults: !!(capture?.facial_recognition_path || capture?.speaker_identification_path)
    });
  }, [capture, captureId, isProcessing, showProgress, processMutation.isPending]);

  // Handle button click to process recognition
  const handleProcessRecognition = () => {
    console.log('Starting recognition process');
    processMutation.mutate();
  };
  
  const handleProgressComplete = () => {
    console.log('Progress component signaled completion');
    setIsProcessing(false);
    
    // Refetch capture data to get updated recognition results
    refetch().then(() => {
      console.log('Refetched capture data after completion');
      // Keep showing the progress component so users can see the final status
      // Don't hide it automatically
    }).catch((error: any) => {
      console.error('Error refetching capture data:', error);
      // Still keep progress visible even if refetch fails
    });
  };
  
  const jumpToTimestamp = (seconds: number) => {
    if (videoElement) {
      videoElement.currentTime = seconds;
      videoElement.play().catch(err => console.error('Error playing video:', err));
    }
  };
  
  const formatTime = (seconds: number): string => {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.floor(seconds % 60);
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
  };
  
  if (isLoading) {
    return (
      <div className="mt-6">
        <h3 className="text-lg font-medium mb-2">Recognition</h3>
        <div className="bg-gray-50 p-4 rounded">
          <p className="text-gray-500">Loading recognition data...</p>
        </div>
      </div>
    );
  }
  
  if (isError) {
    return (
      <div className="mt-6">
        <h3 className="text-lg font-medium mb-2">Recognition</h3>
        <div className="bg-red-50 p-4 rounded border-l-4 border-red-500">
          <p className="text-red-700">Error loading recognition data.</p>
        </div>
      </div>
    );
  }
  
  const hasFacialRecognition = capture?.facial_recognition_path;
  const hasSpeakerIdentification = capture?.speaker_identification_results;
  const hasRecognitionResults = hasFacialRecognition || hasSpeakerIdentification;
  
  // Parse speaker identification results if available
  const speakerResults = hasSpeakerIdentification 
    ? (typeof capture.speaker_identification_results === 'string' 
      ? JSON.parse(capture.speaker_identification_results) 
      : capture.speaker_identification_results)
    : null;
  
  return (
    <div className="mt-6">
      <h3 className="text-lg font-medium mb-2">Recognition</h3>
      
      {!hasRecognitionResults ? (
        <div className="bg-gray-50 p-4 rounded border border-gray-200">
          <p className="text-gray-700 mb-3">
            No recognition data available for this capture. Process this capture for facial recognition and speaker identification.
          </p>
          <button
            onClick={handleProcessRecognition}
            disabled={isProcessing}
            className={`px-3 py-1.5 rounded text-white ${
              isProcessing ? 'bg-blue-400 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700'
            }`}
          >
            {isProcessing ? 'Processing...' : 'Process Recognition'}
          </button>
        </div>
      ) : (
        <div>
          {/* Recognition Status */}
          <div className="bg-white p-4 rounded border border-gray-200 mb-4">
            <div className="flex items-center justify-between mb-2">
              <h4 className="font-medium">Recognition Status</h4>
              <button
                onClick={handleProcessRecognition}
                disabled={isProcessing}
                className={`px-2 py-1 text-sm rounded text-white ${
                  isProcessing ? 'bg-blue-400 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700'
                }`}
              >
                {isProcessing ? 'Processing...' : capture?.recognition_status === 'completed' ? 'Reprocess' : 'Process Recognition'}
              </button>
            </div>
            
            <div className="grid grid-cols-2 gap-4 mb-4">
              <div>
                <p className="text-sm text-gray-500">Facial Recognition:</p>
                <p className={`text-sm ${hasFacialRecognition ? 'text-green-600' : 'text-yellow-600'}`}>
                  {hasFacialRecognition ? 'Available' : 'Not Available'}
                </p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Speaker Identification:</p>
                <p className={`text-sm ${hasSpeakerIdentification ? 'text-green-600' : 'text-yellow-600'}`}>
                  {hasSpeakerIdentification ? 'Available' : 'Not Available'}
                </p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Status:</p>
                <p className={`text-sm ${capture?.recognition_status === 'completed' ? 'text-green-600' : capture?.recognition_status === 'error' ? 'text-red-600' : 'text-blue-600'}`}>
                  {capture?.recognition_status ? capture.recognition_status.charAt(0).toUpperCase() + capture.recognition_status.slice(1) : 'Not Started'}
                </p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Last Updated:</p>
                <p className="text-sm text-gray-600">
                  {capture?.recognition_completed_at ? new Date(capture.recognition_completed_at).toLocaleString() : 'N/A'}
                </p>
              </div>
            </div>
            
            {/* Always show progress information during processing */}
            <div className="mb-4">
              <div className="text-sm font-medium mb-2">
                {isProcessing ? (
                  <div className="flex items-center">
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600 mr-2"></div>
                    <span className="text-blue-600">Recognition in progress...</span>
                  </div>
                ) : capture?.recognition_status === 'completed' ? (
                  <div className="text-green-600">Recognition completed successfully</div>
                ) : capture?.recognition_status === 'error' ? (
                  <div className="text-red-600">Recognition failed</div>
                ) : (
                  <div className="text-gray-600">No recognition data available</div>
                )}
              </div>
              
              {/* Debug information */}
              <div className="text-xs text-gray-500 mb-2">
                Status: <span className="font-mono">{capture?.recognition_status || 'unknown'}</span> | 
                Processing: <span className="font-mono">{isProcessing ? 'true' : 'false'}</span> | 
                Show Progress: <span className="font-mono">{showProgress ? 'true' : 'false'}</span>
              </div>
              
              {/* Show detailed progress component */}
              {(isProcessing || showProgress) && (
                <div className="mt-4 border border-gray-200 rounded p-3 bg-gray-50">
                  <div className="text-sm font-medium mb-2">Recognition Progress Details:</div>
                  <RecognitionProgress 
                    captureId={captureId} 
                    isProcessing={isProcessing} 
                    onComplete={handleProgressComplete} 
                  />
                </div>
              )}
              
              {/* Add a button to hide/show progress details when completed */}
              {!isProcessing && showProgress && (capture?.recognition_status === 'completed' || capture?.recognition_status === 'error') && (
                <div className="mt-2">
                  <button 
                    onClick={() => setShowProgress(!showProgress)}
                    className="text-sm text-blue-600 hover:text-blue-800 underline"
                  >
                    {showProgress ? "Hide details" : "Show details"}
                  </button>
                </div>
              )}
              
              {/* Force show progress button if it's processing but progress isn't visible */}
              {isProcessing && !showProgress && (
                <div className="mt-2">
                  <button 
                    onClick={() => setShowProgress(true)}
                    className="text-sm bg-blue-600 text-white px-3 py-1 rounded hover:bg-blue-700"
                  >
                    Show Progress Details
                  </button>
                </div>
              )}
            </div>
          </div>
          
          {/* Speaker Results */}
          {speakerResults && speakerResults.speakers && speakerResults.speakers.length > 0 && (
            <div className="bg-white p-4 rounded border border-gray-200 mb-4">
              <h4 className="font-medium mb-3">Identified Speakers</h4>
              <div className="space-y-3 max-h-60 overflow-y-auto">
                {speakerResults.speakers.map((speaker: any, index: number) => (
                  <div key={index} className="bg-gray-50 p-3 rounded border border-gray-200">
                    <div className="flex justify-between items-start">
                      <div>
                        <div className="flex items-center">
                          <span className="font-medium">{speaker.name}</span>
                          <span className={`ml-2 px-2 py-0.5 text-xs rounded-full ${
                            speaker.confidence > 0.7 ? 'bg-green-100 text-green-800' : 
                            speaker.confidence > 0.5 ? 'bg-yellow-100 text-yellow-800' : 
                            'bg-red-100 text-red-800'
                          }`}>
                            {Math.round(speaker.confidence * 100)}% confidence
                          </span>
                        </div>
                        <div className="text-sm text-gray-500 mt-1">
                          {formatTime(speaker.start_time)} - {formatTime(speaker.end_time)} ({Math.round(speaker.duration)} seconds)
                        </div>
                      </div>
                      <button
                        onClick={() => jumpToTimestamp(speaker.start_time)}
                        className="px-2 py-1 text-xs bg-blue-100 text-blue-700 rounded hover:bg-blue-200"
                      >
                        Jump to Timestamp
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
          
          {/* Facial Recognition Video */}
          {hasFacialRecognition && (
            <div className="bg-white p-4 rounded border border-gray-200">
              <h4 className="font-medium mb-3">Facial Recognition Video</h4>
              <p className="text-sm text-gray-500 mb-2">
                This video has been processed with facial recognition to identify speakers.
              </p>
              <div className="text-sm text-blue-600 hover:underline cursor-pointer">
                <a href={`/api/v1/videos/static/facial_recognition/${capture.id}`} target="_blank" rel="noopener noreferrer">
                  View Facial Recognition Video
                </a>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default RecognitionPanel;
