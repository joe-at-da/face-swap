import React, { useState, useEffect, useCallback } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { api } from '../../utils/api';
import { toast } from 'react-toastify';
import { useAuth } from '../../contexts/AuthContext';

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
  speaker?: string;
  speaker_name?: string;
  speaker_confidence?: number;
  matched_with_video?: boolean;
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
  transcription_error?: string;
  audio_path?: string | null;
  audio_file_path?: string | null;
  video_path?: string | null;
  speaker_diarization_status?: string;
  speaker_diarization_results?: string;
  speaker_diarization_completed_at?: string;
}

interface TranscriptionProgress {
  stage?: string;
  progress?: number;
  message?: string;
  estimated_completion?: string;
}

interface TranscriptionStatus {
  id: number;
  status: string;
  error?: string;
  results_available: boolean;
  results_path?: string;
  progress?: TranscriptionProgress;
}

interface CaptureData {
  id: number;
  name?: string;
  status?: string;
  created_at?: string;
  updated_at?: string;
  audio_path?: string | null;
  audio_file_path?: string | null;
  video_path?: string | null;
  duration?: number;
  transcription_status?: string;
  transcription_error?: string;
  transcription_completed_at?: string;
  transcription_results?: string;
  speaker_diarization_status?: string;
  speaker_diarization_completed_at?: string;
}

const TranscriptionPanel: React.FC<TranscriptionPanelProps> = ({ captureId, audioElement }) => {
  const [isProcessing, setIsProcessing] = useState(false);
  const [showTranscription, setShowTranscription] = useState(false);
  const [transcriptionResults, setTranscriptionResults] = useState<TranscriptionData | null>(null);
  const [selectedSegment, setSelectedSegment] = useState<number | null>(null);

  // Fetch capture data
  const { data: capture, isLoading: captureLoading, error: captureError, refetch } = useQuery<CaptureData>({
    queryKey: ['captureTranscription', captureId],
    queryFn: async () => {
      if (!captureId) {
        // Return a default capture data object instead of undefined
        return {
          id: 0,
          status: 'unknown',
          transcription_status: 'not_started',
          transcription_results: undefined
        } as CaptureData;
      }
      
      try {
        console.log(`Fetching capture data for ID: ${captureId}`);
        const response = await api.get(`/capture/${captureId}`);
        console.log('Capture API response:', response);
        
        // Ensure we always return a valid CaptureData object
        if (response && response.data) {
          return response.data as CaptureData;
        } else {
          console.warn('API returned empty response data');
          return {
            id: captureId,
            status: 'unknown',
            transcription_status: 'unknown'
          } as CaptureData;
        }
      } catch (error) {
        console.error('Error fetching capture data:', error);
        // Return a default capture data object with error information
        return {
          id: captureId,
          status: 'error',
          transcription_status: 'error',
          transcription_error: error instanceof Error ? error.message : String(error)
        } as CaptureData;
      }
    },
    enabled: !!captureId,
    refetchInterval: 5000, // Poll every 5 seconds for better progress updates
    staleTime: 0 // Consider data always stale to ensure fresh data
  });

  // Get authentication token
  const { token } = useAuth();

  // Fetch transcription status
  const {
    data: transcriptionStatus,
    isLoading,
    error,
    refetch: refetchStatus
  } = useQuery<TranscriptionStatus>({
    queryKey: ['transcriptionStatus', captureId, token],
    queryFn: async () => {
      if (!captureId || !token) {
        // Return a default status object instead of null
        return {
          id: captureId || 0,
          status: 'not_started',
          results_available: false
        } as TranscriptionStatus;
      }
      
      try {
        // Use the same base URL as the successful capture API calls (port 8000)
        const response = await fetch(`http://localhost:8000/api/v1/audio-transcription/status/${captureId}`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        
        if (!response.ok) {
          console.warn(`Failed to fetch transcription status: ${response.statusText}`);
          // Return a default status object with error information
          return {
            id: captureId,
            status: 'error',
            error: `API Error: ${response.statusText}`,
            results_available: false
          } as TranscriptionStatus;
        }
        
        const data = await response.json();
        return data;
      } catch (error) {
        console.error('Error fetching transcription status:', error);
        // Return a default status object with error information instead of throwing
        return {
          id: captureId,
          status: 'error',
          error: error instanceof Error ? error.message : String(error),
          results_available: false
        } as TranscriptionStatus;
      }
    },
    enabled: !!captureId && !!token,
    refetchInterval: 5000, // Poll every 5 seconds for better progress updates
    refetchIntervalInBackground: true
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
  const startTranscription = async (withSpeakerDiarization: boolean = false) => {
    if (!captureId) return;

    try {
      setIsProcessing(true);
      const response = await fetch('http://localhost:8000/api/v1/audio-transcription/transcribe', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          capture_id: captureId,
          model_size: 'medium',
          with_speaker_diarization: withSpeakerDiarization
        }),
      });

      if (!response.ok) {
        throw new Error(`Failed to start transcription: ${response.statusText}`);
      }

      const data = await response.json();
      console.log('Transcription started:', data);

      // Start polling for status
      refetch();
      refetchStatus();
    } catch (err) {
      console.error('Error starting transcription:', err);
      toast.error(`Failed to start transcription: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setIsProcessing(false);
    }
  };

  // Process transcription mutation - used to start the transcription process
  const processMutation = useMutation({
    mutationFn: async () => {
      return startTranscription(true);
    },
    onSuccess: () => {
      console.log('Transcription processing started successfully');
    },
    onError: (error) => {
      console.error('Error starting transcription:', error);
    }
  });

  // Fetch transcription results
  const fetchTranscriptionResults = useCallback(async () => {
    if (!captureId || !token) return { success: false, message: 'Missing capture ID or token' };

    try {
      const response = await fetch(`http://localhost:8000/api/v1/audio-transcription/results/${captureId}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      if (!response.ok) {
        throw new Error(`Failed to fetch transcription results: ${response.statusText}`);
      }

      const data = await response.json();
      console.log('Transcription results:', data);
      
      // Enhanced debugging
      if (data.success === false) {
        console.error('API returned success: false', data);
      }
      
      if (data.results) {
        console.log('Results structure:', Object.keys(data.results));
        console.log('Results text available:', !!data.results.text);
        console.log('Results segments available:', Array.isArray(data.results.segments) ? data.results.segments.length : 'not an array');
        
        // Make sure we have a valid TranscriptionData object
        const processedResults = {
          text: data.results.text || '',
          segments: Array.isArray(data.results.segments) ? data.results.segments : [],
          language: data.results.language || 'en'
        };
        
        setTranscriptionResults(processedResults);
        setShowTranscription(true);
        return { success: true, results: processedResults };
      } else {
        console.error('No results property in response');
        toast.error('No transcription results available');
        return { success: false, message: 'No transcription results available' };
      }
    } catch (err) {
      console.error('Error fetching transcription results:', err);
      toast.error(`Failed to fetch transcription results: ${err instanceof Error ? err.message : String(err)}`);
      return { success: false, error: err instanceof Error ? err.message : String(err) };
    }
  }, [captureId, token]);

  // Automatically fetch results when transcription is completed
  useEffect(() => {
    if (transcriptionStatus && transcriptionStatus.status === 'completed' && 
        transcriptionStatus.results_available && !transcriptionResults) {
      console.log('Transcription completed, fetching results...');
      fetchTranscriptionResults();
    }
  }, [transcriptionStatus, transcriptionResults, captureId, fetchTranscriptionResults]);

  // Play specific segment when selected
  useEffect(() => {
    if (selectedSegment !== null && transcriptionResults && audioElement) {
      const segment = transcriptionResults.segments[selectedSegment];
      if (segment) {
        console.log(`Playing segment ${selectedSegment} at ${segment.start}s`);
        audioElement.currentTime = segment.start;
        audioElement.play().catch(err => {
          console.error('Error playing audio:', err);
        });
      }
    }
  }, [selectedSegment, transcriptionResults, audioElement]);

  // Render status message based on capture data
  const renderCaptureStatusMessage = () => {
    if (!capture) {
      return null;
    }

    if (capture.transcription_error) {
      return (
        <div className="text-red-500 mb-2">
          Error: {capture.transcription_error}
        </div>
      );
    }

    if (capture.transcription_completed_at) {
      return (
        <div className="text-green-500 mb-2">
          Transcription completed at {new Date(capture.transcription_completed_at).toLocaleString()}
        </div>
      );
    }

    if (capture.transcription_status === 'processing') {
      return (
        <div className="text-blue-500 mb-2">
          Transcription in progress...
          <div className="text-sm text-gray-500 mt-2">
            Checking for updates every 5 seconds...
          </div>
        </div>
      );
    }

    return null;
  };

  // Check if audio file is available
  const isAudioAvailable = () => {
    return capture && (capture.audio_path || capture.audio_file_path);
  };

  // Check if transcription is available
  const isTranscriptionAvailable = () => {
    return transcriptionStatus && transcriptionStatus.status === 'completed' && transcriptionResults !== null;
  };

  // Check if transcription is in progress
  const isTranscriptionInProgress = () => {
    return transcriptionStatus && transcriptionStatus.status === 'processing';
  };

  // Check if transcription has failed
  const isTranscriptionFailed = () => {
    return transcriptionStatus && transcriptionStatus.status === 'error';
  };

  // Check if transcription has not started
  const isTranscriptionNotStarted = () => {
    return !transcriptionStatus || transcriptionStatus.status === 'not_started';
  };

  // Handle button click to start transcription process
  const handleStartTranscription = () => {
    if (isTranscriptionInProgress() || isTranscriptionAvailable()) {
      console.log('Not starting transcription - already processing or completed');
      return;
    }
    
    console.log('Starting transcription process...');
    startTranscription(true); // Start with speaker diarization enabled
  };

  // State for search functionality and UI tabs
  const [searchQuery, setSearchQuery] = useState('');
  const [filteredSegments, setFilteredSegments] = useState<TranscriptionSegment[]>([]);
  const [activeTab, setActiveTab] = useState<'segments' | 'fullText'>('segments');

  // Effect to filter segments based on search query
  useEffect(() => {
    if (!transcriptionResults?.segments || searchQuery.trim() === '') {
      setFilteredSegments(transcriptionResults?.segments || []);
      return;
    }

    const query = searchQuery.toLowerCase();
    const filtered = transcriptionResults.segments.filter(segment => 
      segment.text.toLowerCase().includes(query)
    );
    setFilteredSegments(filtered);
  }, [searchQuery, transcriptionResults]);

  // Function to export transcription as text
  const exportTranscription = () => {
    if (!transcriptionResults) return;
    
    const text = transcriptionResults.text;
    const blob = new Blob([text], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `transcription_capture_${captureId}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const renderProgressBar = (progress?: number) => {
    if (progress === undefined) return null;
    
    return (
      <div className="w-full bg-gray-200 rounded-full h-2.5 mb-2">
        <div 
          className="bg-blue-600 h-2.5 rounded-full" 
          style={{ width: `${Math.min(100, progress)}%` }}
        ></div>
      </div>
    );
  };

  const formatEstimatedTime = (isoString?: string) => {
    if (!isoString) return null;
    
    try {
      const estimatedTime = new Date(isoString);
      const now = new Date();
      const diffMs = estimatedTime.getTime() - now.getTime();
      
      if (diffMs <= 0) return "almost done";
      
      const diffMinutes = Math.round(diffMs / 60000);
      if (diffMinutes < 1) return "less than a minute";
      if (diffMinutes === 1) return "about 1 minute";
      return `about ${diffMinutes} minutes`;
    } catch (e) {
      return null;
    }
  };

  const getStageLabel = (stage?: string) => {
    if (!stage) return "Processing";
    
    const stageLabels: Record<string, string> = {
      "initializing": "Initializing",
      "setup": "Setting up",
      "voice_database": "Updating voice database",
      "diarization": "Identifying speakers",
      "fallback_diarization": "Using alternative speaker identification",
      "speaker_matching": "Matching speakers",
      "combining": "Combining results",
      "facial_recognition": "Processing facial recognition",
      "combining_video": "Combining audio and video data",
      "fallback_combining": "Finalizing results",
      "completed": "Completed",
      "completed_with_errors": "Completed with some issues",
      "error": "Error"
    };
    
    return stageLabels[stage] || stage.charAt(0).toUpperCase() + stage.slice(1).replace(/_/g, ' ');
  };

  const renderStatus = () => {
    if (!captureId) {
      return <div className="text-gray-500">No capture selected</div>;
    }

    if (isLoading) {
      return <div className="text-blue-500">Loading transcription status...</div>;
    }

    if (error) {
      return <div className="text-red-500">Error: {error instanceof Error ? error.message : String(error)}</div>;
    }

    if (!transcriptionStatus) {
      return <div className="text-gray-500">No transcription status available</div>;
    }

    if (transcriptionStatus.status === "error") {
      return (
        <div className="text-red-500">
          Transcription failed: {transcriptionStatus.error || "Unknown error"}
        </div>
      );
    }

    if (transcriptionStatus.status === "processing") {
      const progress = transcriptionStatus.progress;
      const estimatedTimeRemaining = formatEstimatedTime(progress?.estimated_completion);
      const stageLabel = getStageLabel(progress?.stage);
      
      return (
        <div className="text-blue-500">
          <div className="font-semibold mb-1">Transcription in progress</div>
          {progress?.progress !== undefined && (
            <div className="mb-2">
              {renderProgressBar(progress.progress)}
              <div className="text-sm flex justify-between">
                <span>{stageLabel}: {progress.progress}%</span>
                {estimatedTimeRemaining && (
                  <span>Estimated time remaining: {estimatedTimeRemaining}</span>
                )}
              </div>
            </div>
          )}
          {progress?.message && (
            <div className="text-sm italic">{progress.message}</div>
          )}
          {!progress && (
            <div className="text-sm">(checking status every 5 seconds)</div>
          )}
        </div>
      );
    }

    if (transcriptionStatus.status === "completed" && transcriptionStatus.results_available) {
      return (
        <div className="text-green-500">
          Transcription completed. Results available.
        </div>
      );
    }

    return <div className="text-gray-500">Status: {transcriptionStatus.status}</div>;
  };

  const handleCopyTranscription = () => {
    if (transcriptionStatus && transcriptionStatus.status === 'completed' && transcriptionResults) {
      navigator.clipboard.writeText(transcriptionResults.text)
        .then(() => {
          console.log('Transcription copied to clipboard');
          toast.success('Transcription copied to clipboard');
        })
        .catch(err => {
          console.error('Error copying to clipboard:', err);
          toast.error('Failed to copy to clipboard');
        });
    }
  };

  const handleDownloadTranscription = () => {
    if (transcriptionStatus && transcriptionStatus.status === 'completed' && transcriptionResults) {
      // Create a blob with the transcription text
      const blob = new Blob([transcriptionResults.text], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      
      // Create a temporary link and trigger download
      const a = document.createElement('a');
      a.href = url;
      a.download = `transcription_${captureId}.txt`;
      document.body.appendChild(a);
      a.click();
      
      // Clean up
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }
  };

  const handleViewTranscription = () => {
    if (transcriptionStatus && transcriptionStatus.status === 'completed') {
      fetchTranscriptionResults();
      setShowTranscription(true);
    }
  };

  return (
    <div className="mt-6">
      <div className="flex justify-between items-center mb-3">
        <h3 className="text-lg font-medium">Audio Transcription</h3>
        {transcriptionStatus && transcriptionStatus.status === 'completed' && transcriptionResults && (
          <button 
            onClick={exportTranscription}
            className="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 text-gray-700 rounded flex items-center"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            Export Text
          </button>
        )}
      </div>
      
      {(!transcriptionStatus || transcriptionStatus.status === 'not_started') && !isProcessing && (
        <div className="bg-gray-50 p-6 rounded-lg border border-gray-200 shadow-sm">
          <div className="flex items-start mb-4">
            <div className="bg-blue-100 p-2 rounded-full mr-3">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
              </svg>
            </div>
            <div>
              <h4 className="font-medium text-gray-800 mb-1">Speech-to-Text Transcription</h4>
              <p className="text-gray-600 mb-4">
                Convert the audio to text with timestamps. This will create a searchable transcript of the parliamentary session.
              </p>
              <button
                onClick={handleStartTranscription}
                disabled={processMutation.isPending}
                className={`px-4 py-2 rounded text-white flex items-center ${processMutation.isPending ? 'bg-gray-400 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700'}`}
              >
                {processMutation.isPending ? (
                  <>
                    <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Starting...
                  </>
                ) : (
                  <>
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                    </svg>
                    Start Transcription
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
      
      {isProcessing && (
        <div className="bg-blue-50 p-6 rounded-lg border border-blue-200 shadow-sm mb-4">
          <div className="flex items-center mb-3">
            <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-blue-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <span className="text-blue-700 font-medium">Transcribing audio...</span>
          </div>
          <div className="bg-white rounded-lg p-4 border border-blue-100">
            <div className="mb-2">
              <div className="h-2 w-full bg-gray-200 rounded-full overflow-hidden">
                <div className="h-full bg-blue-500 rounded-full animate-pulse" style={{ width: '60%' }}></div>
              </div>
            </div>
            <p className="text-sm text-gray-600">
              The system is processing the audio file using speech recognition. This may take several minutes depending on the length of the audio.
            </p>
            <div className="mt-3 text-xs text-gray-500 flex items-center">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              Refreshing status every 5 seconds...
            </div>
          </div>
        </div>
      )}
      
      {captureId && (
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm mb-4 overflow-hidden">
          <div className="p-4 border-b border-gray-200 bg-gray-50">
            <div className="flex justify-between items-center">
              <h4 className="font-medium text-gray-800">Transcription Status</h4>
            </div>
          </div>
          <div className="p-4">
            {renderStatus()}
          </div>
        </div>
      )}
      
      {transcriptionStatus && transcriptionStatus.status === 'completed' && transcriptionResults && (
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm mb-4 overflow-hidden">
          <div className="p-4 border-b border-gray-200 bg-gray-50">
            <div className="flex justify-between items-center">
              <h4 className="font-medium text-gray-800">Transcription Results</h4>
              <div className="flex items-center space-x-2">
                <div className="relative">
                  <input
                    type="text"
                    placeholder="Search in transcript..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-8 pr-3 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                  />
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 text-gray-400 absolute left-2 top-1.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                  {searchQuery && (
                    <button 
                      onClick={() => setSearchQuery('')}
                      className="absolute right-2 top-1.5 text-gray-400 hover:text-gray-600"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  )}
                </div>
                {searchQuery && (
                  <span className="text-xs text-gray-500">
                    {filteredSegments.length} {filteredSegments.length === 1 ? 'result' : 'results'}
                  </span>
                )}
              </div>
            </div>
          </div>
          
          <div className="p-4">
            {/* Tabs for different views */}
            <div className="border-b border-gray-200 mb-4">
              <nav className="-mb-px flex space-x-6">
                <button 
                  onClick={() => setActiveTab('segments')}
                  className={`whitespace-nowrap py-2 px-1 border-b-2 font-medium text-sm transition-colors ${activeTab === 'segments' ? 'border-blue-500 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}`}
                >
                  Segments
                </button>
                <button 
                  onClick={() => setActiveTab('fullText')}
                  className={`whitespace-nowrap py-2 px-1 border-b-2 font-medium text-sm transition-colors ${activeTab === 'fullText' ? 'border-blue-500 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}`}
                >
                  Full Text
                </button>
              </nav>
            </div>
            
            {/* Segments view */}
            {activeTab === 'segments' && (
              filteredSegments && filteredSegments.length > 0 ? (
                <div className="space-y-3 max-h-[500px] overflow-y-auto pr-2">
                  {filteredSegments.map((segment, index) => (
                    <div 
                      key={segment.id} 
                      className={`p-3 mb-2 rounded-md cursor-pointer transition-colors ${selectedSegment === segment.id ? 'bg-blue-100 border-blue-300' : 'bg-white hover:bg-gray-50 border-gray-200'} border`}
                      onClick={() => {
                        setSelectedSegment(segment.id);
                        jumpToTimestamp(segment.start);
                      }}
                    >
                      <div className="flex justify-between items-center mb-1">
                        <span className="text-xs font-medium text-gray-500">
                          {formatTime(segment.start)} - {formatTime(segment.end)}
                        </span>
                        <span className="text-xs text-gray-400">
                          {Math.round((segment.end - segment.start) * 10) / 10}s
                        </span>
                      </div>
                      {segment.speaker_name && (
                        <div className="flex items-center mb-2">
                          <div 
                            className={`px-2 py-1 rounded-full text-xs font-medium mr-2 ${segment.matched_with_video ? 'bg-green-100 text-green-800' : 'bg-blue-100 text-blue-800'}`}
                          >
                            {segment.speaker_name}
                            {segment.speaker_confidence && segment.speaker_confidence > 0.7 && (
                              <span className="ml-1 text-xs">✓</span>
                            )}
                          </div>
                          {segment.matched_with_video && (
                            <span className="text-xs text-gray-500 flex items-center">
                              <svg xmlns="http://www.w3.org/2000/svg" className="h-3 w-3 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                              </svg>
                              Video match
                            </span>
                          )}
                        </div>
                      )}
                      <p className="text-sm text-blue-100">
                        {searchQuery ? (
                          <span dangerouslySetInnerHTML={{
                            __html: segment.text.replace(
                              new RegExp(`(${searchQuery})`, 'gi'),
                              '<mark class="bg-yellow-200 rounded px-0.5">$1</mark>'
                            )
                          }} />
                        ) : segment.text}
                      </p>
                      {segment.no_speech_prob && segment.no_speech_prob > 0.1 && (
                        <div className="mt-1 flex items-center text-xs text-amber-600">
                          <svg xmlns="http://www.w3.org/2000/svg" className="h-3 w-3 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                          </svg>
                          Low confidence segment ({Math.round((1 - segment.no_speech_prob) * 100)}%)
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              ) : searchQuery ? (
                <div className="text-center py-8">
                  <p className="text-gray-500">No segments found matching "{searchQuery}"</p>
                  <button 
                    onClick={() => setSearchQuery('')}
                    className="mt-2 text-blue-600 text-sm hover:underline"
                  >
                    Clear search
                  </button>
                </div>
              ) : (
                <div className="text-center py-8">
                  <p className="text-gray-500">No segments available in the transcription</p>
                </div>
              )
            )}
            
            {/* Full Text view */}
            {activeTab === 'fullText' && transcriptionResults && (
              <div className="bg-gray-800 rounded-lg border border-gray-600 p-4 max-h-[500px] overflow-y-auto">
                {searchQuery && transcriptionResults.text ? (
                  <div className="text-sm text-blue-100 whitespace-pre-wrap" dangerouslySetInnerHTML={{
                    __html: transcriptionResults.text.replace(
                      new RegExp(`(${searchQuery})`, 'gi'),
                      '<mark class="bg-yellow-200 rounded px-0.5">$1</mark>'
                    )
                  }} />
                ) : (
                  <div className="text-sm text-blue-100 whitespace-pre-wrap">
                    {transcriptionResults.text || 'No transcript text available.'}
                  </div>
                )}
              </div>
            )}
            
            {/* Language detection */}
            {transcriptionResults.language && (
              <div className="mt-4 pt-3 border-t border-gray-200 flex items-center text-sm text-gray-500">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-1 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5h12M9 3v2m1.048 9.5A18.022 18.022 0 016.412 9m6.088 9h7M11 21l5-10 5 10M12.751 5C11.783 10.77 8.07 15.61 3 18.129" />
                </svg>
                Detected language: <span className="font-medium ml-1">{transcriptionResults.language}</span>
              </div>
            )}
          </div>
        </div>
      )}
      
      {transcriptionStatus && transcriptionStatus.status === 'completed' && transcriptionStatus.results_available && !transcriptionResults && (
        <div className="bg-yellow-50 p-6 rounded-lg border border-yellow-200 shadow-sm mb-4">
          <div className="flex items-start">
            <div className="bg-yellow-100 p-2 rounded-full mr-3">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-yellow-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
            <div>
              <h4 className="font-medium text-yellow-800 mb-1">Transcription Results Available</h4>
              <p className="text-yellow-700">
                Transcription completed, but there was an issue displaying the results in the UI. You can access the transcription directly using the link below.
              </p>
              {capture?.transcription_path && (
                <div className="mt-3 p-3 bg-white rounded border border-yellow-200">
                  <p className="font-medium text-sm mb-2">Transcription File:</p>
                  <code className="block bg-gray-50 p-2 rounded text-sm overflow-x-auto">
                    {capture.transcription_path}
                  </code>
                  <a 
                    href={`http://localhost:8000/api/v1/audio-transcription/results/${captureId}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="mt-3 px-3 py-1 text-sm bg-blue-100 hover:bg-blue-200 text-blue-800 rounded inline-flex items-center"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                    </svg>
                    View Transcription JSON
                  </a>
                </div>
              )}
              <button
                onClick={handleStartTranscription}
                className="mt-3 px-3 py-1 text-sm bg-yellow-100 hover:bg-yellow-200 text-yellow-800 rounded inline-flex items-center"
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                Try Again
              </button>
            </div>
          </div>
        </div>
      )}
      
      {transcriptionStatus && transcriptionStatus.status === 'completed' && !transcriptionResults && (
        <div className="bg-yellow-50 p-6 rounded-lg border border-yellow-200 shadow-sm mb-4">
          <div className="flex items-start">
            <div className="bg-yellow-100 p-2 rounded-full mr-3">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-yellow-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
            <div>
              <h4 className="font-medium text-yellow-800 mb-1">No Transcription Results</h4>
              <p className="text-yellow-700">
                Transcription completed, but no results were found. The audio might not contain any recognizable speech or there might have been an issue with the processing.
              </p>
              <button
                onClick={handleStartTranscription}
                className="mt-3 px-3 py-1 text-sm bg-yellow-100 hover:bg-yellow-200 text-yellow-800 rounded inline-flex items-center"
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                Try Again
              </button>
            </div>
          </div>
        </div>
      )}
      
      {transcriptionStatus && transcriptionStatus.status === 'error' && (
        <div className="bg-red-50 p-6 rounded-lg border border-red-200 shadow-sm mb-4">
          <div className="flex items-start">
            <div className="bg-red-100 p-2 rounded-full mr-3">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div>
              <h4 className="font-medium text-red-800 mb-1">Transcription Error</h4>
              {capture?.transcription_error?.includes('No audio') || 
               capture?.transcription_error?.includes('does not have audio') ? (
                <div>
                  <p className="text-red-700">
                    <strong>No audio found in this capture.</strong> This video file doesn't contain an audio track that can be transcribed.
                  </p>
                  <div className="mt-3 p-3 bg-gray-50 border border-gray-200 rounded text-sm text-gray-700">
                    <p className="mb-2">Possible solutions:</p>
                    <ul className="list-disc pl-5 space-y-1">
                      <li>Verify that the original source has audio</li>
                      <li>Try re-capturing the session with audio enabled</li>
                      <li>Upload a separate audio file for this capture</li>
                    </ul>
                  </div>
                </div>
              ) : (
                <div>
                  <p className="text-red-700">
                    An error occurred during the transcription process. This might be due to issues with the audio file or the transcription service.
                  </p>
                  <button
                    onClick={handleStartTranscription}
                    className="mt-3 px-3 py-1 text-sm bg-red-100 hover:bg-red-200 text-red-800 rounded inline-flex items-center"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                    Try Again
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default TranscriptionPanel;
