import React, { useState, useEffect } from 'react';
import { checkCaptureStatus, CombinedStatus } from '../../utils/captureStatus';

interface CaptureStatusIndicatorProps {
  captureId: number;
  onComplete?: (status: CombinedStatus) => void;
}

const CaptureStatusIndicator: React.FC<CaptureStatusIndicatorProps> = ({ captureId, onComplete }) => {
  const [status, setStatus] = useState<CombinedStatus | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [pollInterval, setPollInterval] = useState<NodeJS.Timeout | null>(null);

  // Check status on mount and start polling
  useEffect(() => {
    if (!captureId) return;

    const checkStatus = async () => {
      try {
        setLoading(true);
        const result = await checkCaptureStatus(captureId);
        setStatus(result);
        setLoading(false);

        // If both video and audio are ready, stop polling and call onComplete
        if (result.videoReady && result.audioReady) {
          if (pollInterval) {
            clearInterval(pollInterval);
            setPollInterval(null);
          }
          if (onComplete) {
            onComplete(result);
          }
        }
      } catch (err) {
        console.error('Error checking capture status:', err);
        setError('Failed to check capture status');
        setLoading(false);
      }
    };

    // Check immediately
    checkStatus();

    // Start polling every 5 seconds
    const interval = setInterval(checkStatus, 5000);
    setPollInterval(interval);

    // Clean up on unmount
    return () => {
      if (interval) {
        clearInterval(interval);
      }
    };
  }, [captureId, onComplete]);

  // Clean up polling when component unmounts
  useEffect(() => {
    return () => {
      if (pollInterval) {
        clearInterval(pollInterval);
      }
    };
  }, [pollInterval]);

  if (loading && !status) {
    return (
      <div className="flex items-center justify-center p-4 bg-gray-100 rounded-md">
        <svg className="animate-spin h-5 w-5 mr-3 text-indigo-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
        <span>Checking capture status...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 bg-red-100 text-red-700 rounded-md">
        <p className="font-bold">Error</p>
        <p>{error}</p>
      </div>
    );
  }

  if (!status) {
    return null;
  }

  return (
    <div className="p-4 bg-gray-100 rounded-md">
      <h3 className="text-lg font-medium mb-2">Capture Status</h3>
      
      <div className="grid grid-cols-2 gap-4">
        <div>
          <p className="font-medium">Video Status:</p>
          <div className="flex items-center mt-1">
            {status.videoReady ? (
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                Ready
              </span>
            ) : (
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                Processing
              </span>
            )}
          </div>
        </div>
        
        <div>
          <p className="font-medium">Audio Status:</p>
          <div className="flex items-center mt-1">
            {status.audioReady ? (
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                Ready
              </span>
            ) : (
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                Processing
              </span>
            )}
          </div>
        </div>
      </div>
      
      <div className="mt-4">
        <p className="font-medium">Overall Status:</p>
        <p className="mt-1">{status.status}</p>
      </div>
      
      {status.videoReady && status.audioReady && (
        <div className="mt-4 p-3 bg-green-100 text-green-800 rounded-md">
          <p className="font-bold">Capture Complete!</p>
          <p>Both video and audio are ready for use.</p>
        </div>
      )}
    </div>
  );
};

export default CaptureStatusIndicator;
