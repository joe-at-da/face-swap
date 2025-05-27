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
  const [recognitionStatus, setRecognitionStatus] = useState<RecognitionStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [audioInfo, setAudioInfo] = useState<AudioInfo | null>(null);
  const [transcriptionData, setTranscriptionData] = useState<TranscriptionData | null>(null);
  const [integratedTimeline, setIntegratedTimeline] = useState<IntegratedTimelineData | null>(null);
  const [isLoadingTranscription, setIsLoadingTranscription] = useState(false);
  const [transcriptionError, setTranscriptionError] = useState('');
  const [isStartingRecognition, setIsStartingRecognition] = useState(false);

  // Start recognition process
  const startRecognition = async () => {
    if (!captureId || isNaN(Number(captureId))) {
      console.error('Invalid capture ID:', captureId);
      setError('Invalid capture ID. Please check the URL and try again.');
      return;
    }
    
    setIsStartingRecognition(true);
    try {
      console.log('Starting recognition process for capture ID:', captureId);
      const response = await api.post('/recognition/combined-recognition', {
        video_id: Number(captureId),
        save_output: true
      });
      
      console.log('Recognition process started:', response);
      toast.success('Recognition process started');
      
      // Fetch the updated status
      fetchStatus();
    } catch (err) {
      console.error('Error starting recognition process:', err);
      toast.error('Failed to start recognition process');
      setError('Failed to start recognition process. Please try again.');
      setLoading(false);
    } finally {
      setIsStartingRecognition(false);
    }
  };

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
      // Get the data from the response
      let responseData = response.data || response;
      
      console.log('Raw recognition status response:', responseData);
      
      // Create a valid RecognitionStatus object
      const statusData: RecognitionStatus = {
        // Default to 'not_started' if no status is present
        status: 'not_started',
        // Add other fields with defaults
        steps: [],
        progress: 0
      };
      
      // If we have a valid response object, extract properties
      if (responseData && typeof responseData === 'object') {
        // Check if the response has a nested status object structure
        // Format: { success: true, status: { status: 'completed', ... }, error: null }
        if (responseData.success === true && responseData.status && typeof responseData.status === 'object') {
          console.log('Found nested status object:', responseData.status);
          
          // Extract the nested status object
          const nestedStatus = responseData.status;
          
          // Copy properties from the nested status object
          if (nestedStatus.status && typeof nestedStatus.status === 'string') {
            statusData.status = nestedStatus.status;
          }
          
          // Copy other properties from the nested status
          ['progress', 'started_at', 'completed_at', 'results', 'has_results'].forEach(key => {
            if (key in nestedStatus) {
              (statusData as any)[key] = (nestedStatus as any)[key];
            }
          });
          
          // If there's an error in the response, store it
          if (responseData.error) {
            statusData.error = responseData.error;
          }
        } else {
          // Handle flat structure (no nested status object)
          // Copy all existing properties
          Object.keys(responseData).forEach(key => {
            if (key in responseData) {
              (statusData as any)[key] = (responseData as any)[key];
            }
          });
        }
        
        // Ensure status is a valid value
        if (typeof statusData.status === 'string' && 
            ['not_started', 'scheduled', 'processing', 'completed', 'failed'].includes(statusData.status)) {
          // Status is already valid
        } else {
          console.warn('Recognition status has invalid status property:', statusData.status);
          
          // Try to determine status from other properties
          if (statusData.completed_at) {
            statusData.status = 'completed';
          } else if (statusData.started_at) {
            statusData.status = 'processing';
          } else {
            statusData.status = 'not_started';
          }
          
          console.log('Determined status from properties:', statusData.status);
        }
      } else {
        console.warn('Empty or invalid response from recognition status API');
      }
      
      console.log('Processed recognition status:', statusData);
      setRecognitionStatus(statusData);
      
      // If recognition is completed, fetch additional data
      if (statusData.status === 'completed') {
        fetchAudioInfo();
        fetchTranscriptionData();
        
        // Call the callback if provided
        if (onProcessingComplete) {
          onProcessingComplete();
        }
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
    try {
      const response = await api.get(`/capture/${captureId}/audio-info`);
      const audioInfo = response.data || response;
      setAudioInfo(audioInfo);
    } catch (err) {
      console.error('Error fetching audio info:', err);
      // Create a default audio info object when the endpoint returns an error
      setAudioInfo({
        file_path: null,
        file_name: null,
        source_url: null
      });
      // Don't set an error state, as this is not critical
    }
  };

  // Fetch transcription data
  const fetchTranscriptionData = async () => {
    try {
      setIsLoadingTranscription(true);
      setTranscriptionError('');
      
      console.log('Fetching transcription data for captureId:', captureId);
      const response = await api.get(`/recognition/timeline/${captureId}/transcription`);
      console.log('Transcription data response:', response);
      
      // Handle different response formats
      const data = response.data || response;
      
      // Validate the response
      if (!data) {
        throw new Error('Empty response from transcription API');
      }
      
      // Log the raw data structure to better understand the format
      console.log('Raw transcription data structure:', JSON.stringify(data).substring(0, 200) + '...');
      
      // Create default transcription data object
      const transcriptionData: TranscriptionData = {
        text: '',
        segments: [],
        language: 'en',
        duration: 0
      };
      
      // Create default integrated timeline data
      const integratedData: IntegratedTimelineData = {
        success: true,
        transcription: transcriptionData,
        timeline: [],
        correlations: []
      };
      
      // Try to extract data from various possible formats
      // Check for direct text and segments
      if (typeof data.text === 'string') {
        transcriptionData.text = data.text;
        console.log('Found text in response');
      }
      
      if (Array.isArray(data.segments)) {
        transcriptionData.segments = data.segments;
        console.log('Found segments in response');
      }
      
      if (typeof data.language === 'string') {
        transcriptionData.language = data.language;
      }
      
      if (typeof data.duration === 'number') {
        transcriptionData.duration = data.duration;
      }
      
      // Check for nested transcription object
      if (data.transcription && typeof data.transcription === 'object') {
        console.log('Found nested transcription object');
        
        if (typeof data.transcription.text === 'string') {
          transcriptionData.text = data.transcription.text;
        }
        
        if (Array.isArray(data.transcription.segments)) {
          transcriptionData.segments = data.transcription.segments;
        }
        
        if (typeof data.transcription.language === 'string') {
          transcriptionData.language = data.transcription.language;
        }
        
        if (typeof data.transcription.duration === 'number') {
          transcriptionData.duration = data.transcription.duration;
        }
      }
      
      // Check for timeline data
      if (Array.isArray(data.timeline)) {
        integratedData.timeline = data.timeline;
        console.log('Found timeline data');
      }
      
      // Check for correlations data
      if (Array.isArray(data.correlations)) {
        integratedData.correlations = data.correlations;
        console.log('Found correlations data');
      }
      
      // If we have a transcript property that's a string, use it as text
      if (typeof data.transcript === 'string' && data.transcript.length > 0) {
        transcriptionData.text = data.transcript;
        console.log('Found transcript string');
      }
      
      // If we have a result property that contains text, use it
      if (data.result && typeof data.result.text === 'string') {
        transcriptionData.text = data.result.text;
        console.log('Found text in result object');
      }
      
      // Update the integrated data with our transcription data
      integratedData.transcription = transcriptionData;
      
      // Set state with whatever data we were able to extract
      setTranscriptionData(transcriptionData);
      setIntegratedTimeline(integratedData);
      
      // Log what we're using
      console.log('Using transcription data:', transcriptionData);
      console.log('Using integrated timeline data:', integratedData);
      
      // If we couldn't extract any meaningful data, set an error
      if (transcriptionData.text === '' && transcriptionData.segments.length === 0) {
        console.warn('No usable transcription data found');
        setTranscriptionError('No transcription data available');
      }
    } catch (err) {
      console.error('Error fetching transcription data:', err);
      
      // Create minimal valid objects to prevent UI errors
      const emptyTranscription: TranscriptionData = {
        text: '',
        segments: [],
        language: 'en',
        duration: 0
      };
      
      const emptyIntegratedData: IntegratedTimelineData = {
        success: false,
        transcription: emptyTranscription,
        timeline: [],
        correlations: [],
        error: err instanceof Error ? err.message : 'Unknown error'
      };
      
      setTranscriptionData(emptyTranscription);
      setIntegratedTimeline(emptyIntegratedData);
      setTranscriptionError('Error fetching transcription data. Please try again.');
    } finally {
      setIsLoadingTranscription(false);
    }
  };

  // Initial fetch
  useEffect(() => {
    fetchStatus();
    
    // Set up polling interval
    const interval = setInterval(() => {
      if (recognitionStatus?.status === 'processing' || recognitionStatus?.status === 'scheduled') {
        fetchStatus();
      }
    }, 5000);
    
    return () => clearInterval(interval);
  }, [captureId]);

  // Render loading state
  if (loading) {
    return (
      <div className="bg-gray-800 rounded-lg shadow-lg p-6">
        <h2 className="text-xl font-bold mb-6 text-white">Recognition Results</h2>
        <div className="flex justify-center items-center h-32">
          <div className="spinner"></div>
          <span className="ml-3 text-gray-300">Loading recognition status...</span>
        </div>
      </div>
    );
  }

  // Render error state
  if (error) {
    return (
      <div className="bg-gray-800 rounded-lg shadow-lg p-6">
        <h2 className="text-xl font-bold mb-6 text-white">Recognition Results</h2>
        <div className="bg-red-900 border-l-4 border-red-500 p-4 mb-4">
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
      
      {recognitionStatus?.status === 'not_started' || recognitionStatus?.status === 'scheduled' || recognitionStatus?.status === 'processing' ? (
        <div>
          <div className="mb-4">
            <div className="flex items-center">
              <div className={`w-3 h-3 rounded-full mr-2 ${
                recognitionStatus.status === 'processing' ? 'bg-blue-500' : 
                'bg-gray-500'
              }`}></div>
              <span className="font-medium text-white">Status: </span>
              <span className="ml-1 capitalize text-white">
                {recognitionStatus.status === 'not_started' ? 'Not Started' : 
                 recognitionStatus.status === 'processing' ? 'Processing' : 
                 recognitionStatus.status === 'scheduled' ? 'Scheduled' : 'Unknown'}
              </span>
              {recognitionStatus.status === 'processing' && recognitionStatus.progress && (
                <span className="ml-2 text-gray-400">
                  ({Math.round(recognitionStatus.progress)}%)
                </span>
              )}
            </div>
          </div>
          
          {/* Progress bar */}
          {recognitionStatus.status === 'processing' && (
            <div className="w-full bg-gray-700 rounded-full h-4 mb-4">
              <div 
                className="h-4 rounded-full bg-blue-500" 
                style={{ width: `${Math.min(100, Math.max(0, recognitionStatus.progress || 0))}%` }}
              ></div>
            </div>
          )}
          
          <div className="mt-4">
            <button
              onClick={() => router.push(`/capture/${captureId}`)}
              className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-md mr-2"
            >
              Back to Capture
            </button>
          </div>
        </div>
      ) : recognitionStatus?.status === 'completed' ? (
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
            <FacesView recognitionResults={recognitionStatus.results} />
          )}
          
          {activeTab === 'timeline' && (
            <TimelineView 
              videoId={captureId.toString()} 
              transcriptionData={transcriptionData} 
              integratedTimeline={integratedTimeline} 
            />
          )}
        </div>
      ) : (
        <div className="bg-red-900 border-l-4 border-red-500 p-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <p className="text-sm text-red-300">Recognition failed. Please try again.</p>
              <button 
                onClick={() => {
                  setLoading(true);
                  startRecognition();
                }}
                className="mt-2 px-3 py-1 bg-red-800 hover:bg-red-700 rounded-md text-xs text-white"
              >
                Retry
              </button>
            </div>
          </div>
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
