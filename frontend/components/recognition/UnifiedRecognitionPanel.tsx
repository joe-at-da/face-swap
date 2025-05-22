import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../../contexts/AuthContext';
import { toast } from 'react-toastify';
import * as Path from 'path';
import { api } from '../../utils/api';

// API base URL
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api/v1';

interface UnifiedRecognitionPanelProps {
  captureId: number;
  onProcessingComplete?: () => void;
}

interface RecognitionStatus {
  status: 'not_started' | 'scheduled' | 'processing' | 'completed' | 'failed';
  progress?: number;
  steps?: Array<{
    name: string;
    status: 'waiting' | 'in_progress' | 'completed' | 'failed';
    progress?: number;
  }>;
  error?: string;
  started_at?: string;
  completed_at?: string;
  results?: any;
}

interface TranscriptionOptions {
  enableSpeakerIdentification: boolean;
  enableFacialRecognition: boolean;
}

const UnifiedRecognitionPanel: React.FC<UnifiedRecognitionPanelProps> = ({
  captureId,
  onProcessingComplete
}) => {
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
  const [audioInfo, setAudioInfo] = useState<any>(null);

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
    // If processing is completed, stop polling
    if (recognitionStatus?.status === 'completed' && refreshInterval) {
      clearInterval(refreshInterval);
      setRefreshInterval(null);
      if (onProcessingComplete) {
        onProcessingComplete();
      }
    }
  }, [recognitionStatus?.status]);

  const fetchStatus = async () => {
    try {
      setIsRefreshing(true);
      
      // First try to get detailed status
      try {
        const detailedResponse = await axios.get(`${API_BASE_URL}/recognition/detailed-status/${captureId}`, {
          headers: {
            Authorization: `Bearer ${token}`
          }
        });
        
        const detailedData = detailedResponse.data as { success: boolean; status: any };
        if (detailedData.success) {
          const statusData = detailedData.status;
          
          // Map the backend status format to our component's format
          const mappedStatus: RecognitionStatus = {
            status: statusData.status,
            started_at: statusData.started_at,
            completed_at: statusData.completed_at,
            progress: statusData.progress?.completion_percentage || 0,
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
        const basicResponse = await axios.get(`${API_BASE_URL}/recognition-status/${captureId}`, {
          headers: {
            Authorization: `Bearer ${token}`
          }
        });
        
        const basicData = basicResponse.data as { success: boolean; status: any };
        if (basicData.success) {
          const statusData = basicData.status;
          
          // Map the basic status
          const mappedStatus: RecognitionStatus = {
            status: statusData.status,
            started_at: statusData.started_at,
            completed_at: statusData.completed_at
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
  
  // Helper function to get file name from path
  const Path = {
    basename: (path: string) => {
      return path.split('/').pop() || path;
    }
  };

  const startRecognitionProcess = async () => {
    try {
      setIsStartingProcess(true);
      
      // Use the combined recognition endpoint
      const response = await axios.post(`${API_BASE_URL}/combined-recognition`, {
        video_id: captureId,
        save_output: true
      }, {
        headers: {
          Authorization: `Bearer ${token}`
        }
      });
      
      const responseData = response.data as { success: boolean; error?: string };
      
      if (responseData.success) {
        toast.success('Recognition process started successfully');
        fetchStatus(); // Refresh status immediately
      } else {
        toast.error(responseData.error || 'Failed to start recognition process');
      }
    } catch (err) {
      console.error('Error starting recognition process:', err);
      toast.error('Failed to start recognition process');
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
      'Audio Extraction',
      'Transcription',
      'Speaker Identification',
      'Facial Recognition'
    ];
    return stepNames[index] || `Step ${index + 1}`;
  };

  const getStatusColor = (status: string): string => {
    switch (status) {
      case 'not_started':
        return 'text-gray-500';
      case 'scheduled':
        return 'text-blue-500';
      case 'processing':
        return 'text-yellow-500';
      case 'completed':
        return 'text-green-500';
      case 'failed':
        return 'text-red-500';
      default:
        return 'text-gray-500';
    }
  };

  const getStatusBgColor = (status: string): string => {
    switch (status) {
      case 'not_started':
        return 'bg-gray-100';
      case 'scheduled':
        return 'bg-blue-100';
      case 'processing':
        return 'bg-yellow-100';
      case 'completed':
        return 'bg-green-100';
      case 'failed':
        return 'bg-red-100';
      default:
        return 'bg-gray-100';
    }
  };

  if (loading && !recognitionStatus) {
    return (
      <div className="bg-gray-800 text-white rounded-lg p-6 mb-6">
        <div className="flex justify-center items-center h-40">
          <div className="spinner"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-gray-800 text-white rounded-lg p-6 mb-6">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-semibold">Recognition & Transcription</h2>
        {recognitionStatus?.status === 'processing' && (
          <div className="flex items-center">
            <div className="spinner-sm mr-2"></div>
            <span>Refreshing status...</span>
          </div>
        )}
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
            {recognitionStatus?.status?.replace('_', ' ') || 'Not Started'}
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

      {/* Recognition Progress */}
      {recognitionStatus?.status === 'processing' && (
        <div className="bg-gray-700 rounded-lg p-4 mb-6">
          <h3 className="text-lg font-semibold mb-3">Recognition Progress</h3>
          
          <div className="mb-4">
            <div className="flex justify-between mb-1">
              <span>Overall Progress</span>
              <span>{recognitionStatus.progress || 0}%</span>
            </div>
            <div className="w-full bg-gray-600 rounded-full h-2.5">
              <div 
                className="bg-blue-500 h-2.5 rounded-full" 
                style={{ width: `${recognitionStatus.progress || 0}%` }}
              ></div>
            </div>
          </div>
          
          <div className="space-y-3">
            <h4 className="font-medium">Processing Steps</h4>
            {recognitionStatus.steps ? (
              recognitionStatus.steps.map((step, index) => (
                <div key={index} className="bg-gray-800 rounded-lg p-3">
                  <div className="flex justify-between items-center mb-1">
                    <div className="flex items-center">
                      {step.status === 'completed' ? (
                        <svg className="w-4 h-4 text-green-500 mr-2" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                        </svg>
                      ) : step.status === 'in_progress' ? (
                        <div className="spinner-xs mr-2"></div>
                      ) : (
                        <div className="w-4 h-4 mr-2"></div>
                      )}
                      <span>{getStepName(index)}</span>
                    </div>
                    <span className={`text-sm px-2 py-0.5 rounded-full ${
                      step.status === 'completed' ? 'bg-green-900 text-green-300' :
                      step.status === 'in_progress' ? 'bg-blue-900 text-blue-300' :
                      step.status === 'failed' ? 'bg-red-900 text-red-300' :
                      'bg-gray-900 text-gray-300'
                    }`}>
                      {step.status.replace('_', ' ')}
                    </span>
                  </div>
                  {step.status === 'in_progress' && step.progress !== undefined && (
                    <div className="w-full bg-gray-600 rounded-full h-1.5 mt-2">
                      <div 
                        className="bg-blue-500 h-1.5 rounded-full" 
                        style={{ width: `${step.progress}%` }}
                      ></div>
                    </div>
                  )}
                </div>
              ))
            ) : (
              <div className="text-gray-400">No step information available</div>
            )}
          </div>
        </div>
      )}

      {/* Start Recognition Form */}
      {recognitionStatus?.status === 'not_started' && (
        <div className="bg-gray-700 rounded-lg p-4 mb-6">
          <h3 className="text-lg font-semibold mb-3">Start Recognition Process</h3>
          
          <div className="mb-4">
            <p className="text-gray-300 mb-3">
              Convert the audio to text with timestamps. This will create a searchable transcript of the parliamentary session.
            </p>
            
            <div className="space-y-3">
              <div className="flex items-center">
                <label className="inline-flex items-center cursor-pointer">
                  <input 
                    type="checkbox" 
                    className="sr-only peer"
                    checked={transcriptionOptions.enableSpeakerIdentification}
                    onChange={() => handleOptionChange('enableSpeakerIdentification')}
                  />
                  <div className="relative w-11 h-6 bg-gray-600 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-500"></div>
                  <span className="ml-3 text-gray-200">Enable Speaker Identification</span>
                </label>
                <div className="ml-2 text-gray-400 cursor-pointer group relative">
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 w-48 p-2 bg-gray-900 text-xs text-gray-300 rounded shadow-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-opacity">
                    Uses voice recognition to identify and tag speakers in the transcript
                  </div>
                </div>
              </div>
              
              <div className="flex items-center">
                <label className="inline-flex items-center cursor-pointer">
                  <input 
                    type="checkbox" 
                    className="sr-only peer"
                    checked={transcriptionOptions.enableFacialRecognition}
                    onChange={() => handleOptionChange('enableFacialRecognition')}
                  />
                  <div className="relative w-11 h-6 bg-gray-600 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-500"></div>
                  <span className="ml-3 text-gray-200">Enable Facial Recognition</span>
                </label>
                <div className="ml-2 text-gray-400 cursor-pointer group relative">
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 w-48 p-2 bg-gray-900 text-xs text-gray-300 rounded shadow-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-opacity">
                    Detects and identifies faces in the video to enhance speaker recognition
                  </div>
                </div>
              </div>
            </div>
          </div>
          
          <button
            onClick={startRecognitionProcess}
            disabled={isStartingProcess}
            className="flex items-center justify-center w-full sm:w-auto px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-opacity-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isStartingProcess ? (
              <>
                <div className="spinner-xs mr-2"></div>
                Starting...
              </>
            ) : (
              <>
                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Start Recognition Process
              </>
            )}
          </button>
        </div>
      )}

      {/* Completed Results Summary */}
      {recognitionStatus?.status === 'completed' && recognitionStatus.results && (
        <div className="bg-gray-700 rounded-lg p-4 mb-6">
          <h3 className="text-lg font-semibold mb-3">Recognition Results</h3>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <div className="bg-gray-800 rounded-lg p-3">
              <h4 className="font-medium text-gray-300 mb-2">Transcription</h4>
              <div className="text-gray-200">
                <div className="flex justify-between mb-1">
                  <span>Total Duration</span>
                  <span>{recognitionStatus.results.duration_seconds ? formatDuration(recognitionStatus.results.duration_seconds) : 'N/A'}</span>
                </div>
                <div className="flex justify-between mb-1">
                  <span>Segments</span>
                  <span>{recognitionStatus.results.segments?.length || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span>Words</span>
                  <span>{recognitionStatus.results.word_count || 0}</span>
                </div>
              </div>
            </div>
            
            <div className="bg-gray-800 rounded-lg p-3">
              <h4 className="font-medium text-gray-300 mb-2">Speaker Recognition</h4>
              <div className="text-gray-200">
                <div className="flex justify-between mb-1">
                  <span>Speakers Detected</span>
                  <span>{recognitionStatus.results.speakers?.length || 0}</span>
                </div>
                <div className="flex justify-between mb-1">
                  <span>Identified Speakers</span>
                  <span>{recognitionStatus.results.identified_speakers || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span>Face Samples</span>
                  <span>{recognitionStatus.results.face_samples || 0}</span>
                </div>
              </div>
            </div>
          </div>
          
          <div className="flex justify-end">
            <button
              onClick={() => window.location.href = `/parliament-tv/${captureId}/transcript`}
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
