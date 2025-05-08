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
  const [recognitionStatus, setRecognitionStatus] = useState<string | undefined>(undefined);
  const [recognitionResults, setRecognitionResults] = useState<any | null>(null);

  console.log('RecognitionPanel render state:', { isProcessing, showProgress, recognitionStatus });
  
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
    enabled: !!captureId,
    refetchInterval: isProcessing ? 5000 : false, // Poll every 5 seconds when processing
  });
  
  // Check if recognition is already in progress or completed when component mounts or data changes
  useEffect(() => {
    if (capture) {
      console.log('Capture data changed:', capture);
      
      // Update recognition status from capture data
      if (capture.recognition_status) {
        setRecognitionStatus(capture.recognition_status);
        
        // If status is completed or error, update the processing state
        if (capture.recognition_status === 'completed' || capture.recognition_status === 'error') {
          setIsProcessing(false);
          
          // Try to parse and set the recognition results if available
          if (capture.speaker_identification_results) {
            try {
              const results = typeof capture.speaker_identification_results === 'string' 
                ? JSON.parse(capture.speaker_identification_results)
                : capture.speaker_identification_results;
              setRecognitionResults(results);
            } catch (e) {
              console.error('Error parsing recognition results:', e);
            }
          }
        } else if (capture.recognition_status === 'processing') {
          // If status is processing, update the processing state
          setIsProcessing(true);
          setShowProgress(true);
        }
      }
    }
  }, [capture]);

  // Handle button click to process recognition
  const handleProcessRecognition = () => {
    console.log('Starting recognition process');
    setIsProcessing(true);
    setShowProgress(true);
    setRecognitionStatus('processing');
    processMutation.mutate();
  };

  // Handle progress completion
  const handleProgressComplete = () => {
    console.log('Recognition progress complete');
    setIsProcessing(false);
    // Refetch the capture data to get updated recognition results
    refetch().then(() => {
      console.log('Refetched capture data after completion');
    }).catch(err => {
      console.error('Error refetching capture data:', err);
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

  // Initialize all state hooks at the top level (not conditionally)
  const [speakerResults, setSpeakerResults] = useState<any | null>(null);
  
  const hasFacialRecognition = !!capture?.facial_recognition_path;
  const hasSpeakerIdentification = capture?.speaker_identification_results;
  const hasRecognitionResults = hasFacialRecognition || hasSpeakerIdentification;

  // Check if we have speaker identification results
  useEffect(() => {
    if (capture?.speaker_identification_results) {
      try {
        const results = typeof capture.speaker_identification_results === 'string' 
          ? JSON.parse(capture.speaker_identification_results)
          : capture.speaker_identification_results;
        setSpeakerResults(results);
        setRecognitionResults(results);
      } catch (e) {
        console.error('Error parsing speaker results:', e);
      }
    }
  }, [capture?.speaker_identification_results]);

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
            disabled={isProcessing || processMutation.isPending}
            className={`px-4 py-2 rounded text-white ${isProcessing || processMutation.isPending ? 'bg-gray-400 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700'}`}
          >
            {isProcessing || processMutation.isPending ? (
              <span className="flex items-center">
                <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Processing...
              </span>
            ) : 'Process Recognition'}
          </button>
        </div>
      ) : (
        <div>
          {/* Recognition Status */}
          <div className="bg-white p-4 rounded border border-gray-200 mb-4">
            <h4 className="font-medium mb-3">Recognition Status</h4>
            <div className="space-y-2">
              {isLoading ? (
                <div className="text-sm text-gray-500">Loading recognition status...</div>
              ) : isError ? (
                <div className="text-sm text-red-500">Error loading recognition status</div>
              ) : (
                <div>
                  <div className="text-sm mb-2">
                    {!recognitionStatus || recognitionStatus === 'not_started' ? (
                      <span className="text-gray-500">No recognition data available for this capture.</span>
                    ) : recognitionStatus === 'processing' ? (
                      <span className="text-blue-500">Recognition is currently processing...</span>
                    ) : recognitionStatus === 'completed' ? (
                      <span className="text-green-500">Recognition completed successfully.</span>
                    ) : recognitionStatus === 'error' ? (
                      <span className="text-red-500">Recognition failed with an error.</span>
                    ) : (
                      <span className="text-gray-500">Unknown recognition status: {recognitionStatus}</span>
                    )}
                  </div>
                  
                  {/* Process Button */}
                  {(!recognitionStatus || 
                    recognitionStatus === 'not_started' || 
                    recognitionStatus === 'error') && (
                    <button
                      onClick={handleProcessRecognition}
                      disabled={isProcessing || processMutation.isPending}
                      className={`px-4 py-2 rounded text-white ${isProcessing || processMutation.isPending ? 'bg-gray-400 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700'}`}
                    >
                      {isProcessing || processMutation.isPending ? (
                        <span className="flex items-center">
                          <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                          </svg>
                          Processing...
                        </span>
                      ) : 'Process Recognition'}
                    </button>
                  )}
                </div>
              )}
              
              {/* Progress Component */}
              {(isProcessing || showProgress) && (
                <div className="mt-4 border-t pt-4 border-gray-200">
                  <RecognitionProgress 
                    captureId={captureId} 
                    isProcessing={isProcessing} 
                    onComplete={handleProgressComplete} 
                  />
                </div>
              )}
              
              {/* Add a button to hide/show progress details when completed */}
              {!isProcessing && (recognitionStatus === 'completed' || recognitionStatus === 'error') && (
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
