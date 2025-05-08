import React, { useState, useEffect, useCallback } from 'react';
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

/**
 * RecognitionPanel Component
 * Handles the recognition process for a capture, including displaying status and results
 */
const RecognitionPanel: React.FC<RecognitionPanelProps> = ({ captureId, videoElement }) => {
  // All state hooks declared at the top level to avoid React Hooks errors
  const [isProcessing, setIsProcessing] = useState(false);
  const [showProgress, setShowProgress] = useState(false);
  const [recognitionStatus, setRecognitionStatus] = useState<string | undefined>(undefined);
  const [recognitionResults, setRecognitionResults] = useState<any | null>(null);
  const [speakerResults, setSpeakerResults] = useState<any | null>(null);

  console.log('RecognitionPanel render state:', { isProcessing, showProgress, recognitionStatus });
  
  // Fetch capture data to get recognition status
  const { data: capture, isLoading, isError, error, refetch } = useQuery<CaptureData>({
    queryKey: ['captureRecognition', captureId],
    queryFn: async () => {
      const response = await api.get(`/capture/${captureId}`);
      return response as CaptureData;
    },
    refetchInterval: isProcessing ? 3000 : false, // Poll every 3 seconds while processing
  });

  // Helper function to format time in MM:SS format
  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
  };

  // Jump to a specific timestamp in the video
  const jumpToTimestamp = useCallback((seconds: number) => {
    if (videoElement) {
      videoElement.currentTime = seconds;
      videoElement.play();
    }
  }, [videoElement]);

  // Handle progress completion
  const handleProgressComplete = useCallback(() => {
    console.log('Recognition progress complete, refreshing data');
    // Refetch the capture data to get the latest status and results
    refetch();
    // We'll let the useEffect that watches capture handle the state updates
  }, [refetch]);

  // Process recognition mutation - used to start the recognition process
  const processMutation = useMutation({
    mutationFn: async () => {
      try {
        console.log('Starting recognition processing for capture ID:', captureId);
        
        // Set processing state
        setIsProcessing(true);
        setShowProgress(true);
        
        // Make request to combined recognition endpoint
        const response = await api.post('/recognition/combined-recognition', {
          video_id: captureId
        });
        
        console.log('Recognition processing response:', response);
        return response;
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

  // Handle button click to process recognition
  const handleProcessRecognition = useCallback(() => {
    processMutation.mutate();
  }, [processMutation]);

  // Effect to update state based on capture data changes
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
              setSpeakerResults(results);
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
      
      // Handle speaker identification results separately
      if (capture.speaker_identification_results) {
        try {
          const results = typeof capture.speaker_identification_results === 'string' 
            ? JSON.parse(capture.speaker_identification_results)
            : capture.speaker_identification_results;
          setSpeakerResults(results);
        } catch (e) {
          console.error('Error parsing speaker results:', e);
        }
      }
    }
  }, [capture]);

  // If loading or error, show appropriate UI
  if (isLoading) {
    return (
      <div className="mt-6">
        <h3 className="text-lg font-medium mb-2">Recognition</h3>
        <div className="bg-gray-50 p-4 rounded border border-gray-200">
          <p className="text-gray-700">Loading recognition data...</p>
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="mt-6">
        <h3 className="text-lg font-medium mb-2">Recognition</h3>
        <div className="bg-gray-50 p-4 rounded border border-gray-200">
          <p className="text-red-700">Error loading recognition data.</p>
        </div>
      </div>
    );
  }
  
  const hasFacialRecognition = !!capture?.facial_recognition_path;
  const hasSpeakerIdentification = capture?.speaker_identification_results;
  const hasRecognitionResults = hasFacialRecognition || hasSpeakerIdentification;

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
          <div className="bg-white p-4 rounded border border-gray-200 mb-4">
            <div className="flex justify-between items-start">
              <h4 className="font-medium">Recognition Status</h4>
              
              {/* Process button if we have results but want to reprocess */}
              {!isProcessing && (
                <button
                  onClick={handleProcessRecognition}
                  disabled={processMutation.isPending}
                  className="px-3 py-1 text-sm rounded text-white bg-blue-600 hover:bg-blue-700"
                >
                  {processMutation.isPending ? 'Starting...' : 'Reprocess'}
                </button>
              )}
            </div>
            
            <div className="mt-3">
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
                      <span className="text-gray-500">Recognition status: {recognitionStatus}</span>
                    )}
                  </div>
                  
                  {/* Show progress component if processing or if we want to show details */}
                  {(isProcessing || showProgress) && (
                    <div className="mt-3 border-t pt-3 border-gray-100">
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
