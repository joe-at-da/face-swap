import React, { useState, useEffect, useCallback } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { api } from '../../utils/api';

interface TranscriptionPanelProps {
  captureId: number;
  audioElement?: HTMLAudioElement | null;
}

interface TranscriptionData {
  text: string;
  segments: TranscriptionSegment[];
  language: string;
}

interface TranscriptionSegment {
  id: number;
  start: number;
  end: number;
  text: string;
  tokens?: number[];
  temperature?: number;
  avg_logprob?: number;
  compression_ratio?: number;
  no_speech_prob?: number;
}

interface CaptureData {
  id: number;
  status?: string;
  transcription_status?: string;
  transcription_path?: string;
  transcription_results?: string;
  transcription_completed_at?: string;
}

const TranscriptionPanel: React.FC<TranscriptionPanelProps> = ({ captureId, audioElement }) => {
  const [isProcessing, setIsProcessing] = useState(false);
  const [showTranscription, setShowTranscription] = useState(false);
  const [transcriptionStatus, setTranscriptionStatus] = useState<string | undefined>(undefined);
  const [transcriptionResults, setTranscriptionResults] = useState<TranscriptionData | null>(null);
  const [selectedSegment, setSelectedSegment] = useState<number | null>(null);

  console.log('TranscriptionPanel render state:', { isProcessing, showTranscription, transcriptionStatus });

  // Fetch capture data to get transcription status
  const { data: capture, isLoading, isError, error, refetch } = useQuery<CaptureData>({
    queryKey: ['captureTranscription', captureId],
    queryFn: async () => {
      console.log(`Fetching capture data for ID: ${captureId}`);
      const response = await api.get(`/capture/${captureId}`);
      console.log('Capture API response:', response);
      return response as CaptureData;
    },
    refetchInterval: 3000, // Poll every 3 seconds
    staleTime: 0, // Consider data always stale to ensure fresh data
  });

  // Helper function to format time in MM:SS format
  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  // Function to jump to a specific timestamp in the audio
  const jumpToTimestamp = (seconds: number) => {
    if (audioElement) {
      audioElement.currentTime = seconds;
      audioElement.play().catch(err => console.error('Error playing audio:', err));
    }
  };

  // Function to start the transcription process
  const startTranscription = useCallback(async () => {
    if (!captureId) return;
    
    // Don't start transcription if it's already completed or processing
    if (transcriptionStatus === 'completed' || transcriptionStatus === 'processing' || isProcessing) {
      console.log(`Transcription already ${transcriptionStatus}, not starting again`);
      return;
    }
    
    setIsProcessing(true);
    setShowTranscription(true);
    
    console.log(`Starting transcription processing for capture ID: ${captureId}`);
    
    try {
      const response = await api.post('/audio-transcription/transcribe', {
        capture_id: captureId,
        model_size: "medium"
      });
      
      console.log('Transcription process started:', response);
      
      // Refetch capture data to get updated status
      refetch();
    } catch (error) {
      console.error('Error starting transcription process:', error);
      setIsProcessing(false);
    }
  }, [captureId, refetch, transcriptionStatus, isProcessing]);

  // Process transcription mutation - used to start the transcription process
  const processMutation = useMutation({
    mutationFn: startTranscription,
    onSuccess: () => {
      console.log('Transcription processing started successfully');
    },
    onError: (error) => {
      console.error('Error in transcription processing:', error);
      setIsProcessing(false);
    }
  });

  // Fetch transcription results when status is completed
  const fetchTranscriptionResults = useCallback(async () => {
    if (!captureId || transcriptionStatus !== 'completed') return;
    
    try {
      console.log(`Fetching transcription results for capture ID: ${captureId}`);
      const response = await api.get(`/audio-transcription/results/${captureId}`);
      console.log('Transcription results:', response);
      
      if (response.success && response.results) {
        setTranscriptionResults(response.results);
      }
    } catch (error) {
      console.error('Error fetching transcription results:', error);
    }
  }, [captureId, transcriptionStatus]);

  // Effect to update state based on capture data changes
  useEffect(() => {
    if (capture) {
      console.log('Capture data changed:', capture);
      console.log('Current status in state:', { isProcessing, transcriptionStatus });
      
      // Check for transcription status
      if (capture.transcription_status) {
        console.log(`Setting transcription status to: ${capture.transcription_status}`);
        setTranscriptionStatus(capture.transcription_status);
        
        // If status is completed or error, update the processing state
        if (capture.transcription_status === 'completed' || capture.transcription_status === 'error') {
          console.log(`Transcription process is ${capture.transcription_status}, updating UI state`);
          setIsProcessing(false);
          setShowTranscription(true);
          
          // Try to parse and set the transcription results if available
          if (capture.transcription_results) {
            console.log('Transcription results found, parsing...');
            try {
              const results = typeof capture.transcription_results === 'string' 
                ? JSON.parse(capture.transcription_results)
                : capture.transcription_results;
              console.log('Parsed transcription results:', results);
              setTranscriptionResults(results);
            } catch (e) {
              console.error('Error parsing transcription results:', e);
            }
          } else {
            // If no results in the capture data, fetch them separately
            fetchTranscriptionResults();
          }
        } else if (capture.transcription_status === 'processing') {
          // If status is processing, update the processing state
          console.log('Transcription is still processing');
          setIsProcessing(true);
          setShowTranscription(true);
        }
      }
      
      // Force update UI based on transcription_completed_at
      if (capture.transcription_completed_at) {
        console.log('Transcription has a completed timestamp:', capture.transcription_completed_at);
        setIsProcessing(false);
        setTranscriptionStatus('completed');
        setShowTranscription(true);
        
        // Fetch results if we don't have them yet
        if (!transcriptionResults) {
          fetchTranscriptionResults();
        }
      }
    }
  }, [capture, isProcessing, transcriptionStatus, transcriptionResults, fetchTranscriptionResults]);

  // Handle button click to start transcription process
  const handleStartTranscription = () => {
    // Don't start if already processing or completed
    if (isProcessing || transcriptionStatus === 'completed') {
      console.log('Not starting transcription - already processing or completed');
      return;
    }
    processMutation.mutate();
  };

  return (
    <div className="mt-6">
      <h3 className="text-lg font-medium mb-2">Audio Transcription</h3>
      
      {!transcriptionStatus && !isProcessing && (
        <div className="bg-gray-50 p-4 rounded border border-gray-200">
          <p className="text-gray-700 mb-3">
            No transcription data available for this capture. Process this audio for speech-to-text transcription.
          </p>
          <button
            onClick={handleStartTranscription}
            disabled={processMutation.isPending}
            className={`px-4 py-2 rounded text-white ${processMutation.isPending ? 'bg-gray-400 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700'}`}
          >
            {processMutation.isPending ? 'Starting...' : 'Start Transcription'}
          </button>
        </div>
      )}
      
      {isProcessing && (
        <div className="bg-gray-50 p-4 rounded border border-gray-200 mb-4">
          <div className="flex items-center">
            <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-blue-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <span className="text-blue-600">Transcribing audio... This may take a few minutes.</span>
          </div>
          <p className="text-sm text-gray-500 mt-2">
            The system is processing the audio file using speech recognition. Please wait.
          </p>
        </div>
      )}
      
      {transcriptionStatus === 'completed' && transcriptionResults && (
        <div className="bg-white p-4 rounded border border-gray-200 mb-4">
          <h4 className="font-medium mb-3">Transcription Results</h4>
          
          {/* Full text transcription */}
          <div className="mb-4">
            <h5 className="text-sm font-medium mb-2">Full Text</h5>
            <div className="bg-gray-50 p-3 rounded text-sm">
              {transcriptionResults.text}
            </div>
          </div>
          
          {/* Segments */}
          {transcriptionResults.segments && transcriptionResults.segments.length > 0 && (
            <div>
              <h5 className="text-sm font-medium mb-2">Segments</h5>
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {transcriptionResults.segments.map((segment, index) => (
                  <div 
                    key={index} 
                    className={`p-3 rounded border ${selectedSegment === index ? 'border-blue-400 bg-blue-50' : 'border-gray-200 bg-gray-50'}`}
                    onClick={() => setSelectedSegment(index)}
                  >
                    <div className="flex justify-between items-start">
                      <div className="text-sm text-gray-500">
                        {formatTime(segment.start)} - {formatTime(segment.end)}
                      </div>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          jumpToTimestamp(segment.start);
                        }}
                        className="px-2 py-1 text-xs bg-blue-100 text-blue-700 rounded hover:bg-blue-200"
                      >
                        Play Segment
                      </button>
                    </div>
                    <p className="mt-1 text-sm">{segment.text}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
          
          {/* Language detection */}
          {transcriptionResults.language && (
            <div className="mt-4 text-sm text-gray-500">
              Detected language: <span className="font-medium">{transcriptionResults.language}</span>
            </div>
          )}
        </div>
      )}
      
      {transcriptionStatus === 'completed' && !transcriptionResults && (
        <div className="bg-white p-4 rounded border border-gray-200 mb-4">
          <p className="text-gray-700">
            Transcription completed, but no results were found. The audio might not contain any recognizable speech.
          </p>
        </div>
      )}
      
      {transcriptionStatus === 'error' && (
        <div className="bg-red-50 p-4 rounded border border-red-200 mb-4">
          <p className="text-red-700">
            An error occurred during transcription. Please try again.
          </p>
        </div>
      )}
    </div>
  );
};

export default TranscriptionPanel;
