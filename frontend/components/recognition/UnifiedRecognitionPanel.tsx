import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import { useAuth } from '../../contexts/AuthContext';
import { toast } from 'react-toastify';
import { api } from '../../utils/api';
import UnifiedRecognitionResults from './UnifiedRecognitionResults';
import EnhancedView from './EnhancedView';
import FacesView from './FacesView';
import TimelineView from './TimelineView';

// API base URL
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api/v1';

// Extend Window interface to include our custom properties
declare global {
  interface Window {
    __audioInfoErrorLogged?: boolean;
  }
}

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

interface AudioInfo {
  file_path: string | null;
  file_name: string | null;
  source_url: string | null;
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
  const [activeTab, setActiveTab] = useState<string>('enhanced');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [recognitionStatus, setRecognitionStatus] = useState<RecognitionStatus | null>(null);
  const [audioInfo, setAudioInfo] = useState<AudioInfo | null>(null);
  const [showDebugInfo, setShowDebugInfo] = useState(false);
  const [transcriptionData, setTranscriptionData] = useState<TranscriptionData | null>(null);
  const [integratedTimeline, setIntegratedTimeline] = useState<IntegratedTimelineData | null>(null);
  const [isLoadingTranscription, setIsLoadingTranscription] = useState(false);
  const [transcriptionError, setTranscriptionError] = useState('');

  // Fetch recognition status on component mount and set up polling
  useEffect(() => {
    // Initial fetch of status
    fetchStatus();
    
    // Set up polling interval to check status every 5 seconds
    const intervalId = setInterval(() => {
      if (recognitionStatus?.status === 'processing' || recognitionStatus?.status === 'scheduled') {
        fetchStatus();
      }
    }, 5000);
    
    // Clean up interval on component unmount
    return () => clearInterval(intervalId);
  }, [captureId]); // Only re-run when captureId changes, not on status changes

  // Fetch recognition status
  const fetchStatus = async () => {
    // Check if captureId is valid
    if (!captureId || isNaN(Number(captureId))) {
      console.error('Invalid capture ID:', captureId);
      setError('Invalid capture ID. Please check the URL and try again.');
      setLoading(false);
      return;
    }
    
    try {
      const response = await api.get(`/recognition/recognition-status/${captureId}`);
      const responseData = response.data || response;
      
      console.log('Recognition status response:', responseData);
      
      // Extract the status object - it might be nested inside a 'status' property
      // or it might be the direct response
      const status = responseData.status && typeof responseData.status === 'object' 
        ? responseData.status 
        : responseData;
      
      console.log('Extracted status:', status);
      console.log('Status type:', status.status, 'Has results:', status.has_results);
      
      // Check if we have detailed recognition results
      if (responseData.results) {
        console.log('Recognition results found in response');
      }
      
      // Ensure status is properly formatted
      if (status && typeof status === 'object') {
        // Make sure we have a valid status object
        setRecognitionStatus({
          status: status.status || 'not_started',
          progress: status.progress || 0,
          error: responseData.error || status.error,
          results: responseData.results || status.results,
          started_at: status.started_at,
          completed_at: status.completed_at
        });
        
        // If completed or has results, fetch transcription data and notify parent
        if (status.status === 'completed' || status.has_results || responseData.results) {
          console.log('Status is completed or has results, fetching additional data');
          // Fetch transcription data first - this is critical for functionality
          await fetchTranscriptionData();
          // Try to fetch audio info, but don't block if it fails
          // This is wrapped in a try/catch to ensure it doesn't affect the main flow
          try {
            await fetchAudioInfo();
          } catch (audioErr) {
            // Audio info is not critical, so just log and continue
            console.info('Audio info fetch failed, but continuing with other data');
          }
          // Notify parent component if recognition is complete
          if (onProcessingComplete) {
            onProcessingComplete();
          }
        }
      } else {
        console.error('Invalid status format:', status);
        setError('Received invalid status format from server');
      }
      
      setLoading(false);
    } catch (err) {
      console.error('Error fetching recognition status:', err);
      setError('Error fetching recognition status. Please try again.');
      setLoading(false);
    }
  };

  // Fetch audio info
  const fetchAudioInfo = async () => {
    // Use a flag to track if we've already logged this error for this session
    // to avoid flooding the console with the same error
    if (window.__audioInfoErrorLogged) {
      // If we've already logged this error, just return silently
      return;
    }
    
    try {
      // Attempt to fetch audio info, but don't block the UI if it fails
      const response = await api.get(`/capture/${captureId}/audio-info`);
      
      // Only process the response if it was successful
      if (response && response.data) {
        const audioInfo = response.data;
        setAudioInfo(audioInfo);
        return;
      }
      
      // If we get here, we didn't get valid data
      setAudioInfo(null);
    } catch (err: any) {
      // Handle 404 errors gracefully - the endpoint might not be implemented yet
      if (err?.response?.status === 404) {
        // Mark that we've logged this error to avoid duplicate logs
        window.__audioInfoErrorLogged = true;
        
        // Only log in development, not in production
        if (process.env.NODE_ENV === 'development') {
          console.info('Audio info endpoint returned 404 - this is expected if the feature is not yet implemented');
        }
      } else {
        // For other errors, log once but don't flood the console
        if (!window.__audioInfoErrorLogged) {
          window.__audioInfoErrorLogged = true;
          console.error('Error fetching audio info:', err);
        }
      }
      
      // Don't block the UI if audio info fails - just continue with null audio info
      setAudioInfo(null);
    }
  };

  // Fetch transcription data
  const fetchTranscriptionData = async () => {
    setIsLoadingTranscription(true);
    try {
      const response = await api.get(`/recognition/timeline/${captureId}/transcription`);
      const data = response.data || response;
      
      if (data && data.success) {
        // Make sure we have valid transcription data
        if (data.transcription) {
          setTranscriptionData(data.transcription);
          setIntegratedTimeline(data);
        } else {
          // Log only in development environment
          if (process.env.NODE_ENV === 'development') {
            console.warn('Transcription data is missing in the response');
          }
          setTranscriptionError('Transcription data is missing in the response');
        }
      } else {
        // Log only in development environment
        if (process.env.NODE_ENV === 'development') {
          console.error('Error in transcription data:', data?.error || 'Unknown error');
        }
        setTranscriptionError(data?.error || 'Failed to load transcription data');
      }
    } catch (err) {
      // Log only in development environment
      if (process.env.NODE_ENV === 'development') {
        console.error('Error fetching transcription data:', err);
      }
      setTranscriptionError('Error fetching transcription data');
    } finally {
      setIsLoadingTranscription(false);
    }
  };

  // Debug info toggle
  const toggleDebugInfo = () => {
    setShowDebugInfo(!showDebugInfo);
  };

  // Render loading state
  if (loading) {
    return (
      <div className="bg-gray-800 rounded-lg shadow-lg p-6 flex flex-col items-center justify-center min-h-[300px]">
        <div className="spinner mb-4"></div>
        <p className="text-white">Loading recognition status...</p>
      </div>
    );
  }

  // Render error state
  if (error) {
    return (
      <div className="bg-gray-800 rounded-lg shadow-lg p-6">
        <div className="bg-red-900 border-l-4 border-red-500 p-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <p className="text-sm text-red-300">{error}</p>
              <button 
                onClick={() => {
                  setLoading(true);
                  setError('');
                  fetchStatus();
                }}
                className="mt-2 px-3 py-1 bg-red-800 hover:bg-red-700 rounded-md text-xs text-white"
              >
                Retry
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Render content based on recognition status
  return (
    <div className="bg-gray-800 rounded-lg shadow-lg p-6">
      <h2 className="text-xl font-bold mb-6 text-white">Recognition Results</h2>
      
      {/* Show processing status if we're still processing */}
      {recognitionStatus?.status === 'processing' && (
        <div className="mb-4">
          <div className="flex items-center">
            <div className="w-3 h-3 rounded-full mr-2 bg-blue-500"></div>
            <span className="font-medium text-white">Status: </span>
            <span className="ml-1 capitalize text-white">Processing</span>
            {recognitionStatus.progress !== undefined && (
              <span className="ml-2 text-gray-400">
                ({Math.round(recognitionStatus.progress)}%)
              </span>
            )}
          </div>
          
          {/* Progress bar */}
          <div className="w-full bg-gray-700 rounded-full h-4 mt-2">
            <div 
              className="h-4 rounded-full bg-blue-500" 
              style={{ width: `${Math.min(100, Math.max(0, recognitionStatus.progress || 0))}%` }}
            ></div>
          </div>
        </div>
      )}
      
      {/* Show scheduled or not started status */}
      {(recognitionStatus?.status === 'scheduled' || recognitionStatus?.status === 'not_started') && (
        <div className="mb-4">
          <div className="flex items-center">
            <div className="w-3 h-3 rounded-full mr-2 bg-gray-500"></div>
            <span className="font-medium text-white">Status: </span>
            <span className="ml-1 capitalize text-white">
              {recognitionStatus.status === 'not_started' ? 'Not Started' : 'Scheduled'}
            </span>
          </div>
        </div>
      )}
      
      {/* Show results if they exist or if status is completed */}
      {(recognitionStatus?.results || recognitionStatus?.status === 'completed') ? (
        <div>
          {/* Tab Navigation */}
          <div className="flex border-b border-gray-700 mb-6 overflow-x-auto">
            {[
              { id: 'enhanced', label: 'Enhanced View' },
              { id: 'unified', label: 'Unified View' },
              { id: 'faces', label: 'Faces' },
              { id: 'timeline', label: 'Timeline' }
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`py-3 px-6 border-b-2 font-medium transition-colors duration-200 whitespace-nowrap ${
                  activeTab === tab.id
                    ? 'border-blue-500 text-blue-500 bg-blue-900/10'
                    : 'border-transparent text-gray-400 hover:text-gray-300 hover:bg-gray-800/30'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
          
          {/* Tab Content */}
          {activeTab === 'enhanced' && (
            <EnhancedView 
              captureId={captureId}
              audioInfo={audioInfo}
              transcriptionData={transcriptionData}
              integratedTimeline={integratedTimeline}
            />
          )}
          
          {activeTab === 'unified' && (
            <UnifiedRecognitionResults videoId={captureId.toString()} />
          )}
          
          {activeTab === 'faces' && (
            <FacesView recognitionResults={recognitionStatus?.results || {}} />
          )}
          
          {activeTab === 'timeline' && (
            <TimelineView 
              videoId={captureId.toString()} 
              transcriptionData={transcriptionData} 
              integratedTimeline={integratedTimeline} 
            />
          )}
        </div>
      ) : recognitionStatus?.status === 'failed' ? (
        <div className="bg-red-900 border-l-4 border-red-500 p-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <p className="text-sm text-red-300">Recognition failed. {recognitionStatus?.error || 'Please try again.'}</p>
              <button 
                onClick={() => {
                  setLoading(true);
                  setError('');
                  fetchStatus();
                }}
                className="mt-2 px-3 py-1 bg-red-800 hover:bg-red-700 rounded-md text-xs text-white"
              >
                Retry
              </button>
            </div>
          </div>
        </div>
      ) : (
        <div className="flex justify-center items-center p-6">
          <button 
            onClick={() => router.push(`/capture/${captureId}`)}
            className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-md"
          >
            Back to Capture
          </button>
        </div>
      )}
      
      <style jsx>{`
        .spinner {
          border: 4px solid rgba(255, 255, 255, 0.1);
          width: 36px;
          height: 36px;
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

export default UnifiedRecognitionPanel;
