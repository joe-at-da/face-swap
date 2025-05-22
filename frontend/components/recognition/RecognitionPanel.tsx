/**
 * @deprecated This component is deprecated and will be removed in a future release.
 * Please use UnifiedRecognitionPanel instead.
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { api } from '../../utils/api';
import RecognitionProgress from './RecognitionProgress';
import { toast } from 'react-toastify';

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

/**
 * @deprecated Use UnifiedRecognitionPanel instead
 */
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
        
        // Set the recognition results
        setRecognitionResults(results);
        
        // Process speaker segments if available
        if (results.speaker_identification && 
            results.speaker_identification.results && 
            results.speaker_identification.results.segments) {
          setSpeakerResults({
            segments: results.speaker_identification.results.segments
          });
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
    <div className="mt-8">
      <h3 className="text-xl font-semibold mb-4">Recognition</h3>

      {/* Recognition Controls */}
      <div className="bg-gray-800 text-white p-6 rounded-lg shadow-lg mb-4">
        <div className="flex items-center justify-between mb-4">
          <h4 className="font-medium text-lg">Status:</h4>
          <div className="flex items-center">
            {recognitionStatus === 'not_started' && (
              <button
                onClick={handleStartRecognition}
                disabled={processMutation.isPending}
                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-opacity-50 disabled:opacity-50 mr-3"
              >
                {processMutation.isPending ? 'Starting...' : 'Start Recognition'}
              </button>
            )}
            {recognitionStatus === 'not_started' && (
              <span className="text-xs bg-gray-700 text-gray-300 px-3 py-1.5 rounded-full font-medium">
                Not Started
              </span>
            )}
            {recognitionStatus === 'processing' && (
              <span className="text-xs bg-blue-900 text-blue-300 px-3 py-1.5 rounded-full font-medium flex items-center">
                <div className="w-2 h-2 bg-blue-400 rounded-full mr-2 animate-pulse"></div>
                Processing
              </span>
            )}
            {recognitionStatus === 'completed' && (
              <span className="text-xs bg-green-900 text-green-300 px-3 py-1.5 rounded-full font-medium flex items-center">
                <svg className="w-3 h-3 mr-1.5 text-green-400" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
                Completed
              </span>
            )}
            {recognitionStatus === 'failed' && (
              <span className="text-xs bg-red-900 text-red-300 px-3 py-1.5 rounded-full font-medium flex items-center">
                <svg className="w-3 h-3 mr-1.5 text-red-400" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                </svg>
                Failed
              </span>
            )}
          </div>
        </div>

        {/* Show info about recognition process */}
        {recognitionStatus === 'not_started' && (
          <div>
            <div className="mb-6 bg-gray-700 p-4 rounded-lg">
              <p className="text-gray-300 mb-4">
                The recognition process identifies speakers and generates a transcript from the audio.
              </p>

              <div className="space-y-4 mb-6">
                <div className="flex items-center">
                  <svg className="w-5 h-5 text-blue-400 mr-2" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                  <span className="text-gray-300">Speaker identification</span>
                </div>
                <div className="flex items-center">
                  <svg className="w-5 h-5 text-blue-400 mr-2" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                  <span className="text-gray-300">Audio transcription</span>
                </div>
                <div className="flex items-center">
                  <svg className="w-5 h-5 text-blue-400 mr-2" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                  <span className="text-gray-300">Facial recognition (if video available)</span>
                </div>
              </div>
            </div>
            
            <button
              onClick={handleStartRecognition}
              disabled={processMutation.isPending}
              className="w-full sm:w-auto px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-opacity-50 disabled:opacity-50 transition-colors flex items-center justify-center font-medium"
            >
              {processMutation.isPending ? (
                <>
                  <div className="spinner-xs mr-2"></div>
                  Starting...
                </>
              ) : (
                <>
                  <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  Start Recognition Process
                </>
              )}
            </button>
          </div>
        )}

        {/* Show message when failed */}
        {recognitionStatus === 'failed' && (
          <div>
            <div className="bg-red-900/30 border border-red-700/50 p-4 rounded-lg mb-4">
              <div className="flex items-start">
                <svg className="w-5 h-5 text-red-500 mr-2 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                </svg>
                <div>
                  <p className="text-red-300 font-medium">Recognition processing failed</p>
                  <p className="text-red-400 mt-1">Please try again or contact support if the issue persists.</p>
                </div>
              </div>
            </div>
            <button
              onClick={handleStartRecognition}
              disabled={processMutation.isPending}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-opacity-50 disabled:opacity-50 flex items-center"
            >
              {processMutation.isPending ? (
                <>
                  <div className="spinner-xs mr-2"></div>
                  Restarting...
                </>
              ) : (
                <>
                  <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                  Restart Recognition
                </>
              )}
            </button>
          </div>
        )}
      </div>

      {/* Audio Transcription Status - Only shown when processing */}
      {isProcessing && (
        <div className="bg-gray-800 text-white p-6 rounded-lg shadow-lg mb-4">
          <div className="flex items-center justify-between mb-2">
            <h4 className="font-medium">Audio Transcription</h4>
            <span className="text-xs text-blue-600 bg-blue-100 px-2 py-1 rounded-full">Part of recognition process</span>
          </div>
          <div className="p-4 bg-blue-50 rounded border border-blue-100 mb-2">
            <div className="flex items-center">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600 mr-2"></div>
              <span className="text-sm font-medium text-blue-700">Transcribing audio...</span>
            </div>
            <div className="mt-3">
              <div className="w-full bg-blue-200 rounded-full h-2.5">
                <div className="bg-blue-600 h-2.5 rounded-full animate-pulse" style={{ width: '50%' }}></div>
              </div>
            </div>
            <p className="mt-3 text-xs text-blue-700">
              The system is processing the audio file using speech recognition.
              This may take several minutes depending on the length of the audio.
            </p>
            <p className="mt-1 text-xs text-gray-500">Refreshing status every 3 seconds...</p>
          </div>
        </div>
      )}

      {/* Speaker Results */}
      {recognitionStatus === 'completed' && speakerResults && speakerResults.segments && speakerResults.segments.length > 0 && (
        <div className="bg-gray-800 text-white p-6 rounded-lg shadow-lg mb-4">
          <div className="flex items-center justify-between mb-4">
            <h4 className="font-medium text-lg">Identified Speakers</h4>
            <span className="text-xs bg-green-900 text-green-300 px-3 py-1.5 rounded-full font-medium flex items-center">
              <svg className="w-3 h-3 mr-1.5 text-green-400" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
              </svg>
              Completed
            </span>
          </div>
          <div className="space-y-3 max-h-80 overflow-y-auto pr-1 custom-scrollbar">
            {speakerResults.segments.map((segment, index) => (
              <div key={index} className="bg-gray-700 p-4 rounded-lg border border-gray-600">
                <div className="flex justify-between items-start">
                  <div>
                    <div className="flex items-center">
                      <span className="font-medium text-white">{segment.speaker || 'Unknown Speaker'}</span>
                      {segment.confidence && (
                        <span className={`ml-2 px-2 py-0.5 text-xs rounded-full ${
                          segment.confidence > 0.7 ? 'bg-green-900 text-green-300' :
                          segment.confidence > 0.5 ? 'bg-yellow-900 text-yellow-300' :
                          'bg-red-900 text-red-300'
                        }`}>
                          {Math.round(segment.confidence * 100)}% confidence
                        </span>
                      )}
                    </div>
                    <div className="text-sm text-gray-400 mt-1">
                      {formatTime(segment.start)} - {formatTime(segment.end)} ({Math.round(segment.end - segment.start)} seconds)
                    </div>
                  </div>
                  <button
                    onClick={() => jumpToTimestamp(segment.start)}
                    className="px-3 py-1.5 text-xs bg-blue-900 text-blue-300 rounded-lg hover:bg-blue-800 transition-colors"
                  >
                    Jump to Timestamp
                  </button>
                </div>
                {segment.text && (
                  <p className="mt-3 text-sm text-gray-300 italic border-t border-gray-600 pt-3">"{segment.text}"</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      
      {/* Transcription Results - Shows when completed */}
      {recognitionStatus === 'completed' && recognitionResults && (
        <div className="bg-gray-800 text-white p-6 rounded-lg shadow-lg mb-4">
          <div className="flex items-center justify-between mb-4">
            <h4 className="font-medium text-lg">Audio Transcription Results</h4>
            <span className="text-xs bg-green-900 text-green-300 px-3 py-1.5 rounded-full font-medium flex items-center">
              <svg className="w-3 h-3 mr-1.5 text-green-400" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
              </svg>
              Completed
            </span>
          </div>
          {recognitionResults.transcription?.transcript || 
           recognitionResults.results_summary?.transcript_text ? (
            <div>
              <div className="mt-2 p-5 bg-gray-700 rounded-lg border border-gray-600">
                <p className="text-gray-300 whitespace-pre-wrap leading-relaxed">
                  {recognitionResults.transcription?.transcript || 
                   recognitionResults.results_summary?.transcript_text}
                </p>
              </div>
              {(recognitionResults.transcription?.message || 
                recognitionResults.results_summary?.transcription_message) && (
                <div className="mt-3 p-3 bg-gray-700/50 rounded-lg">
                  <p className="text-sm text-gray-400">
                    {recognitionResults.transcription?.message || 
                     recognitionResults.results_summary?.transcription_message}
                  </p>
                </div>
              )}
            </div>
          ) : (
            <div className="p-4 bg-gray-700 rounded-lg">
              <p className="text-gray-400">No transcription results available</p>
            </div>
          )}
        </div>
      )}
      
      {/* Show a message when completed but no speaker results */}
      {recognitionStatus === 'completed' && (!speakerResults || !speakerResults.segments || speakerResults.segments.length === 0) && (
        <div className="bg-gray-800 text-white p-6 rounded-lg shadow-lg mb-4">
          <div className="flex items-start">
            <svg className="w-5 h-5 text-blue-400 mr-3 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
            </svg>
            <p className="text-gray-300">{recognitionMessage}</p>
          </div>
        </div>
      )}
      
      <style jsx>{`
        .spinner-xs {
          border: 2px solid rgba(255, 255, 255, 0.1);
          width: 14px;
          height: 14px;
          border-radius: 50%;
          border-left-color: #3b82f6;
          animation: spin 1s linear infinite;
        }
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
        .custom-scrollbar {
          scrollbar-width: thin;
          scrollbar-color: rgba(107, 114, 128, 0.5) rgba(31, 41, 55, 0.5);
        }
        .custom-scrollbar::-webkit-scrollbar {
          width: 8px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: rgba(31, 41, 55, 0.5);
          border-radius: 4px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background-color: rgba(107, 114, 128, 0.5);
          border-radius: 4px;
        }
      `}</style>
    </div>
  );
};

export default RecognitionPanel;
