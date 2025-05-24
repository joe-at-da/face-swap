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
        const detailedResponse = await api.get(`/recognition/status/detailed-status/${captureId}`);
        
        console.log('Detailed status response:', detailedResponse);
        const detailedData = detailedResponse as { success: boolean; status?: string; video_id?: number; progress?: any; completion_percentage?: number; started_at?: string; completed_at?: string };
        if (detailedData.success) {
          // The backend returns the status information directly in the response, not nested under a 'status' property
          const statusData = detailedData;
          
          // Map the backend status format to our component's format
          const mappedStatus: RecognitionStatus = {
            status: statusData.status as "not_started" | "scheduled" | "processing" | "completed" | "failed" || 'not_started',
            started_at: statusData.started_at,
            completed_at: statusData.completed_at,
            // Use completion_percentage directly if available, otherwise try to get it from progress
            progress: statusData.completion_percentage || statusData.progress?.completion_percentage || 0,
            steps: []
          };
          
          // Map steps if available
          if (statusData.progress?.steps) {
            mappedStatus.steps = statusData.progress.steps.map((step: any) => ({
              name: step.name,
              status: step.status === 'completed' ? 'completed' : 
                     step.status === 'failed' ? 'failed' : 'in_progress'
            }));
          }
          
          // Add error if present
          if (statusData.progress?.error) {
            mappedStatus.error = statusData.progress.error;
          }
          
          setRecognitionStatus(mappedStatus);
        }
      } catch (detailedErr) {
        // If detailed status fails, fall back to basic status
        console.log('Falling back to basic status endpoint for captureId:', captureId);
        const basicResponse = await api.get(`/recognition/recognition-status/${captureId}`);
        
        console.log('Basic status response:', basicResponse);
        const basicData = basicResponse as { success: boolean; status?: string; video_id?: number; started_at?: string; completed_at?: string };
        if (basicData.success) {
          // The backend returns the status information directly in the response, not nested under a 'status' property
          const statusData = basicData;
          
          // Map the basic status
          const mappedStatus: RecognitionStatus = {
            status: statusData.status as "not_started" | "scheduled" | "processing" | "completed" | "failed" || 'not_started',
            started_at: statusData.started_at,
            completed_at: statusData.completed_at,
            progress: 0 // No progress info in basic status
          };
          
          setRecognitionStatus(mappedStatus);
        }
      }
      
      // Fetch audio info if not already loaded
      if (!audioInfo) {
        fetchAudioInfo();
      }
      
      setLoading(false);
      setIsRefreshing(false);
    } catch (err) {
      console.error('Error fetching recognition status:', err);
      setError('Failed to fetch recognition status');
      setLoading(false);
      setIsRefreshing(false);
    }
  };

  const fetchAudioInfo = async () => {
    try {
      // Use the api utility to get capture details
      const response = await api.get(`/capture/${captureId}`);
      
      const captureData = response as {
        file_path?: string;
        video_path?: string;
        audio_path?: string;
        url?: string;
      };
      
      // Extract audio information from capture data
      if (captureData) {
        const audioInfo = {
          file_path: captureData.audio_path || 
                    (captureData.file_path ? captureData.file_path.replace('.mp4', '.audio.mp3') : null),
          file_name: captureData.audio_path ? Path.basename(captureData.audio_path) : 
                    (captureData.file_path ? Path.basename(captureData.file_path).replace('.mp4', '.audio.mp3') : null),
          source_url: captureData.url || null
        };
        
        console.log('Audio info:', audioInfo);
        setAudioInfo(audioInfo);
      }
    } catch (err) {
      console.error('Error fetching audio info:', err);
    }
  };

  // Helper function to get basename from path
  const basename = (path: string) => {
    return path.split('/').pop() || path;
  };

  const startRecognitionProcess = async () => {
    try {
      setIsStartingProcess(true);
      setError('');
      
      // Check if we have valid capture data before proceeding
      if (!captureId) {
        setError('Invalid capture ID');
        toast.error('Cannot start recognition: Invalid capture ID');
        return;
      }
      
      // Prepare the request data
      const requestData = {
        video_id: captureId,
        save_output: true,
        options: {
          enable_speaker_identification: transcriptionOptions.enableSpeakerIdentification,
          enable_facial_recognition: transcriptionOptions.enableFacialRecognition
        }
      };
      
      // Call the combined recognition endpoint
      const response = await api.post('/recognition/combined-recognition', requestData);
      
      const responseData = response as { success: boolean; message?: string; error?: string };
      
      if (responseData.success) {
        toast.success('Recognition process started successfully');
        // Fetch the updated status
        fetchStatus();
        
        // Set up polling to regularly check status
        if (refreshInterval) {
          clearInterval(refreshInterval);
        }
        
        // Poll every 3 seconds
        const interval = setInterval(() => {
          fetchStatus();
        }, 3000);
        
        setRefreshInterval(interval);
      } else {
        const errorMessage = responseData.error || responseData.message || 'Failed to start recognition process';
        setError(errorMessage);
        toast.error(errorMessage);
      }
    } catch (err: any) {
      console.error('Error starting recognition process:', err);
      
      // Handle different error scenarios
      let errorMessage = 'Failed to start recognition process';
      
      if (err.response) {
        // The request was made and the server responded with a status code
        // that falls out of the range of 2xx
        if (err.response.status === 400) {
          errorMessage = 'Invalid request: ' + (err.response.data?.message || 'Bad request');
        } else if (err.response.status === 401) {
          errorMessage = 'Authentication error: Please log in again';
        } else if (err.response.status === 403) {
          errorMessage = 'You do not have permission to perform this action';
        } else if (err.response.status === 404) {
          errorMessage = 'Capture not found or recognition service unavailable';
        } else if (err.response.status === 409) {
          errorMessage = 'Recognition process is already in progress for this capture';
        } else if (err.response.status >= 500) {
          errorMessage = 'Server error: ' + (err.response.data?.message || 'Please try again later');
        }
      } else if (err.request) {
        // The request was made but no response was received
        errorMessage = 'No response from server. Please check your network connection.';
      }
      
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
    switch (index) {
      case 0: return 'Initialization';
      case 1: return 'Audio Processing';
      case 2: return 'Speaker Recognition';
      case 3: return 'Facial Recognition';
      case 4: return 'Transcription';
      default: return `Step ${index + 1}`;
    }
  };

  const getStatusColor = (status: string): string => {
    switch (status) {
      case 'not_started':
        return 'text-gray-300';
      case 'scheduled':
        return 'text-blue-300';
      case 'processing':
        return 'text-blue-300';
      case 'completed':
        return 'text-green-300';
      case 'failed':
        return 'text-red-300';
      default:
        return 'text-gray-300';
    }
  };

  const getStatusBgColor = (status: string): string => {
    switch (status) {
      case 'not_started':
        return 'bg-gray-700';
      case 'scheduled':
        return 'bg-blue-900';
      case 'processing':
        return 'bg-blue-900';
      case 'completed':
        return 'bg-green-900';
      case 'failed':
        return 'bg-red-900';
      default:
        return 'bg-gray-700';
    }
  };

  // Calculate estimated time remaining based on progress and start time
  const calculateTimeRemaining = (startedAt: string, progress: number): string => {
    if (!startedAt || progress <= 0) return 'Calculating...';
    
    const startTime = new Date(startedAt).getTime();
    const currentTime = new Date().getTime();
    const elapsedMs = currentTime - startTime;
    
    // Calculate total time based on elapsed time and progress
    const totalEstimatedMs = (elapsedMs / progress) * 100;
    const remainingMs = totalEstimatedMs - elapsedMs;
    
    // Convert to minutes and seconds
    const remainingMinutes = Math.floor(remainingMs / 60000);
    const remainingSeconds = Math.floor((remainingMs % 60000) / 1000);
    
    if (remainingMinutes > 0) {
      return `${remainingMinutes} min ${remainingSeconds} sec`;
    } else {
      return `${remainingSeconds} seconds`;
    }
  };
  
  // Render enhanced progress bar with steps
  const renderProgressBar = (progress: number, steps: RecognitionStep[] = []) => {
    // Calculate color based on progress
    const getProgressColor = () => {
      if (progress < 30) return 'bg-blue-600';
      if (progress < 60) return 'bg-indigo-500';
      if (progress < 90) return 'bg-purple-500';
      return 'bg-green-500';
    };
    
    return (
      <div className="space-y-2">
        {/* Main progress bar */}
        <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
          <div 
            className={`h-full ${getProgressColor()} transition-all duration-500 ease-out`}
            style={{ width: `${progress}%` }}
          ></div>
        </div>
        
        {/* Progress percentage */}
        <div className="flex justify-between text-xs text-gray-300">
          <span>{progress.toFixed(1)}% Complete</span>
          {progress < 100 && (
            <span>{(100 - progress).toFixed(1)}% Remaining</span>
          )}
        </div>
        
        {/* Step indicators */}
        {steps.length > 0 && (
          <div className="grid grid-cols-5 gap-2 mt-3">
            {steps.map((step, index) => (
              <div key={index} className="text-center">
                <div className={`h-1.5 rounded-full ${
                  step.status === 'completed' ? 'bg-green-500' : 
                  step.status === 'in_progress' ? 'bg-blue-500' : 
                  step.status === 'failed' ? 'bg-red-500' : 'bg-gray-700'
                }`}></div>
                <div className="text-xs mt-1 text-gray-300">
                  {step.name || getStepName(index)}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }

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

      {/* Status Overview */}
      <div className="mb-6">
        <div className="flex items-center mb-2">
          <span className="font-semibold mr-2">Status:</span>
          <span className={`px-2 py-1 rounded-full text-sm ${getStatusBgColor(recognitionStatus?.status || 'not_started')} ${getStatusColor(recognitionStatus?.status || 'not_started')}`}>
            {typeof recognitionStatus?.status === 'string' ? recognitionStatus.status.replace('_', ' ') : 'Not Started'}
          </span>
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
              <div className="spinner-sm mr-3"></div>
              <h3 className="font-bold">Processing in progress</h3>
            </div>
            {recognitionStatus.started_at && (
              <div className="text-sm text-blue-300">
                Started {new Date(recognitionStatus.started_at).toLocaleTimeString()}
              </div>
            )}
          </div>
          
          {recognitionStatus.progress !== undefined && (
            <div className="mt-4">
              {renderProgressBar(recognitionStatus.progress, recognitionStatus.steps || [])}
            </div>
          )}
          
          {/* Estimated time remaining */}
          {recognitionStatus.progress && recognitionStatus.progress > 0 && recognitionStatus.started_at && (
            <div className="mt-3 text-sm text-blue-300">
              <div className="flex items-center">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span>
                  {recognitionStatus.progress < 100 ? (
                    <>Estimated time remaining: {calculateTimeRemaining(recognitionStatus.started_at, recognitionStatus.progress)}</>
                  ) : (
                    'Finishing up...'
                  )}
                </span>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Completed State */}
      {recognitionStatus?.status === 'completed' && (
        <div className="bg-green-900 border border-green-700 text-white px-4 py-3 rounded mb-4">
          <div className="flex items-center mb-2">
            <svg className="w-5 h-5 text-green-300 mr-2" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
            <h3 className="font-bold">Processing completed</h3>
          </div>
          
          <div className="text-sm">
            {recognitionStatus.started_at && recognitionStatus.completed_at && (
              <div className="mb-1">
                Duration: {formatDuration((new Date(recognitionStatus.completed_at).getTime() - new Date(recognitionStatus.started_at).getTime()) / 1000)}
              </div>
            )}
          </div>
          
          {/* Button to view recognition results */}
          <button
            onClick={() => router.push(`/recognition/results/${captureId}`)}
            className="mt-3 bg-green-700 hover:bg-green-800 text-white py-1 px-3 rounded text-sm"
          >
            View Results
          </button>
        </div>
      )}

      {/* Not Started State */}
      {(!recognitionStatus || !recognitionStatus.status || recognitionStatus.status === 'not_started') && (
        <div className="bg-gray-900 rounded-lg p-6 mb-6">
          <h3 className="text-lg font-semibold mb-4">Start Recognition Process</h3>
          
          <div className="mb-6">
            <div className="mb-4">
              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  className="form-checkbox h-4 w-4 text-blue-600 rounded focus:ring-blue-500"
                  checked={transcriptionOptions.enableSpeakerIdentification}
                  onChange={() => handleOptionChange('enableSpeakerIdentification')}
                />
                <span>Enable Speaker Identification</span>
              </label>
              <p className="text-sm text-gray-400 ml-6 mt-1">
                Identifies who is speaking in each segment of the audio
              </p>
            </div>
            
            <div>
              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  className="form-checkbox h-4 w-4 text-blue-600 rounded focus:ring-blue-500"
                  checked={transcriptionOptions.enableFacialRecognition}
                  onChange={() => handleOptionChange('enableFacialRecognition')}
                />
                <span>Enable Facial Recognition</span>
              </label>
              <p className="text-sm text-gray-400 ml-6 mt-1">
                Identifies faces in the video and matches them with speakers
              </p>
            </div>
          </div>
          
          <button
            onClick={startRecognitionProcess}
            disabled={isStartingProcess}
            className={`w-full py-2 px-4 rounded-md font-medium focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-opacity-50 ${
              isStartingProcess 
                ? 'bg-gray-600 text-gray-300 cursor-not-allowed' 
                : 'bg-blue-600 hover:bg-blue-700 text-white'
            }`}
          >
            {isStartingProcess ? (
              <div className="flex justify-center items-center">
                <div className="spinner-xs mr-2"></div>
                <span>Starting Process...</span>
              </div>
            ) : (
              'Start Recognition Process'
            )}
          </button>
        </div>
      )}

      {/* Completed State */}
      {recognitionStatus?.status === 'completed' && (
        <div className="bg-green-900 border border-green-700 text-white px-4 py-3 rounded mb-4">
          <div className="flex items-center mb-2">
            <svg className="w-5 h-5 text-green-300 mr-2" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
            <h3 className="font-bold">Processing completed</h3>
          </div>
          
          <div className="text-sm">
            {recognitionStatus.started_at && recognitionStatus.completed_at && (
              <div className="mb-1">
                Duration: {formatDuration((new Date(recognitionStatus.completed_at).getTime() - new Date(recognitionStatus.started_at).getTime()) / 1000)}
              </div>
            )}
          </div>
          
          {recognitionStatus.results && (
            <div className="mt-3 grid grid-cols-2 gap-4 text-sm">
              <div className="bg-green-800 p-3 rounded">
                <h4 className="font-medium mb-2">Transcription</h4>
                <div className="flex justify-between">
                  <span>Duration</span>
                  <span>{recognitionStatus.results.duration ? formatDuration(recognitionStatus.results.duration) : 'N/A'}</span>
                </div>
                <div className="flex justify-between">
                  <span>Words</span>
                  <span>{recognitionStatus.results.word_count || 0}</span>
                </div>
              </div>
              
              <div className="bg-green-800 p-3 rounded">
                <h4 className="font-medium mb-2">Recognition</h4>
                <div className="flex justify-between">
                  <span>Speakers</span>
                  <span>{recognitionStatus.results.identified_speakers || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span>Face Samples</span>
                  <span>{recognitionStatus.results.face_samples || 0}</span>
                </div>
              </div>
            </div>
          )}
          
          <div className="flex justify-end mt-4">
            <button
              onClick={() => window.location.href = `/transcriptions`}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-opacity-50 transition-colors"
            >
              View Full Transcript
            </button>
          </div>
        </div>
      )}

      {/* Error Message */}
      {recognitionStatus?.status === 'failed' && recognitionStatus.error && (
        <div className="bg-red-900 border border-red-700 text-white px-4 py-3 rounded mb-4">
          <h3 className="font-bold mb-2">Processing Failed</h3>
          <p>{recognitionStatus.error}</p>
        </div>
      )}

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
