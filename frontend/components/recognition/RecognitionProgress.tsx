import React, { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../../utils/api';

// Define API response types for TypeScript
interface ApiResponse {
  success: boolean;
  status: {
    status: string;
    progress?: ProgressData;
    video_id: number;
    started_at?: string;
    completed_at?: string;
    has_results?: boolean;
  };
  error?: string;
}

interface RecognitionProgressProps {
  captureId: number;
  isProcessing: boolean;
  onComplete: () => void;
}

interface ProgressStep {
  name: string;
  status: string;
  timestamp: string;
  message?: string;
  completion_percentage?: number;
}

interface ProgressData {
  status: string;
  completed_at?: string;
  error?: string;
  error_at?: string;
  steps: ProgressStep[];
  completion_percentage?: number;
  current_step?: string;
  start_time?: string;
  last_update?: string;
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
      console.log('Recognition progress polling enabled');
    } else if (pollingEnabled) {
      // If we were polling and processing stopped, check one more time
      console.log('Processing stopped, checking final status');
      // We don't disable polling here to allow one more status check
    }
  }, [isProcessing, pollingEnabled]);

  // Fetch recognition status
  const { data, isLoading, isError, error } = useQuery<ApiResponse>(
    {
      queryKey: ['recognitionStatus', captureId],
      queryFn: async () => {
        try {
          console.log(`Fetching detailed recognition status for capture ID: ${captureId}`);
          const response = await api.get(`/recognition/detailed-status/${captureId}`);
          console.log('Recognition status raw response:', response);
          return response as ApiResponse;
        } catch (error) {
          console.error(`Error fetching recognition status for capture ID ${captureId}:`, error);
          throw error;
        }
      },
      enabled: pollingEnabled && !!captureId,
      refetchInterval: pollingEnabled ? 3000 : false, // Poll every 3 seconds when enabled
      retry: 3, // Retry failed requests up to 3 times
      retryDelay: 1000, // Wait 1 second between retries
      staleTime: 0, // Consider data always stale to ensure fresh data
    }
  );

  // Update progress state when data changes
  useEffect(() => {
    console.log('Recognition progress data changed:', data);
    if (data && 'success' in data && data.success && 'status' in data && data.status) {
      // Make sure data.status is an object and not a string
      if (typeof data.status === 'object' && data.status !== null) {
        // Check if we have progress data
        if ('progress' in data.status && data.status.progress) {
          console.log('Setting progress data:', data.status.progress);
          setProgress(data.status.progress);
        } else {
          // If no progress data yet, initialize with basic structure based on status
          console.log('No progress data yet, using status:', data.status);
          const statusString = typeof data.status.status === 'string' ? data.status.status : 'processing';
          const initialProgress: ProgressData = {
            status: statusString,
            steps: [{
              name: 'initialization',
              status: statusString === 'processing' ? 'started' : statusString,
              timestamp: new Date().toISOString()
            }]
          };
          setProgress(initialProgress);
        }
      } else {
        // Handle case where data.status is not an object
        console.log('Status is not an object:', data.status);
        const statusString = typeof data.status === 'string' ? data.status : 'processing';
        const initialProgress: ProgressData = {
          status: statusString,
          steps: [{
            name: 'initialization',
            status: statusString === 'processing' ? 'started' : statusString,
            timestamp: new Date().toISOString()
          }]
        };
        setProgress(initialProgress);
      }
      
      // Check if processing is complete or has error
      const statusValue = typeof data.status === 'object' && data.status !== null && 'status' in data.status
        ? data.status.status
        : typeof data.status === 'string' ? data.status : 'processing';
        
      if (statusValue === 'completed' || statusValue === 'error') {
        console.log('Recognition process completed or has error:', statusValue);
        setPollingEnabled(false);
        // Call onComplete to notify parent component
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
  const calculateProgress = () => {
    if (!progress) return 0;
    
    // If we have an overall completion percentage, use that
    if (progress.completion_percentage !== undefined && progress.completion_percentage !== null) {
      return Math.max(0, Math.min(100, progress.completion_percentage));
    }
    
    // If we have steps with completion percentages, use the latest one
    if (progress.steps && progress.steps.length > 0) {
      // Find the latest step with a completion percentage
      const stepsWithPercentage = progress.steps
        .filter(step => step.completion_percentage !== undefined && step.completion_percentage !== null);
      
      if (stepsWithPercentage.length > 0) {
        // Get the latest step with percentage
        const latestStep = stepsWithPercentage[stepsWithPercentage.length - 1];
        return Math.max(0, Math.min(100, latestStep.completion_percentage || 0));
      }
      
      // Fallback: calculate based on completed steps
      const completedSteps = progress.steps.filter(step => step.status === 'completed').length;
      const totalSteps = progress.steps.length;
      return totalSteps > 0 ? Math.round((completedSteps / totalSteps) * 100) : 0;
    }
    
    return 0;
  };

  useEffect(() => {
    if (isProcessing && !progress) {
      console.log('Processing but no progress data, forcing poll');
      setPollingEnabled(true);
    }
  }, [isProcessing, progress]);

  useEffect(() => {
    console.log('RecognitionProgress component state:', {
      captureId,
      isProcessing,
      pollingEnabled,
      hasData: !!data,
      hasProgress: !!progress,
      isLoading,
      isError
    });
    
    // Log data structure if available
    if (data) {
      console.log('Current data structure:', JSON.stringify(data, null, 2));
    }
  }, [captureId, isProcessing, pollingEnabled, data, progress, isLoading, isError]);

  // Log current state for debugging
  console.log('Current progress state:', { isProcessing, progress, isLoading, isError, error });

  // Always render if isProcessing is true, even without progress data
  // Only hide if not processing and no progress data
  if (!isProcessing && !progress) {
    console.log('Not processing and no progress data, not rendering');
    return null;
  }

  // Show loading state
  if (isLoading && !progress) {
    console.log('Showing loading state');
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
    console.log('Showing error state:', error);
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
  console.log('Rendering progress UI with data:', progress);
  return (
    <div className="bg-white p-4 rounded border border-gray-200 mb-4">
      <h4 className="font-medium mb-3">Recognition Progress</h4>
      
      {/* Connection status indicator */}
      <div className="mb-3 flex items-center">
        <div className={`w-3 h-3 rounded-full mr-2 ${isLoading ? 'bg-yellow-400' : isError ? 'bg-red-500' : pollingEnabled ? 'bg-green-500' : 'bg-gray-400'}`}></div>
        <span className="text-xs text-gray-600">
          {isError ? 'Connection error' : isLoading ? 'Updating...' : pollingEnabled ? 'Connected' : 'Idle'}
        </span>
      </div>
      
      {/* Overall progress bar */}
      <div className="mb-4">
        <div className="flex justify-between mb-1">
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
      
      {/* Overall status message */}
      {progress && (
        <div className={`mb-4 p-2 rounded text-sm ${
          progress.status === 'completed' ? 'bg-green-50 text-green-700' :
          progress.status === 'error' ? 'bg-red-50 text-red-700' :
          'bg-blue-50 text-blue-700'
        }`}>
          {progress.status === 'completed' ? 'Recognition completed successfully' : 
           progress.status === 'error' ? `Error: ${progress.error || 'An unknown error occurred'}` : 
           'Recognition in progress...'}
        </div>
      )}
      
      {/* Steps list */}
      {progress && progress.steps && progress.steps.length > 0 && (
        <div className="space-y-2">
          <h5 className="text-sm font-medium mb-2">Processing Steps</h5>
          {/* Group steps by name to avoid duplicates and show only the latest status for each step */}
          {Object.values(progress.steps.reduce((acc, step) => {
            // Use the step name as the key and keep the latest step for each name
            if (!acc[step.name] || new Date(step.timestamp) > new Date(acc[step.name].timestamp)) {
              acc[step.name] = step;
            }
            return acc;
          }, {} as Record<string, ProgressStep>)).map((step, index) => (
            <div key={index} className="flex items-center justify-between p-2 bg-gray-50 rounded">
              <div className="flex items-center">
                {step.status === 'completed' ? (
                  <svg className="w-4 h-4 text-green-600 mr-2" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                ) : step.status === 'started' ? (
                  <div className="w-4 h-4 mr-2 rounded-full border-2 border-blue-600 border-t-transparent animate-spin"></div>
                ) : step.status === 'error' ? (
                  <svg className="w-4 h-4 text-red-600 mr-2" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                  </svg>
                ) : (
                  <div className="w-4 h-4 mr-2 rounded-full border border-gray-300"></div>
                )}
                <span className="text-sm capitalize">{step.name.replace(/_/g, ' ')}</span>
              </div>
              <div className="flex items-center">
                {step.completion_percentage !== undefined && (
                  <span className="text-xs font-medium mr-2">{step.completion_percentage}%</span>
                )}
                <span className={`text-xs font-medium px-2 py-1 rounded-full ${step.status === 'completed' ? 'bg-green-100 text-green-800' : step.status === 'started' ? 'bg-blue-100 text-blue-800' : step.status === 'error' ? 'bg-red-100 text-red-800' : 'bg-gray-100 text-gray-800'}`}>
                  {step.status === 'completed' ? 'Completed' : 
                   step.status === 'started' ? 'In Progress' : 
                   step.status === 'error' ? 'Error' : 'Pending'}
                </span>
              </div>
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
      
      {/* Debug information */}
      <div className="mt-4 pt-3 border-t border-gray-200">
        <details className="text-xs text-gray-500">
          <summary className="cursor-pointer hover:text-gray-700">Debug Information</summary>
          <div className="mt-2 p-2 bg-gray-50 rounded font-mono whitespace-pre-wrap">
            <div>Capture ID: {captureId}</div>
            <div>Is Processing: {isProcessing ? 'true' : 'false'}</div>
            <div>Polling Enabled: {pollingEnabled ? 'true' : 'false'}</div>
            <div>Is Loading: {isLoading ? 'true' : 'false'}</div>
            <div>Is Error: {isError ? 'true' : 'false'}</div>
            <div>Has Progress Data: {progress ? 'true' : 'false'}</div>
            <div>Progress Status: {progress?.status || 'N/A'}</div>
            <div>Steps Count: {progress?.steps?.length || 0}</div>
          </div>
        </details>
      </div>
    </div>
  );
};

export default RecognitionProgress;
