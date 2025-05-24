import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { useAuth } from '../../contexts/AuthContext';
import { toast } from 'react-toastify';
import * as Path from 'path';
import { api } from '../../utils/api';
import { useRouter } from 'next/router';

// API base URL
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api/v1';

interface UnifiedRecognitionPanelProps {
  captureId: number;
  onProcessingComplete?: () => void;
}

interface RecognitionStep {
  name: string;
  status: 'waiting' | 'in_progress' | 'completed' | 'failed';
  progress?: number;
}

interface RecognitionStatus {
  status: 'not_started' | 'scheduled' | 'processing' | 'completed' | 'failed';
  progress?: number;
  steps?: RecognitionStep[];
  error?: string;
  started_at?: string;
  completed_at?: string;
  results?: any;
}

interface TranscriptionOptions {
  enableSpeakerIdentification: boolean;
  enableFacialRecognition: boolean;
}

interface AudioInfo {
  file_path: string | null;
  file_name: string | null;
  source_url: string | null;
}

const UnifiedRecognitionPanel: React.FC<UnifiedRecognitionPanelProps> = ({
  captureId,
  onProcessingComplete
}) => {
  const router = useRouter();
  const { token } = useAuth();
  const [recognitionStatus, setRecognitionStatus] = useState<RecognitionStatus | null>(null);
  const [transcriptionOptions, setTranscriptionOptions] = useState<TranscriptionOptions>({
    enableSpeakerIdentification: true,
    enableFacialRecognition: true
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [isStartingProcess, setIsStartingProcess] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [refreshInterval, setRefreshInterval] = useState<NodeJS.Timeout | null>(null);
  const [showDebugInfo, setShowDebugInfo] = useState(false);
  const [audioInfo, setAudioInfo] = useState<AudioInfo | null>(null);

  useEffect(() => {
    if (captureId) {
      fetchStatus();
      
      // Set up polling interval
      const interval = setInterval(fetchStatus, 5000);
      setRefreshInterval(interval);
      
      return () => {
        if (interval) clearInterval(interval);
      };
    }
  }, [captureId]);

  useEffect(() => {
    return () => {
      if (refreshInterval) {
        clearInterval(refreshInterval);
        console.log('Cleared refresh interval on unmount');
      }
    };
  }, [refreshInterval]);

  useEffect(() => {
    // If processing is completed, stop polling
    if (recognitionStatus?.status === 'completed' && refreshInterval) {
      clearInterval(refreshInterval);
      setRefreshInterval(null);
      if (onProcessingComplete) {
        onProcessingComplete();
      }
    }
  }, [recognitionStatus?.status, refreshInterval, onProcessingComplete]);

  const fetchStatus = async () => {
    try {
      setIsRefreshing(true);
      
      // First try to get detailed status
      try {
        console.log('Fetching detailed status for captureId:', captureId);
        const detailedResponse = await api.get(`/recognition/detailed-status/${captureId}`);
        
        console.log('Detailed status response:', detailedResponse);
        // Check if detailedResponse has a status object or direct properties
        if (detailedResponse && detailedResponse.success) {
          let statusData: any;
          
          // Handle case where status info is nested under 'status' property
          if (detailedResponse.status && typeof detailedResponse.status === 'object') {
            statusData = detailedResponse.status;
          } else {
            // Handle case where status info is directly in the response
            statusData = detailedResponse;
          }
          
          // Map the backend status format to our component's format
          const mappedStatus: RecognitionStatus = {
            status: (statusData.status as "not_started" | "scheduled" | "processing" | "completed" | "failed") || 'not_started',
            started_at: statusData.started_at,
            completed_at: statusData.completed_at,
            progress: statusData.completion_percentage || 0,
          };
          
          setRecognitionStatus(mappedStatus);
          setLoading(false);
          setError('');
          
          // Also fetch audio info
          fetchAudioInfo();
          
          return;
        }
      } catch (detailedError) {
        console.error('Error fetching detailed status:', detailedError);
        // Fall back to basic status if detailed status fails
      }
      
      // Fallback to basic status endpoint
      const response = await api.get(`/recognition/recognition-status/${captureId}`);
      console.log('Basic status response:', response);
      
      if (response) {
        const data = response;
        
        if (data.status) {
          setRecognitionStatus({
            status: data.status,
            progress: data.progress || 0,
            steps: data.steps || [],
            error: data.error,
            started_at: data.started_at,
            completed_at: data.completed_at,
            results: data.results
          });
        } else {
          setRecognitionStatus({
            status: 'not_started',
            progress: 0
          });
        }
        
        setLoading(false);
        setError('');
        
        // Also fetch audio info
        fetchAudioInfo();
      }
    } catch (err) {
      console.error('Error fetching recognition status:', err);
      setError('Failed to load recognition status. Please try again.');
      setLoading(false);
    } finally {
      setIsRefreshing(false);
    }
  };
  
  const fetchAudioInfo = async () => {
    try {
      // Use the capture endpoint instead of audio-info which doesn't exist
      const response = await api.get(`/capture/${captureId}`);
      
      if (response) {
        // Extract audio information from capture data
        setAudioInfo({
          file_path: response.audio_path || (response.file_path ? response.file_path.replace('.mp4', '.audio.mp3') : null),
          file_name: response.audio_path ? Path.basename(response.audio_path) : 
                    (response.file_path ? Path.basename(response.file_path).replace('.mp4', '.audio.mp3') : null),
          source_url: response.url || null
        });
      }
    } catch (err) {
      console.error('Error fetching audio info:', err);
      // Don't set an error state here, as this is supplementary information
    }
  };

  // Helper function to get basename from path
  const basename = (path: string) => {
    return path ? Path.basename(path) : '';
  };
  
  const startRecognitionProcess = async () => {
    try {
      setIsStartingProcess(true);
      setError('');
      
      // Prepare options for the API call
      const options = {
        enable_speaker_identification: transcriptionOptions.enableSpeakerIdentification,
        enable_facial_recognition: transcriptionOptions.enableFacialRecognition
      };
      
      console.log('Starting recognition process with options:', options);
      
      // Make the API call to start the recognition process
      const response = await api.post(`/recognition/start-recognition/${captureId}`, options);
      
      console.log('Recognition start response:', response);
      
      if (response && response.success) {
        toast.success('Recognition process started successfully!');
        
        // Update the status immediately to show it's processing
        setRecognitionStatus({
          status: 'processing',
          progress: 0,
          started_at: new Date().toISOString()
        });
        
        // If there's no refresh interval, start one
        if (!refreshInterval) {
          const interval = setInterval(fetchStatus, 5000);
          setRefreshInterval(interval);
        }
      } else {
        const errorMessage = response?.error || 'Failed to start recognition process. Please try again.';
        setError(errorMessage);
        toast.error(errorMessage);
      }
    } catch (err) {
      console.error('Error starting recognition process:', err);
      const errorMessage = 'Failed to start recognition process. Please try again.';
      setError(errorMessage);
      toast.error(errorMessage);
    } finally {
      setIsStartingProcess(false);
    }
  };
  
  const handleOptionChange = (option: keyof TranscriptionOptions) => {
    setTranscriptionOptions(prev => ({
      ...prev,
      [option]: !prev[option]
    }));
  };
  
  const getStepName = (index: number): string => {
    const stepNames = [
      'Preparing Audio',
      'Transcribing Audio',
      'Analyzing Speakers',
      'Detecting Faces',
      'Generating Timeline'
    ];
    
    return index < stepNames.length ? stepNames[index] : `Step ${index + 1}`;
  };
  
  const getStatusColor = (status: string): string => {
    switch (status) {
      case 'completed':
        return 'text-green-400';
      case 'in_progress':
        return 'text-blue-400';
      case 'failed':
        return 'text-red-400';
      case 'waiting':
      default:
        return 'text-gray-400';
    }
  };
  
  const getStatusBgColor = (status: string): string => {
    switch (status) {
      case 'completed':
        return 'bg-green-900';
      case 'in_progress':
        return 'bg-blue-900';
      case 'failed':
        return 'bg-red-900';
      case 'waiting':
      default:
        return 'bg-gray-700';
    }
  };

  // Calculate estimated time remaining based on progress and start time
  const calculateTimeRemaining = (startedAt: string, progress: number): string => {
    if (!startedAt || progress <= 0) return 'Calculating...';
    
    const startTime = new Date(startedAt).getTime();
    const now = new Date().getTime();
    const elapsedMs = now - startTime;
    
    // If we've been running for less than 10 seconds, don't try to estimate
    if (elapsedMs < 10000) return 'Calculating...';
    
    // Calculate estimated total time based on progress so far
    const estimatedTotalMs = (elapsedMs / progress) * 100;
    const remainingMs = estimatedTotalMs - elapsedMs;
    
    // Convert to minutes and seconds
    const remainingMinutes = Math.floor(remainingMs / 60000);
    const remainingSeconds = Math.floor((remainingMs % 60000) / 1000);
    
    if (remainingMinutes > 0) {
      return `~${remainingMinutes}m ${remainingSeconds}s remaining`;
    } else {
      return `~${remainingSeconds}s remaining`;
    }
  };
  
  // Render enhanced progress bar with steps
  const renderProgressBar = (progress: number, steps: RecognitionStep[] = []) => {
    // Calculate color based on progress
    const getProgressColor = () => {
      if (progress < 30) return 'bg-blue-500';
      if (progress < 70) return 'bg-blue-400';
      return 'bg-blue-300';
    };
    
    return (
      <div className="w-full">
        {/* Main progress bar */}
        <div className="w-full bg-gray-700 rounded-full h-4 mb-3">
          <div 
            className={`h-4 rounded-full ${getProgressColor()}`} 
            style={{ width: `${Math.min(100, Math.max(0, progress))}%` }}
          ></div>
        </div>
        
        {/* Steps indicators */}
        {steps.length > 0 && (
          <div className="grid grid-cols-1 gap-2 mt-3">
            {steps.map((step, index) => (
              <div key={index} className="flex items-center">
                <div className={`w-6 h-6 rounded-full flex items-center justify-center mr-2 ${getStatusBgColor(step.status)}`}>
                  {step.status === 'completed' ? (
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                  ) : step.status === 'in_progress' ? (
                    <div className="spinner-xs"></div>
                  ) : step.status === 'failed' ? (
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  ) : (
                    <span className="text-xs text-white">{index + 1}</span>
                  )}
                </div>
                <div className="flex-1">
                  <div className="flex justify-between items-center">
                    <span className={`text-sm ${getStatusColor(step.status)}`}>{step.name || getStepName(index)}</span>
                    {step.progress !== undefined && step.status === 'in_progress' && (
                      <span className="text-xs text-gray-400">{Math.round(step.progress)}%</span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  };

  if (loading && !recognitionStatus) {
    return (
      <div className="bg-gray-800 text-white rounded-lg p-6 mb-6">
        <div className="flex justify-center items-center h-32">
          <div className="spinner"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-gray-800 text-white rounded-lg p-6 mb-6">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-semibold">Recognition & Transcription</h2>
      </div>

      {error && (
        <div className="bg-red-900 border border-red-700 text-white px-4 py-3 rounded mb-4">
          {error}
        </div>
      )}

      {/* Status Summary */}
      <div className="mb-6">
        <div className="flex items-center mb-2">
          <div className={`w-3 h-3 rounded-full mr-2 ${
            recognitionStatus?.status === 'completed' ? 'bg-green-500' :
            recognitionStatus?.status === 'processing' ? 'bg-blue-500' :
            recognitionStatus?.status === 'failed' ? 'bg-red-500' :
            'bg-gray-500'
          }`}></div>
          <span className="font-medium">Status: </span>
          <span className="ml-1 capitalize">
            {recognitionStatus?.status === 'not_started' ? 'Not Started' : 
             recognitionStatus?.status === 'processing' ? 'Processing' : 
             recognitionStatus?.status === 'completed' ? 'Completed' :
             recognitionStatus?.status === 'failed' ? 'Failed' :
             recognitionStatus?.status === 'scheduled' ? 'Scheduled' : 'Unknown'}
          </span>
          {isRefreshing && !isStartingProcess && (
            <div className="spinner-xs ml-2"></div>
          )}
        </div>

        {recognitionStatus?.started_at && (
          <div className="text-sm text-gray-300 mb-1">
            Started: {new Date(recognitionStatus.started_at).toLocaleString()}
          </div>
        )}

        {recognitionStatus?.completed_at && (
          <div className="text-sm text-gray-300 mb-1">
            Completed: {new Date(recognitionStatus.completed_at).toLocaleString()}
          </div>
        )}
      </div>

      {/* Processing Status */}
      {recognitionStatus?.status === 'processing' && (
        <div className="bg-blue-900 border border-blue-700 text-white px-4 py-3 rounded mb-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <div className="spinner-sm mr-2"></div>
              <span>Processing your audio...</span>
            </div>
            {recognitionStatus.progress !== undefined && (
              <span className="text-sm font-medium">{Math.round(recognitionStatus.progress)}%</span>
            )}
          </div>
          
          {recognitionStatus.progress !== undefined && (
            <div className="mt-4">
              {renderProgressBar(recognitionStatus.progress, recognitionStatus.steps || [])}
            </div>
          )}
          
          {/* Estimated time remaining */}
          {recognitionStatus.started_at && recognitionStatus.progress !== undefined && recognitionStatus.progress > 0 && (
            <div className="text-sm text-blue-300 mt-2">
              {calculateTimeRemaining(recognitionStatus.started_at, recognitionStatus.progress)}
            </div>
          )}
        </div>
      )}

      {/* Recognition Options */}
      <div className="mb-6">
        <h3 className="text-lg font-medium mb-3">Recognition Options</h3>
        <div className="space-y-3">
          <div className="flex items-center">
            <input
              type="checkbox"
              id="enableSpeakerIdentification"
              checked={transcriptionOptions.enableSpeakerIdentification}
              onChange={() => handleOptionChange('enableSpeakerIdentification')}
              disabled={isStartingProcess || recognitionStatus?.status === 'processing'}
              className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-600 rounded"
            />
            <label htmlFor="enableSpeakerIdentification" className="ml-2 block text-sm">
              Enable Speaker Identification
            </label>
          </div>
          
          <div className="flex items-center">
            <input
              type="checkbox"
              id="enableFacialRecognition"
              checked={transcriptionOptions.enableFacialRecognition}
              onChange={() => handleOptionChange('enableFacialRecognition')}
              disabled={isStartingProcess || recognitionStatus?.status === 'processing'}
              className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-600 rounded"
            />
            <label htmlFor="enableFacialRecognition" className="ml-2 block text-sm">
              Enable Facial Recognition
            </label>
          </div>
        </div>
      </div>

      {/* Buttons for Recognition Actions */}
      <div className="mt-4 space-y-3">
        {/* View Results Button (only shown when completed) */}
        {recognitionStatus?.status === 'completed' && (
          <button
            onClick={() => router.push(`/recognition/results/${captureId}`)}
            className="w-full py-2 px-4 rounded-md font-medium focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-opacity-50 bg-green-600 hover:bg-green-700 text-white"
          >
            View Results
          </button>
        )}

        {/* Start/Restart Button */}
        <button
          onClick={startRecognitionProcess}
          disabled={isStartingProcess || recognitionStatus?.status === 'processing'}
          className={`w-full py-2 px-4 rounded-md font-medium focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-opacity-50 ${
            isStartingProcess || recognitionStatus?.status === 'processing'
              ? 'bg-gray-600 text-gray-300 cursor-not-allowed' 
              : 'bg-blue-600 hover:bg-blue-700 text-white'
          }`}
        >
          {isStartingProcess ? (
            <div className="flex justify-center items-center">
              <div className="spinner-xs mr-2"></div>
              <span>Starting Process...</span>
            </div>
          ) : recognitionStatus?.status === 'processing' ? (
            <div className="flex justify-center items-center">
              <div className="spinner-xs mr-2"></div>
              <span>Processing...</span>
            </div>
          ) : recognitionStatus?.status === 'completed' ? (
            'Restart Recognition'
          ) : recognitionStatus?.status === 'failed' ? (
            'Retry Recognition'
          ) : (
            'Start Recognition Process'
          )}
        </button>
      </div>

      {/* Debug Information */}
      <div className="mt-4 border-t border-gray-700 pt-4">
        <button
          onClick={() => setShowDebugInfo(!showDebugInfo)}
          className="flex items-center text-gray-400 hover:text-gray-300 focus:outline-none"
        >
          <svg 
            xmlns="http://www.w3.org/2000/svg" 
            className={`h-4 w-4 mr-1 transform transition-transform ${showDebugInfo ? 'rotate-90' : ''}`} 
            fill="none" 
            viewBox="0 0 24 24" 
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
          Debug Information
        </button>
        
        {showDebugInfo && (
          <div className="mt-2 p-3 bg-gray-900 rounded-lg text-xs text-gray-400 font-mono">
            <h4 className="font-medium mb-1">Audio Information</h4>
            {audioInfo ? (
              <div>
                <div>Audio File Path: {audioInfo.file_path}</div>
                <div>Audio File Name: {audioInfo.file_name}</div>
                <div>Audio Source URL: {audioInfo.source_url}</div>
              </div>
            ) : (
              <div>No audio information available</div>
            )}
            
            <h4 className="font-medium mt-3 mb-1">Recognition Status</h4>
            <pre className="overflow-x-auto">
              {JSON.stringify(recognitionStatus, null, 2)}
            </pre>
          </div>
        )}
      </div>

      <style jsx>{`
        .spinner {
          border: 4px solid rgba(255, 255, 255, 0.1);
          width: 36px;
          height: 36px;
          border-radius: 50%;
          border-left-color: #3b82f6;
          animation: spin 1s linear infinite;
        }
        .spinner-sm {
          border: 3px solid rgba(255, 255, 255, 0.1);
          width: 20px;
          height: 20px;
          border-radius: 50%;
          border-left-color: #3b82f6;
          animation: spin 1s linear infinite;
        }
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
      `}</style>
    </div>
  );
};

// Helper function to format duration in seconds to HH:MM:SS
const formatDuration = (seconds: number): string => {
  if (!seconds) return '00:00:00';
  
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);
  
  return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
};

export default UnifiedRecognitionPanel;