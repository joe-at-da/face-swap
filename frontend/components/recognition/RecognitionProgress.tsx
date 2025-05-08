import React, { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../../utils/api';

interface RecognitionProgressProps {
  captureId: number;
  isProcessing: boolean;
  onComplete: () => void;
}

interface ProgressStep {
  name: string;
  status: string;
  timestamp: string;
}

interface ProgressData {
  status: string;
  completed_at?: string;
  error?: string;
  error_at?: string;
  steps: ProgressStep[];
}

const RecognitionProgress: React.FC<RecognitionProgressProps> = ({ 
  captureId, 
  isProcessing,
  onComplete 
}) => {
  const [progress, setProgress] = useState<ProgressData | null>(null);
  const [pollingEnabled, setPollingEnabled] = useState(false);

  // Start polling when isProcessing becomes true
  useEffect(() => {
    if (isProcessing) {
      setPollingEnabled(true);
    }
  }, [isProcessing]);

  // Fetch recognition status
  const { data, isLoading, isError } = useQuery({
    queryKey: ['recognitionStatus', captureId],
    queryFn: async () => {
      try {
        const response = await api.get(`/recognition/recognition-status/${captureId}`);
        return response;
      } catch (error) {
        console.error('Error fetching recognition status:', error);
        throw error;
      }
    },
    enabled: pollingEnabled && !!captureId,
    refetchInterval: pollingEnabled ? 3000 : false, // Poll every 3 seconds when enabled
  });

  // Update progress state when data changes
  useEffect(() => {
    if (data?.success && data?.status?.progress) {
      setProgress(data.status.progress);
      
      // Check if processing is complete or has error
      if (data.status.status === 'completed' || data.status.status === 'error') {
        setPollingEnabled(false);
        onComplete();
      }
    }
  }, [data, onComplete]);

  // Helper function to get step display name
  const getStepDisplayName = (stepName: string): string => {
    const displayNames: Record<string, string> = {
      'initialization': 'Initialization',
      'speaker_identification': 'Speaker Identification',
      'transcription': 'Transcription',
      'completion': 'Finalizing Results'
    };
    return displayNames[stepName] || stepName;
  };

  // Helper function to get step status class
  const getStepStatusClass = (status: string): string => {
    switch (status) {
      case 'completed':
        return 'bg-green-100 text-green-800';
      case 'started':
        return 'bg-blue-100 text-blue-800';
      case 'error':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  // Calculate overall progress percentage
  const calculateProgress = (): number => {
    if (!progress || !progress.steps || progress.steps.length === 0) return 0;
    
    const totalSteps = progress.steps.length;
    const completedSteps = progress.steps.filter(step => step.status === 'completed').length;
    
    return Math.floor((completedSteps / totalSteps) * 100);
  };

  // If not processing and no progress data, don't render anything
  if (!isProcessing && !progress) {
    return null;
  }

  // Show loading state
  if (isLoading && !progress) {
    return (
      <div className="bg-white p-4 rounded border border-gray-200 mb-4">
        <h4 className="font-medium mb-3">Recognition Progress</h4>
        <div className="flex items-center justify-center p-4">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
          <span className="ml-2 text-sm text-gray-600">Loading progress information...</span>
        </div>
      </div>
    );
  }

  // Show error state
  if (isError) {
    return (
      <div className="bg-white p-4 rounded border border-gray-200 mb-4">
        <h4 className="font-medium mb-3">Recognition Progress</h4>
        <div className="bg-red-50 p-3 rounded text-red-700 text-sm">
          Error loading recognition progress. Please try again later.
        </div>
      </div>
    );
  }

  // If we have progress data or we're processing, show the progress UI
  return (
    <div className="bg-white p-4 rounded border border-gray-200 mb-4">
      <h4 className="font-medium mb-3">Recognition Progress</h4>
      
      {/* Overall progress status */}
      <div className="mb-4">
        <div className="flex justify-between items-center mb-1">
          <span className="text-sm font-medium">Overall Progress</span>
          <span className="text-sm font-medium">{calculateProgress()}%</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2.5">
          <div 
            className="bg-blue-600 h-2.5 rounded-full" 
            style={{ width: `${calculateProgress()}%` }}
          ></div>
        </div>
      </div>
      
      {/* Status message */}
      {progress && (
        <div className={`mb-4 p-2 rounded text-sm ${
          progress.status === 'completed' ? 'bg-green-50 text-green-700' :
          progress.status === 'error' ? 'bg-red-50 text-red-700' :
          'bg-blue-50 text-blue-700'
        }`}>
          {progress.status === 'completed' && 'Recognition completed successfully'}
          {progress.status === 'error' && `Error: ${progress.error || 'An unknown error occurred'}`}
          {progress.status !== 'completed' && progress.status !== 'error' && 'Recognition in progress...'}
        </div>
      )}
      
      {/* Steps list */}
      {progress && progress.steps && progress.steps.length > 0 && (
        <div className="space-y-2">
          <h5 className="text-sm font-medium mb-2">Processing Steps</h5>
          {progress.steps.map((step, index) => (
            <div key={index} className="flex items-center justify-between p-2 bg-gray-50 rounded">
              <div className="flex items-center">
                {step.status === 'completed' ? (
                  <svg className="w-4 h-4 text-green-600 mr-2" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                ) : step.status === 'started' ? (
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600 mr-2"></div>
                ) : step.status === 'error' ? (
                  <svg className="w-4 h-4 text-red-600 mr-2" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                  </svg>
                ) : (
                  <svg className="w-4 h-4 text-gray-400 mr-2" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd" />
                  </svg>
                )}
                <span className="text-sm">{getStepDisplayName(step.name)}</span>
              </div>
              <span className={`text-xs px-2 py-1 rounded-full ${getStepStatusClass(step.status)}`}>
                {step.status.charAt(0).toUpperCase() + step.status.slice(1)}
              </span>
            </div>
          ))}
        </div>
      )}
      
      {/* If no steps yet but processing */}
      {(!progress || !progress.steps || progress.steps.length === 0) && isProcessing && (
        <div className="flex items-center justify-center p-4">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
          <span className="ml-2 text-sm text-gray-600">Initializing recognition process...</span>
        </div>
      )}
    </div>
  );
};

export default RecognitionProgress;
