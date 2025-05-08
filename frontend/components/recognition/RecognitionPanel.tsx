import React, { useState, useEffect } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { api } from '../../utils/api';
import RecognitionProgress from './RecognitionProgress';

interface RecognitionPanelProps {
  captureId: number;
  videoElement: HTMLVideoElement | null;
}

const RecognitionPanel: React.FC<RecognitionPanelProps> = ({ captureId, videoElement }) => {
  const [isProcessing, setIsProcessing] = useState(false);
  const [showProgress, setShowProgress] = useState(false);
  
  // Fetch capture data to get recognition status
  const { data: capture, isLoading, isError, refetch } = useQuery({
    queryKey: ['captureRecognition', captureId],
    queryFn: async () => {
      return await api.get(`/capture/${captureId}`);
    },
    enabled: !!captureId
  });
  
  // Check if recognition is already in progress when component mounts
  useEffect(() => {
    if (capture?.recognition_status === 'processing') {
      setIsProcessing(true);
      setShowProgress(true);
    }
  }, [capture]);

  // Process recognition mutation
  const processMutation = useMutation({
    mutationFn: async () => {
      setIsProcessing(true);
      setShowProgress(true);
      try {
        console.log('Starting recognition processing for capture ID:', captureId);
        
        // Get the token from localStorage for debugging
        const token = localStorage.getItem('token');
        console.log('Auth token available:', !!token);
        if (token) {
          console.log('Token first 20 chars:', token.substring(0, 20));
        }
        
        // Log the API base URL
        console.log('API base URL:', (api as any).getBaseUrl?.() || 'Not available');
        
        // Use the API client to make the request with the correct path
        console.log('Making request to combined recognition endpoint');
        console.log('Request payload:', { video_id: captureId, save_output: true });
        
        try {
          // Make sure there's a slash between the base URL and the endpoint
          const response = await api.post('/recognition/combined-recognition', {
            video_id: captureId,
            save_output: true
          });
          
          console.log('Recognition processing response:', response);
          return response;
        } catch (error) {
          console.error('Error details:', error);
          // Try a direct fetch as a fallback
          console.log('Trying direct fetch as fallback...');
          const directResponse = await fetch('http://localhost:8000/api/v1/recognition/combined-recognition', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
              video_id: captureId,
              save_output: true
            })
          });
          
          console.log('Direct fetch status:', directResponse.status);
          if (!directResponse.ok) {
            const errorText = await directResponse.text();
            console.error('Direct fetch error:', errorText);
            throw new Error(`Direct fetch error: ${directResponse.status} - ${errorText}`);
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
      // We'll keep isProcessing true until the progress component tells us it's done
      refetch();
    },
    onError: (error) => {
      console.error('Error processing recognition:', error);
      // Keep showing progress to display the error
    }
  });
  
  const handleProcessRecognition = () => {
    processMutation.mutate();
  };
  
  const handleProgressComplete = () => {
    // Called when the progress component detects completion
    setIsProcessing(false);
    refetch();
    // Keep showing progress for a moment so user can see completion
    setTimeout(() => {
      setShowProgress(false);
    }, 3000);
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
            
            {/* Show progress information if processing or if showProgress is true */}
            {(isProcessing || showProgress) && (
              <RecognitionProgress 
                captureId={captureId} 
                isProcessing={isProcessing} 
                onComplete={handleProgressComplete} 
              />
            )}
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
