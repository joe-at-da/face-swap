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
  recognition_results?: any; // Add this property for recognition results
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
  const [recognitionMessage, setRecognitionMessage] = useState<string>('');

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
    refetchInterval: 2000, // Poll every 2 seconds regardless of processing state
    staleTime: 0, // Consider data always stale to ensure fresh data
    refetchOnWindowFocus: true, // Refetch when window regains focus
  });
  
  // Process the recognition results for display
  const processRecognitionResults = useCallback(() => {
    if (capture?.recognition_results) {
      try {
        // Parse the results if they're a string
        const results = typeof capture.recognition_results === 'string' 
          ? JSON.parse(capture.recognition_results) 
          : capture.recognition_results;
        
        console.log('Processing recognition results:', results);
        
        // Check if we have speaker identification results
        const hasSpeakers = results.speaker_identification && 
          results.speaker_identification.results && 
          results.speaker_identification.results.speakers && 
          results.speaker_identification.results.speakers.length > 0;
        
        // Check if we have transcription results
        const hasTranscript = 
          (results.transcription && results.transcription.transcript && results.transcription.transcript.length > 0) ||
          (results.results_summary && results.results_summary.transcript_text && results.results_summary.transcript_text.length > 0 && 
           results.results_summary.transcript_text !== 'No transcript available.');
        
        // Set the recognition message based on the results
        if (hasSpeakers && hasTranscript) {
          const speakerCount = results.speaker_identification.results.speakers.length;
          setRecognitionMessage(`Recognition completed successfully. ${speakerCount} speaker(s) identified and transcription available.`);
        } else if (hasSpeakers) {
          const speakerCount = results.speaker_identification.results.speakers.length;
          setRecognitionMessage(`Recognition completed successfully. ${speakerCount} speaker(s) identified, but no transcription available.`);
        } else if (hasTranscript) {
          setRecognitionMessage('Recognition completed. No speakers were identified, but transcription is available.');
        } else {
          // Check if there are any messages in the results
          const speakerMessage = results.speaker_identification?.message || results.results_summary?.speaker_identification_message || '';
          const transcriptMessage = results.transcription?.message || results.results_summary?.transcription_message || '';
          
          if (speakerMessage || transcriptMessage) {
            setRecognitionMessage(`Recognition completed. ${speakerMessage} ${transcriptMessage}`.trim());
          } else {
            setRecognitionMessage('Recognition completed, but no speakers or transcription were identified in this clip.');
          }
        }
      } catch (error) {
        console.error('Error processing recognition results:', error);
        setRecognitionMessage('Recognition completed, but there was an error processing the results.');
      }
    } else {
      setRecognitionMessage('Recognition completed, but no results were returned.');
    }
  }, [capture]);
  
  // Also fetch recognition status directly to ensure we have the most up-to-date information
  const { data: recognitionStatusData } = useQuery({
    queryKey: ['recognitionStatusDirect', captureId],
    queryFn: async () => {
      console.log(`Fetching direct recognition status for ID: ${captureId}`);
      try {
        const response = await api.get(`/recognition/recognition-status/${captureId}`);
        console.log('Direct recognition status response:', response);
        return response;
      } catch (error) {
        console.warn(`Error fetching direct status, will rely on capture data: ${error}`);
        return null;
      }
    },
    enabled: !!captureId && (isProcessing || recognitionStatus === 'processing'),
    refetchInterval: isProcessing ? 2000 : false, // Poll every 2 seconds when processing
    staleTime: 0, // Consider data always stale to ensure fresh data
  });
  
  // Mutation to start the recognition process
  const processMutation = useMutation<any, Error, void>({
    mutationFn: async () => {
      console.log(`Starting recognition process for ID: ${captureId}`);
      return await api.post(`/recognition/combined-recognition`, { video_id: captureId, save_output: true });
    },
    onSuccess: () => {
      console.log('Recognition process started successfully');
      setIsProcessing(true);
      setShowProgress(true);
      setRecognitionStatus('processing');
      refetch(); // Refetch to get the updated status
    },
    onError: (error) => {
      console.error('Error starting recognition process:', error);
      setRecognitionStatus('error');
    }
  });
  
  // Handle button click to start recognition process
  const handleStartRecognition = () => {
    console.log('Starting recognition process...');
    processMutation.mutate();
  };

  // Handle when the progress component signals completion
  const handleProgressComplete = useCallback((status?: string) => {
    console.log(`Progress component signaled completion with status: ${status || 'completed'}`);
    setIsProcessing(false);
    
    // Update recognition status if provided
    if (status) {
      setRecognitionStatus(status);
    } else {
      setRecognitionStatus('completed');
    }
    
    // Trigger a refetch to get the latest data
    refetch();
  }, [refetch]);

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
          setIsProcessing(false);
        } else if (capture.recognition_status === 'processing' && !isProcessing) {
          // If status is processing but our state doesn't reflect that, update it
          setIsProcessing(true);
          setShowProgress(true);
        }
      } else {
        console.log('No recognition_status in capture data');
      }
      
      // Process the recognition results for display
      processRecognitionResults();
      
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
  }, [capture, isProcessing, recognitionStatus, speakerResults, processRecognitionResults]);
  
  // Effect to process direct recognition status updates
  useEffect(() => {
    if (recognitionStatusData && recognitionStatusData.status) {
      console.log('Recognition status data updated:', recognitionStatusData);
      
      // Update the status if it's different
      if (recognitionStatusData.status.status !== recognitionStatus) {
        console.log(`Updating recognition status from direct query: ${recognitionStatusData.status.status}`);
        setRecognitionStatus(recognitionStatusData.status.status);
      }
      
      // If status is completed or error, update the processing state
      if (recognitionStatusData.status.status === 'completed' || recognitionStatusData.status.status === 'error') {
        setIsProcessing(false);
      }
    }
  }, [recognitionStatusData, recognitionStatus]);

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
      videoElement.play().catch(e => console.error('Error playing video:', e));
    }
  };

  return (
    <div className="space-y-4">
      {/* Recognition Controls */}
      <div className="bg-white p-4 rounded border border-gray-200">
        <div className="flex justify-between items-center">
          <h3 className="text-lg font-medium">Recognition</h3>
          {!isProcessing && recognitionStatus !== 'completed' && (
            <button
              onClick={handleStartRecognition}
              disabled={isProcessing}
              className="px-4 py-2 bg-primary text-white rounded hover:bg-primary-dark disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Start Recognition
            </button>
          )}
        </div>
        
        {/* Status and Progress */}
        <div className="mt-4">
          <div className="text-sm text-gray-600 mb-1">Status:</div>
          <div className="bg-gray-50 p-3 rounded border border-gray-200">
            {isLoading ? (
              <div className="animate-pulse h-4 bg-gray-200 rounded w-1/4"></div>
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
      </div>
      
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
      
      {/* Transcription Results */}
      {recognitionStatus === 'completed' && recognitionResults && (
        <div className="bg-white p-4 rounded border border-gray-200 mb-4">
          <h4 className="font-medium mb-3">Transcription</h4>
          {recognitionResults.transcription?.transcript || 
           recognitionResults.results_summary?.transcript_text ? (
            <div>
              <div className="mt-2 p-4 bg-gray-50 rounded border border-gray-200">
                <p className="text-sm whitespace-pre-wrap">
                  {recognitionResults.transcription?.transcript || 
                   recognitionResults.results_summary?.transcript_text}
                </p>
              </div>
              {(recognitionResults.transcription?.message || 
                recognitionResults.results_summary?.transcription_message) && (
                <div className="mt-2">
                  <p className="text-xs text-gray-500">
                    {recognitionResults.transcription?.message || 
                     recognitionResults.results_summary?.transcription_message}
                  </p>
                </div>
              )}
            </div>
          ) : (
            <p className="text-sm text-gray-500">No transcription results available</p>
          )}
        </div>
      )}
      
      {/* Show a message when completed but no speaker results */}
      {recognitionStatus === 'completed' && (!speakerResults || !speakerResults.segments || speakerResults.segments.length === 0) && (
        <div className="bg-white p-4 rounded border border-gray-200 mb-4">
          <p className="text-gray-700">{recognitionMessage}</p>
        </div>
      )}
    </div>
  );
};

export default RecognitionPanel;
