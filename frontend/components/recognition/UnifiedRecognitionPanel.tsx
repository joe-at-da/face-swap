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
  correlations_count?: number;
  face_count?: number;
  speaker_count?: number;
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

interface CorrelationStats {
  total: number;
  high_confidence: number;
  medium_confidence: number;
  low_confidence: number;
  face_count: number;
  speaker_count: number;
  processing: boolean;
  error?: string;
}

interface TranscriptionSegment {
  id: number;
  type: string;
  start: number;
  end: number;
  text: string;
  speaker?: string;
  speaker_events?: any[];
  confidence: number;
}

interface TranscriptionData {
  text: string;
  segments: TranscriptionSegment[];
  language: string;
  duration: number;
}

interface IntegratedTimelineData {
  success: boolean;
  transcription: TranscriptionData;
  timeline: any[];
  correlations: any[];
  error?: string;
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
  const [correlationStats, setCorrelationStats] = useState<CorrelationStats>({
    total: 0,
    high_confidence: 0,
    medium_confidence: 0,
    low_confidence: 0,
    face_count: 0,
    speaker_count: 0,
    processing: false
  });
  const [isUpdatingCorrelations, setIsUpdatingCorrelations] = useState(false);
  const [transcriptionData, setTranscriptionData] = useState<TranscriptionData | null>(null);
  const [integratedTimeline, setIntegratedTimeline] = useState<IntegratedTimelineData | null>(null);
  const [isLoadingTranscription, setIsLoadingTranscription] = useState(false);
  const [transcriptionError, setTranscriptionError] = useState('');

  const fetchTranscriptionData = async () => {
    try {
      setIsLoadingTranscription(true);
      setTranscriptionError('');
      
      console.log('Fetching transcription data for captureId:', captureId);
      const response = await api.get(`/recognition/timeline/${captureId}/transcription`);
      console.log('Transcription data response:', response);
      
      // Handle different response formats
      const data = response.data || response;
      
      if (data && data.success) {
        // Ensure transcription data has the expected structure
        if (data.transcription) {
          setTranscriptionData(data.transcription);
          setIntegratedTimeline(data);
          console.log('Transcription data loaded successfully');
        } else {
          console.error('Transcription data missing in response:', data);
          setTranscriptionError('Invalid transcription data format');
          setTranscriptionData(null);
          setIntegratedTimeline(null);
        }
      } else {
        const errorMessage = data?.error || 'Failed to fetch transcription data';
        console.error('Transcription data error:', errorMessage);
        setTranscriptionError(errorMessage);
        setTranscriptionData(null);
        setIntegratedTimeline(null);
      }
    } catch (error) {
      console.error('Error fetching transcription data:', error);
      setTranscriptionError('Failed to fetch transcription data');
      setTranscriptionData(null);
      setIntegratedTimeline(null);
    } finally {
      setIsLoadingTranscription(false);
    }
  };

  useEffect(() => {
    if (captureId) {
      fetchStatus();
      fetchAudioInfo();
      fetchCorrelationStats();
      fetchTranscriptionData();
      
      // Set up polling interval
      const interval = setInterval(() => {
        fetchStatus();
        if (correlationStats.processing) {
          fetchCorrelationStats();
        }
      }, 5000);
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
            correlations_count: statusData.correlations_count,
            face_count: statusData.face_count,
            speaker_count: statusData.speaker_count,
            completed_at: statusData.completed_at,
            progress: statusData.completion_percentage || statusData.progress || 0,
            steps: statusData.steps || []
          };
          
          console.log('Mapped status with progress:', mappedStatus);
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
          const statusObj = {
            status: data.status,
            progress: data.progress || data.completion_percentage || 0,
            steps: data.steps || [],
            error: data.error,
            started_at: data.started_at,
            completed_at: data.completed_at,
            results: data.results
          };
          
          console.log('Setting recognition status with progress:', statusObj);
          setRecognitionStatus(statusObj);
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
      console.log('Fetching audio info for captureId:', captureId);
      const response = await api.get(`/capture/${captureId}/audio`);
      console.log('Audio info response:', response);
      
      if (response && response.data) {
        setAudioInfo(response.data);
      } else {
        setAudioInfo({
          file_path: null,
          file_name: null,
          source_url: null
        });
      }
    } catch (err) {
      console.error('Error fetching audio info:', err);
      // Set default audio info instead of null to prevent UI errors
      setAudioInfo({
        file_path: null,
        file_name: null,
        source_url: null
      });
    }
  };

  const fetchCorrelationStats = async () => {
    try {
      console.log('Fetching correlation stats for captureId:', captureId);
      const response = await api.get(`/recognition/timeline/${captureId}/correlations`);
      console.log('Correlation stats response:', response);
      
      if (response && response.success) {
        // Count confidence levels
        const correlations = response.correlations || [];
        const highConfidence = correlations.filter((c: any) => 
          c.confidence_level === 'high' || c.confidence_level === 'very_high'
        ).length;
        const mediumConfidence = correlations.filter((c: any) => 
          c.confidence_level === 'medium'
        ).length;
        const lowConfidence = correlations.filter((c: any) => 
          c.confidence_level === 'low' || c.confidence_level === 'very_low'
        ).length;
        
        setCorrelationStats({
          total: correlations.length,
          high_confidence: highConfidence,
          medium_confidence: mediumConfidence,
          low_confidence: lowConfidence,
          face_count: response.face_count || 0,
          speaker_count: response.speaker_count || 0,
          processing: false,
          error: undefined // Clear any previous errors
        });
      } else {
        // Keep existing stats but update processing status and error
        setCorrelationStats(prev => ({
          ...prev,
          total: prev.total || 0,
          high_confidence: prev.high_confidence || 0,
          medium_confidence: prev.medium_confidence || 0,
          low_confidence: prev.low_confidence || 0,
          face_count: prev.face_count || 0,
          speaker_count: prev.speaker_count || 0,
          processing: false,
          error: response?.error || 'Failed to fetch correlation stats'
        }));
      }
    } catch (err: any) {
      console.error('Error fetching correlation stats:', err);
      // Maintain existing stats but update error state
      setCorrelationStats(prev => ({
        ...prev,
        total: prev.total || 0,
        high_confidence: prev.high_confidence || 0,
        medium_confidence: prev.medium_confidence || 0,
        low_confidence: prev.low_confidence || 0,
        face_count: prev.face_count || 0,
        speaker_count: prev.speaker_count || 0,
        processing: false,
        error: err?.message || 'Error fetching correlation stats'
      }));
    }
  };
  
  const updateCorrelations = async () => {
    try {
      setIsUpdatingCorrelations(true);
      setCorrelationStats(prev => ({ ...prev, processing: true, error: undefined }));
      
      const response = await api.post(`/recognition/timeline/${captureId}/update-correlations`);
      console.log('Update correlations response:', response);
      
      if (response && response.success) {
        toast.success('Correlation detection updated successfully');
        // Fetch updated stats
        await fetchCorrelationStats();
      } else {
        const errorMessage = response?.error || 'Failed to update correlations';
        toast.error(errorMessage);
        setCorrelationStats(prev => ({
          ...prev,
          processing: false,
          error: errorMessage
        }));
      }
    } catch (err: any) {
      console.error('Error updating correlations:', err);
      const errorMessage = err?.message || 'Error updating correlations';
      toast.error(errorMessage);
      setCorrelationStats(prev => ({
        ...prev,
        processing: false,
        error: errorMessage
      }));
    } finally {
      setIsUpdatingCorrelations(false);
    }
  };
  
  const startRecognitionProcess = async () => {
    try {
      setIsStartingProcess(true);
      setError('');
      
      // Prepare the request data with the correct format
      const requestData = {
        video_id: captureId,
        save_output: true,
        options: {
          enable_speaker_identification: transcriptionOptions.enableSpeakerIdentification,
          enable_facial_recognition: transcriptionOptions.enableFacialRecognition
        }
      };
      
      console.log('Starting recognition process with options:', requestData);
      
      // Make the API call to start the recognition process using the combined-recognition endpoint
      const response = await api.post('/recognition/combined-recognition', requestData);
      
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
        const errorMessage = response?.error || response?.message || 'Failed to start recognition process. Please try again.';
        setError(errorMessage);
        toast.error(errorMessage);
      }
    } catch (err: any) {
      console.error('Error starting recognition process:', err);
      
      // Handle different error scenarios
      let errorMessage = 'Failed to start recognition process';
      
      if (err.response) {
        // The request was made and the server responded with a status code
        if (err.response.status === 400) {
          errorMessage = 'Invalid request: ' + (err.response.data?.message || 'Bad request');
        } else if (err.response.status === 401) {
          errorMessage = 'Authentication error: Please log in again';
        } else if (err.response.status === 403) {
          errorMessage = 'You do not have permission to perform this action';
        } else if (err.response.status === 404) {
          errorMessage = 'Recognition service endpoint not found';
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
    setTranscriptionOptions((prev: TranscriptionOptions) => ({
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

  // Render transcription timeline
  const renderTranscriptionTimeline = () => {
    if (isLoadingTranscription) {
      return (
        <div className="flex justify-center items-center h-40">
          <div className="spinner-sm"></div>
          <span className="ml-2">Loading transcription...</span>
        </div>
      );
    }
    
    if (transcriptionError) {
      return (
        <div className="text-red-400 p-3 border border-red-600 rounded-md text-sm">
          <p>Error loading transcription: {transcriptionError}</p>
          <button 
            onClick={fetchTranscriptionData}
            className="mt-2 px-3 py-1 bg-red-700 hover:bg-red-600 rounded-md text-xs"
          >
            Retry
          </button>
        </div>
      );
    }
    
    if (!transcriptionData || !transcriptionData.segments || transcriptionData.segments.length === 0) {
      return (
        <div className="text-gray-400 p-3 border border-gray-700 rounded-md text-sm">
          No transcription data available for this video.
        </div>
      );
    }

    // Get correlation data if available
    const correlations = integratedTimeline?.correlations || [];
    const hasCorrelations = correlations.length > 0;
    
    return (
      <div className="mt-4">
        <h3 className="text-lg font-medium mb-2">Transcription Timeline</h3>
        
        {/* Show correlation stats if available */}
        {hasCorrelations && (
          <div className="mb-4 p-3 bg-blue-900 bg-opacity-30 border border-blue-700 rounded-md">
            <h4 className="text-sm font-medium mb-1">Correlation Statistics</h4>
            <p className="text-xs text-gray-300">
              Found {correlations.length} correlations between face and voice recognition
            </p>
          </div>
        )}
        
        <div className="max-h-80 overflow-y-auto pr-2">
          {transcriptionData.segments.map((segment: TranscriptionSegment, index: number) => {
            // Find speaker color based on speaker name
            const speakerColor = segment.speaker ? 
              `hsl(${(segment.speaker.charCodeAt(0) * 10) % 360}, 70%, 50%)` : 
              '#6B7280';
            
            // Find any correlations that match this segment's time range
            const matchingCorrelations = hasCorrelations ? correlations.filter((corr: any) => {
              return (segment.start <= corr.end_time && segment.end >= corr.start_time);
            }) : [];
            
            // Use a different style if there are matching correlations
            const hasMatches = matchingCorrelations.length > 0;
            const borderColor = hasMatches ? '#10B981' : speakerColor; // Green for matches
            const bgColor = hasMatches ? 'rgba(16, 185, 129, 0.1)' : 'rgba(31, 41, 55, 0.8)';
            
            return (
              <div 
                key={`segment-${segment.id || index}`}
                className="mb-3 p-3 rounded-md border-l-4"
                style={{ borderLeftColor: borderColor, backgroundColor: bgColor }}
              >
                <div className="flex justify-between items-start mb-1">
                  <div className="flex items-center">
                    {segment.speaker && (
                      <span 
                        className="px-2 py-1 rounded-md text-xs font-medium mr-2"
                        style={{ backgroundColor: `${speakerColor}30` }}
                      >
                        {segment.speaker}
                      </span>
                    )}
                    <span className="text-gray-400 text-xs">
                      {formatDuration(segment.start)} - {formatDuration(segment.end)}
                    </span>
                  </div>
                  {segment.confidence && (
                    <span className="text-gray-500 text-xs">
                      {(segment.confidence * 100).toFixed(1)}% confidence
                    </span>
                  )}
                </div>
                <p className="text-sm">{segment.text}</p>
                
                {/* Show correlation details if any */}
                {hasMatches && (
                  <div className="mt-2 p-2 bg-gray-900 bg-opacity-50 rounded-sm border border-green-800 border-opacity-50">
                    <p className="text-xs font-medium text-green-400">
                      {matchingCorrelations.length} face-voice correlation{matchingCorrelations.length > 1 ? 's' : ''}
                    </p>
                    {matchingCorrelations.map((corr: any, i: number) => (
                      <p key={i} className="text-xs text-gray-400 mt-1">
                        Confidence: {(corr.confidence * 100).toFixed(1)}% 
                        ({formatDuration(corr.start_time)} - {formatDuration(corr.end_time)})
                      </p>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  return (
    <div className="bg-gray-800 text-white rounded-lg p-6 mb-6">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-semibold">Recognition & Transcription</h2>
      </div>
      
      {loading ? (
        <div className="flex justify-center items-center h-40">
          <div className="spinner"></div>
        </div>
      ) : error ? (
        <div className="text-red-400 p-4 border border-red-600 rounded-md">
          {error}
          <button 
            onClick={fetchStatus}
            className="mt-2 px-3 py-1 bg-red-700 hover:bg-red-600 rounded-md text-sm"
          >
            Retry
          </button>
        </div>
      ) : recognitionStatus ? (
        <div>
          <div className="mb-4">
            <div className="flex items-center">
              <div className={`w-3 h-3 rounded-full mr-2 ${
                recognitionStatus.status === 'completed' ? 'bg-green-500' : 
                recognitionStatus.status === 'processing' ? 'bg-blue-500' : 
                recognitionStatus.status === 'failed' ? 'bg-red-500' : 
                'bg-gray-500'
              }`}></div>
              <span className="font-medium">Status: </span>
              <span className="ml-1 capitalize">
                {recognitionStatus.status === 'not_started' ? 'Not Started' : 
                 recognitionStatus.status === 'processing' ? 'Processing' : 
                 recognitionStatus.status === 'scheduled' ? 'Scheduled' : 
                 recognitionStatus.status === 'completed' ? 'Completed' : 
                 recognitionStatus.status === 'failed' ? 'Failed' : 'Unknown'}
              </span>
              {recognitionStatus.status === 'processing' && (
                <div className="spinner-xs ml-2"></div>
              )}
            </div>

            {recognitionStatus.started_at && (
              <div className="text-sm text-gray-300 mt-1">
                Started: {new Date(recognitionStatus.started_at).toLocaleString()}
              </div>
            )}

            {recognitionStatus.completed_at && (
              <div className="text-sm text-gray-300 mb-1">
                Completed: {new Date(recognitionStatus.completed_at).toLocaleString()}
              </div>
            )}
          </div>
          
          {/* Display transcription timeline */}
          {renderTranscriptionTimeline()}
        </div>
      ) : null}

      {/* Processing Status */}
      {recognitionStatus?.status === 'processing' && (
        <div className="bg-blue-900 border border-blue-700 text-white px-4 py-3 rounded mb-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <div className="spinner-sm mr-2"></div>
              <span>Processing your audio...</span>
            </div>
            {recognitionStatus.progress !== undefined && (
              <span className="text-sm font-bold text-blue-300">{Math.round(recognitionStatus.progress)}%</span>
            )}
          </div>
          
          {/* Always show progress bar even if progress is 0 */}
          <div className="mt-4">
            {renderProgressBar(
              recognitionStatus.progress !== undefined ? recognitionStatus.progress : 0, 
              recognitionStatus.steps || []
            )}
          </div>
          
          {/* Display step information if available */}
          {recognitionStatus.steps && recognitionStatus.steps.length > 0 && (
            <div className="mt-2 text-sm text-blue-200">
              <p>Current step: {recognitionStatus.steps.find(s => s.status === 'in_progress')?.name || 'Initializing...'}</p>
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

      {/* Correlation Statistics */}
      {recognitionStatus?.status === 'completed' && (
        <div className="mt-6 bg-gray-800 dark:bg-gray-900 rounded-lg p-4">
          <h3 className="text-lg font-semibold mb-3 text-white">Correlation Statistics</h3>
          
          <div className="grid grid-cols-3 gap-4 mb-4">
            <div className="bg-gray-700 dark:bg-gray-800 rounded-lg p-3 text-center">
              <div className="text-2xl font-bold text-blue-400">{correlationStats.face_count}</div>
              <div className="text-sm text-gray-300">Face Detections</div>
            </div>
            <div className="bg-gray-700 dark:bg-gray-800 rounded-lg p-3 text-center">
              <div className="text-2xl font-bold text-green-400">{correlationStats.speaker_count}</div>
              <div className="text-sm text-gray-300">Speaker Segments</div>
            </div>
            <div className="bg-gray-700 dark:bg-gray-800 rounded-lg p-3 text-center">
              <div className="text-2xl font-bold text-purple-400">{correlationStats.total}</div>
              <div className="text-sm text-gray-300">Total Correlations</div>
            </div>
          </div>
          
          <div className="mb-4">
            <div className="flex justify-between mb-1">
              <span className="text-sm text-gray-300">Confidence Levels</span>
            </div>
            <div className="w-full bg-gray-700 rounded-full h-4 overflow-hidden">
              {correlationStats.total > 0 ? (
                <div className="flex h-full">
                  <div 
                    className="bg-yellow-500" 
                    style={{ width: `${(correlationStats.high_confidence / correlationStats.total) * 100}%` }}
                    title={`High Confidence: ${correlationStats.high_confidence}`}
                  ></div>
                  <div 
                    className="bg-purple-500" 
                    style={{ width: `${(correlationStats.medium_confidence / correlationStats.total) * 100}%` }}
                    title={`Medium Confidence: ${correlationStats.medium_confidence}`}
                  ></div>
                  <div 
                    className="bg-purple-700" 
                    style={{ width: `${(correlationStats.low_confidence / correlationStats.total) * 100}%` }}
                    title={`Low Confidence: ${correlationStats.low_confidence}`}
                  ></div>
                </div>
              ) : (
                <div className="h-full w-full bg-gray-600"></div>
              )}
            </div>
            <div className="flex justify-between text-xs text-gray-400 mt-1">
              <div className="flex items-center">
                <div className="w-3 h-3 bg-yellow-500 mr-1 rounded-sm"></div>
                <span>High: {correlationStats.high_confidence}</span>
              </div>
              <div className="flex items-center">
                <div className="w-3 h-3 bg-purple-500 mr-1 rounded-sm"></div>
                <span>Medium: {correlationStats.medium_confidence}</span>
              </div>
              <div className="flex items-center">
                <div className="w-3 h-3 bg-purple-700 mr-1 rounded-sm"></div>
                <span>Low: {correlationStats.low_confidence}</span>
              </div>
            </div>
          </div>
          
          <button
            onClick={updateCorrelations}
            disabled={isUpdatingCorrelations || correlationStats.processing}
            className={`w-full py-2 px-4 rounded-md font-medium focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-opacity-50 ${isUpdatingCorrelations || correlationStats.processing ? 'bg-gray-600 text-gray-300 cursor-not-allowed' : 'bg-indigo-600 hover:bg-indigo-700 text-white'}`}
          >
            {isUpdatingCorrelations || correlationStats.processing ? (
              <div className="flex justify-center items-center">
                <div className="spinner-xs mr-2"></div>
                <span>Updating Correlations...</span>
              </div>
            ) : (
              'Run Enhanced Correlation Detection'
            )}
          </button>
          
          {correlationStats.error && (
            <div className="mt-2 text-sm text-red-400">{correlationStats.error}</div>
          )}
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
            
            <h4 className="font-medium mt-3 mb-1">Correlation Stats</h4>
            <pre className="overflow-x-auto">
              {JSON.stringify(correlationStats, null, 2)}
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