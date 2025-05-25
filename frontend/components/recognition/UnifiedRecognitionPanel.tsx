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
      const status = response.data || response;
      
      console.log('Recognition status:', status);
      setRecognitionStatus(status);
      
      // If completed, fetch transcription data
      if (status.status === 'completed') {
        fetchTranscriptionData();
        fetchAudioInfo();
        
        // Notify parent component if recognition is complete
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
      
      console.log('Audio info:', audioInfo);
      setAudioInfo(audioInfo);
    } catch (err) {
      console.error('Error fetching audio info:', err);
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
      
      if (data && data.success) {
        // Ensure transcription data has the expected structure
        if (data.transcription) {
          setTranscriptionData(data.transcription);
          setIntegratedTimeline(data);
        } else {
          setTranscriptionError('Invalid transcription data format');
        }
      } else {
        setTranscriptionError(data?.error || 'Failed to fetch transcription data');
      }
    } catch (err) {
      console.error('Error fetching transcription data:', err);
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
                  fetchStatus();
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
