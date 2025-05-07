import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../../utils/api';

interface Speaker {
  name: string;
  confidence: number;
  start_time: number;
  end_time: number;
  duration: number;
}

interface RecognitionSectionProps {
  captureId: number;
  videoElement: HTMLVideoElement | null;
}

const RecognitionSection: React.FC<RecognitionSectionProps> = ({ captureId, videoElement }) => {
  const queryClient = useQueryClient();
  const [isProcessing, setIsProcessing] = useState(false);
  
  // Fetch recognition data
  const { data: recognitionData, isLoading, isError } = useQuery({
    queryKey: ['recognition', captureId],
    queryFn: async () => {
      const captureData = await api.get(`/capture/${captureId}`);
      
      // Check if speaker identification results exist
      if (captureData.speaker_identification_results) {
        return {
          hasSpeakerIdentification: true,
          speakerResults: captureData.speaker_identification_results,
          hasTranscription: !!captureData.has_transcription,
          transcriptionId: captureData.transcription_id
        };
      }
      
      return {
        hasSpeakerIdentification: false,
        speakerResults: null,
        hasTranscription: !!captureData.has_transcription,
        transcriptionId: captureData.transcription_id
      };
    },
    enabled: !!captureId
  });
  
  // Fetch transcription if available
  const { data: transcriptionData } = useQuery({
    queryKey: ['transcription', recognitionData?.transcriptionId],
    queryFn: async () => {
      if (!recognitionData?.transcriptionId) return null;
      return await api.get(`/transcription/${recognitionData.transcriptionId}`);
    },
    enabled: !!recognitionData?.transcriptionId
  });
  
  // Mutation for starting recognition processing
  const processMutation = useMutation({
    mutationFn: async () => {
      setIsProcessing(true);
      return await api.post('/recognition/combined-recognition', {
        video_id: captureId,
        save_output: true
      });
    },
    onSuccess: () => {
      // Invalidate and refetch queries
      queryClient.invalidateQueries({ queryKey: ['recognition', captureId] });
      queryClient.invalidateQueries({ queryKey: ['captureSession', captureId] });
      setIsProcessing(false);
    },
    onError: (error) => {
      console.error('Error processing recognition:', error);
      setIsProcessing(false);
    }
  });
  
  const handleStartProcessing = () => {
    processMutation.mutate();
  };
  
  const jumpToTimestamp = (seconds: number) => {
    if (videoElement) {
      videoElement.currentTime = seconds;
      videoElement.play().catch(err => console.error('Error playing video:', err));
    }
  };
  
  const formatTime = (seconds: number): string => {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.floor(seconds % 60);
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
  };
  
  if (isLoading) {
    return (
      <div className="mt-8">
        <h3 className="text-lg font-semibold mb-4">Recognition</h3>
        <div className="text-gray-500">Loading recognition data...</div>
      </div>
    );
  }
  
  if (isError) {
    return (
      <div className="mt-8">
        <h3 className="text-lg font-semibold mb-4">Recognition</h3>
        <div className="bg-red-50 border-l-4 border-red-500 p-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
            <div className="ml-3">
              <p className="text-sm text-red-700">Error loading recognition data.</p>
            </div>
          </div>
        </div>
      </div>
    );
  }
  
  // If no recognition data is available
  if (!recognitionData?.hasSpeakerIdentification && !recognitionData?.hasTranscription) {
    return (
      <div className="mt-8">
        <h3 className="text-lg font-semibold mb-4">Recognition</h3>
        <div className="bg-gray-50 border border-gray-200 rounded-md p-4 mb-4">
          <p className="text-gray-700 mb-4">
            No recognition data available for this capture. Process this capture for speaker identification and transcription.
          </p>
          <button
            onClick={handleStartProcessing}
            disabled={isProcessing}
            className={`px-4 py-2 rounded-md text-white ${
              isProcessing ? 'bg-blue-400 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700'
            }`}
          >
            {isProcessing ? 'Processing...' : 'Process Recognition'}
          </button>
        </div>
      </div>
    );
  }
  
  return (
    <div className="mt-8">
      <h3 className="text-lg font-semibold mb-4">Recognition</h3>
      
      {/* Speaker Identification Results */}
      {recognitionData?.hasSpeakerIdentification && recognitionData.speakerResults && (
        <div className="mb-6">
          <h4 className="text-md font-medium mb-3">Speaker Identification</h4>
          <div className="space-y-3 max-h-80 overflow-y-auto">
            {recognitionData.speakerResults.speakers && recognitionData.speakerResults.speakers.length > 0 ? (
              recognitionData.speakerResults.speakers.map((speaker: Speaker, index: number) => (
                <div key={index} className="bg-white border border-gray-200 rounded-md p-3 shadow-sm">
                  <div className="flex justify-between items-start">
                    <div>
                      <div className="flex items-center">
                        <span className="font-medium">{speaker.name}</span>
                        <span className={`ml-2 px-2 py-0.5 text-xs rounded-full ${
                          speaker.confidence > 0.7 ? 'bg-green-100 text-green-800' : 
                          speaker.confidence > 0.5 ? 'bg-yellow-100 text-yellow-800' : 
                          'bg-red-100 text-red-800'
                        }`}>
                          {Math.round(speaker.confidence * 100)}% confidence
                        </span>
                      </div>
                      <div className="text-sm text-gray-500 mt-1">
                        {formatTime(speaker.start_time)} - {formatTime(speaker.end_time)} ({Math.round(speaker.duration)} seconds)
                      </div>
                    </div>
                    <button
                      onClick={() => jumpToTimestamp(speaker.start_time)}
                      className="px-2 py-1 text-sm bg-blue-100 text-blue-700 rounded hover:bg-blue-200"
                    >
                      Jump to Timestamp
                    </button>
                  </div>
                </div>
              ))
            ) : (
              <div className="text-gray-500">No speakers identified in this capture.</div>
            )}
          </div>
        </div>
      )}
      
      {/* Transcription Results */}
      {recognitionData?.hasTranscription && transcriptionData && (
        <div className="mb-6">
          <h4 className="text-md font-medium mb-3">Transcription</h4>
          <div className="bg-white border border-gray-200 rounded-md p-4 shadow-sm">
            {transcriptionData.content ? (
              <div className="max-h-80 overflow-y-auto whitespace-pre-wrap text-gray-700">
                {transcriptionData.content}
              </div>
            ) : (
              <div className="text-gray-500">Transcription is available but has no content.</div>
            )}
            {transcriptionData.id && (
              <div className="mt-3 text-right">
                <a 
                  href={`/transcriptions/${transcriptionData.id}`}
                  className="text-blue-600 hover:text-blue-800 text-sm"
                >
                  View Full Transcription
                </a>
              </div>
            )}
          </div>
        </div>
      )}
      
      {/* Process Button (if some data exists but not all) */}
      {(!recognitionData?.hasSpeakerIdentification || !recognitionData?.hasTranscription) && (
        <div className="mt-4">
          <button
            onClick={handleStartProcessing}
            disabled={isProcessing}
            className={`px-4 py-2 rounded-md text-white ${
              isProcessing ? 'bg-blue-400 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700'
            }`}
          >
            {isProcessing ? 'Processing...' : 'Process Recognition'}
          </button>
          <p className="text-sm text-gray-500 mt-2">
            {!recognitionData?.hasSpeakerIdentification && !recognitionData?.hasTranscription
              ? 'Process this capture for speaker identification and transcription.'
              : !recognitionData?.hasSpeakerIdentification
              ? 'Speaker identification is not available. Process to identify speakers.'
              : 'Transcription is not available. Process to generate transcription.'}
          </p>
        </div>
      )}
    </div>
  );
};

export default RecognitionSection;
