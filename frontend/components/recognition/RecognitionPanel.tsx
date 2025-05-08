import React, { useState, useEffect, useCallback } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { api } from '../../utils/api';
import RecognitionProgress from './RecognitionProgress';

interface RecognitionPanelProps {
  captureId: number;
  videoElement: HTMLVideoElement | null;
}

interface CaptureData {
  id: number;
  status?: string; // General capture status
  recognition_status?: string;
  facial_recognition_path: string | null;
  speaker_identification_path: string | null;
  speaker_identification_results: string | null;
  recognition_completed_at: string | null;
}

interface SpeakerSegment {
  speaker: string;
  start: number;
  end: number;
  confidence?: number;
  text?: string;
}

interface SpeakerResults {
  segments?: SpeakerSegment[];
}

const RecognitionPanel: React.FC<RecognitionPanelProps> = ({ captureId, videoElement }) => {
  const [isProcessing, setIsProcessing] = useState(false);
  const [showProgress, setShowProgress] = useState(false);
  const [recognitionStatus, setRecognitionStatus] = useState<string | undefined>(undefined);
  const [recognitionResults, setRecognitionResults] = useState<any | null>(null);
  const [speakerResults, setSpeakerResults] = useState<SpeakerResults | null>(null);

  console.log('RecognitionPanel render state:', { isProcessing, showProgress, recognitionStatus });

  // Fetch capture data to get recognition status
  const { data: capture, isLoading, isError, error, refetch } = useQuery<CaptureData>({
    queryKey: ['captureRecognition', captureId],
    queryFn: async () => {
      console.log(`Fetching capture data for ID: ${captureId}`);
      const response = await api.get(`/capture/${captureId}`);
      console.log('Capture API response:', response);
      return response as CaptureData;
    },
    refetchInterval: 3000, // Poll every 3 seconds regardless of processing state
    staleTime: 0, // Consider data always stale to ensure fresh data
  });

  // Helper function to format time in MM:SS format
  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  // Function to jump to a specific timestamp in the video
  const jumpToTimestamp = (seconds: number) => {
    if (videoElement) {
      videoElement.currentTime = seconds;
      videoElement.play().catch(err => console.error('Error playing video:', err));
    }
  };

  // Function to start the recognition process
  const startRecognition = useCallback(async () => {
    if (!captureId || !videoElement) return;
    
    // Don't start recognition if it's already completed or processing
    if (recognitionStatus === 'completed' || recognitionStatus === 'processing' || isProcessing) {
      console.log(`Recognition already ${recognitionStatus}, not starting again`);
      return;
    }
    
    setIsProcessing(true);
    setShowProgress(true);
    
    console.log(`Starting recognition processing for capture ID: ${captureId}`);
    
    try {
      const response = await api.post('/recognition/combined-recognition', {
        video_id: captureId,
      });
      
      console.log('Recognition process started:', response);
      
      // Refetch capture data to get updated status
      refetch();
    } catch (error) {
      console.error('Error starting recognition process:', error);
      setIsProcessing(false);
    }
  }, [captureId, videoElement, refetch, recognitionStatus, isProcessing]);

  // Process recognition mutation - used to start the recognition process
  const processMutation = useMutation({
    mutationFn: startRecognition,
    onSuccess: () => {
      console.log('Recognition processing started successfully');
      // We'll keep the processing state true until the progress component signals completion
    },
    onError: (error) => {
      console.error('Error in recognition processing:', error);
      setIsProcessing(false);
      setShowProgress(false);
    }
  });

  // Handle button click to start recognition process
  const handleStartRecognition = () => {
    // Don't start if already processing or completed
    if (isProcessing || recognitionStatus === 'completed') {
      console.log('Not starting recognition - already processing or completed');
      return;
    }
    processMutation.mutate();
  };

  // Handle when the progress component signals completion
  const handleProgressComplete = useCallback(() => {
    console.log('Progress component signaled completion');
    setIsProcessing(false);
    // We'll let the useEffect that watches capture handle the state updates
  }, []);

  // Effect to update state based on capture data changes
  useEffect(() => {
    if (capture) {
      console.log('Capture data changed:', capture);
      console.log('Current status in state:', { isProcessing, recognitionStatus });
      
      // First check if we have a completed timestamp, which is the most reliable indicator
      if (capture.recognition_completed_at) {
        console.log('Recognition has a completed timestamp:', capture.recognition_completed_at);
        setIsProcessing(false);
        setRecognitionStatus('completed');
        setShowProgress(true); // Keep showing progress to see the completed status
      }
      
      // Then check recognition_status
      if (capture.recognition_status) {
        console.log(`Setting recognition status to: ${capture.recognition_status}`);
        setRecognitionStatus(capture.recognition_status);
        
        // If status is completed or error, update the processing state
        if (capture.recognition_status === 'completed' || capture.recognition_status === 'error') {
          console.log(`Recognition process is ${capture.recognition_status}, updating UI state`);
          setIsProcessing(false);
          setShowProgress(true); // Keep showing progress to see the completed status
          
          // Try to parse and set the recognition results if available
          if (capture.speaker_identification_results) {
            console.log('Speaker identification results found, parsing...');
            try {
              const results = typeof capture.speaker_identification_results === 'string' 
                ? JSON.parse(capture.speaker_identification_results)
                : capture.speaker_identification_results;
              console.log('Parsed speaker results:', results);
              setRecognitionResults(results);
              setSpeakerResults(results);
            } catch (e) {
              console.error('Error parsing recognition results:', e);
            }
          } else {
            console.log('No speaker identification results available');
          }
        } else if (capture.recognition_status === 'processing') {
          // If status is processing, update the processing state
          console.log('Recognition is still processing');
          setIsProcessing(true);
          setShowProgress(true);
        }
      } else {
        console.log('No recognition_status in capture data');
      }
      
      // Only set recognition status to completed if we have explicit recognition completion indicators
      if (capture.recognition_completed_at) {
        console.log('Recognition has a completed timestamp, ensuring UI reflects this');
        setIsProcessing(false);
        setRecognitionStatus('completed');
      }
      // Don't automatically set recognition status to completed just because capture is completed
      
      // Handle speaker identification results separately as a fallback
      if (capture.speaker_identification_results && !speakerResults) {
        console.log('Processing speaker results as fallback');
        try {
          const results = typeof capture.speaker_identification_results === 'string' 
            ? JSON.parse(capture.speaker_identification_results)
            : capture.speaker_identification_results;
          console.log('Setting speaker results from fallback logic:', results);
          setSpeakerResults(results);
          setRecognitionResults(results);
        } catch (e) {
          console.error('Error parsing speaker results:', e);
        }
      }
    }
  }, [capture, isProcessing, recognitionStatus, speakerResults]);

  return (
    <div className="mt-6">
      <h3 className="text-lg font-medium mb-2">Recognition</h3>
      
      {!recognitionStatus && !isProcessing && (
        <div className="bg-gray-50 p-4 rounded border border-gray-200">
          <p className="text-gray-700 mb-3">
            No recognition data available for this capture. Process this capture for facial recognition and speaker identification.
          </p>
          <button
            onClick={handleStartRecognition}
            disabled={processMutation.isPending}
            className={`px-4 py-2 rounded text-white ${processMutation.isPending ? 'bg-gray-400 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700'}`}
          >
            {processMutation.isPending ? 'Starting...' : 'Start Recognition'}
          </button>
        </div>
      )}
      
      {(isProcessing || recognitionStatus === 'completed') && (
        <div className="bg-gray-50 p-4 rounded border border-gray-200 mb-4">
          <div className="flex justify-between items-start">
            <h4 className="font-medium">Recognition Status</h4>
          </div>
          
          <div className="mt-3">
            {isLoading ? (
              <div className="text-sm text-gray-500">Loading recognition status...</div>
            ) : isError ? (
              <div className="text-sm text-red-500">Error loading recognition status</div>
            ) : (
              <div>
                <div className="text-sm mb-2">
                  {!recognitionStatus ? (
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
                
                {/* Show progress component */}
                {(isProcessing || recognitionStatus === 'completed') && (
                  <div className="mt-3 border-t pt-3 border-gray-100">
                    <RecognitionProgress 
                      captureId={captureId} 
                      isProcessing={isProcessing} 
                      onComplete={handleProgressComplete} 
                    />
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
      
      {/* Speaker Results */}
      {recognitionStatus === 'completed' && speakerResults && speakerResults.segments && speakerResults.segments.length > 0 && (
        <div className="bg-white p-4 rounded border border-gray-200 mb-4">
          <h4 className="font-medium mb-3">Identified Speakers</h4>
          <div className="space-y-3 max-h-60 overflow-y-auto">
            {speakerResults.segments.map((segment, index) => (
              <div key={index} className="bg-gray-50 p-3 rounded border border-gray-200">
                <div className="flex justify-between items-start">
                  <div>
                    <div className="flex items-center">
                      <span className="font-medium">{segment.speaker || 'Unknown Speaker'}</span>
                      {segment.confidence && (
                        <span className={`ml-2 px-2 py-0.5 text-xs rounded-full ${
                          segment.confidence > 0.7 ? 'bg-green-100 text-green-800' : 
                          segment.confidence > 0.5 ? 'bg-yellow-100 text-yellow-800' : 
                          'bg-red-100 text-red-800'
                        }`}>
                          {Math.round(segment.confidence * 100)}% confidence
                        </span>
                      )}
                    </div>
                    <div className="text-sm text-gray-500 mt-1">
                      {formatTime(segment.start)} - {formatTime(segment.end)} ({Math.round(segment.end - segment.start)} seconds)
                    </div>
                  </div>
                  <button
                    onClick={() => jumpToTimestamp(segment.start)}
                    className="px-2 py-1 text-xs bg-blue-100 text-blue-700 rounded hover:bg-blue-200"
                  >
                    Jump to Timestamp
                  </button>
                </div>
                {segment.text && (
                  <p className="mt-2 text-sm text-gray-700 italic">"{segment.text}"</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
      
      {/* Show a message when completed but no speaker results */}
      {recognitionStatus === 'completed' && (!speakerResults || !speakerResults.segments || speakerResults.segments.length === 0) && (
        <div className="bg-white p-4 rounded border border-gray-200 mb-4">
          <p className="text-gray-700">Recognition completed, but no speakers were identified in this clip.</p>
        </div>
      )}
    </div>
  );
};

export default RecognitionPanel;
