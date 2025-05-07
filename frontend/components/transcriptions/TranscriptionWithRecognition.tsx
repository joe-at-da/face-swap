import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { api } from '../../utils/api';

interface Speaker {
  name: string;
  confidence: number;
  start_time: number;
  end_time: number;
  duration: number;
}

interface TranscriptionWithRecognitionProps {
  transcriptionId: number;
  captureId: number;
}

const TranscriptionWithRecognition: React.FC<TranscriptionWithRecognitionProps> = ({ 
  transcriptionId, 
  captureId 
}) => {
  const [activeTab, setActiveTab] = useState<'transcription' | 'recognition'>('transcription');
  
  // Fetch transcription data
  const { data: transcription, isLoading: isLoadingTranscription, isError: isErrorTranscription } = useQuery({
    queryKey: ['transcription', transcriptionId],
    queryFn: async () => {
      return await api.get(`/transcription/${transcriptionId}`);
    },
    enabled: !!transcriptionId
  });
  
  // Fetch capture data to get recognition results
  const { data: capture, isLoading: isLoadingCapture, isError: isErrorCapture } = useQuery({
    queryKey: ['captureSession', captureId],
    queryFn: async () => {
      return await api.get(`/capture/${captureId}`);
    },
    enabled: !!captureId
  });
  
  const isLoading = isLoadingTranscription || isLoadingCapture;
  const isError = isErrorTranscription || isErrorCapture;
  
  const formatTime = (seconds: number): string => {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.floor(seconds % 60);
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
  };
  
  if (isLoading) {
    return (
      <div className="bg-white shadow rounded-lg p-6">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-1/4 mb-6"></div>
          <div className="h-3 bg-gray-200 rounded w-full mb-3"></div>
          <div className="h-3 bg-gray-200 rounded w-full mb-3"></div>
          <div className="h-3 bg-gray-200 rounded w-3/4 mb-3"></div>
        </div>
      </div>
    );
  }
  
  if (isError) {
    return (
      <div className="bg-white shadow rounded-lg p-6">
        <div className="bg-red-50 border-l-4 border-red-500 p-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
            <div className="ml-3">
              <p className="text-sm text-red-700">Error loading transcription data.</p>
            </div>
          </div>
        </div>
      </div>
    );
  }
  
  const hasSpeakerIdentification = capture?.speaker_identification_results && 
    typeof capture.speaker_identification_results === 'object' && 
    capture.speaker_identification_results.speakers && 
    capture.speaker_identification_results.speakers.length > 0;
  
  return (
    <div className="bg-white shadow rounded-lg overflow-hidden">
      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="flex -mb-px">
          <button
            onClick={() => setActiveTab('transcription')}
            className={`py-4 px-6 text-center border-b-2 font-medium text-sm ${
              activeTab === 'transcription'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Transcription
          </button>
          <button
            onClick={() => setActiveTab('recognition')}
            className={`py-4 px-6 text-center border-b-2 font-medium text-sm ${
              activeTab === 'recognition'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Speaker Recognition
          </button>
        </nav>
      </div>
      
      {/* Content */}
      <div className="p-6">
        {activeTab === 'transcription' && (
          <div>
            <h3 className="text-lg font-semibold mb-4">Transcription</h3>
            {transcription?.content ? (
              <div className="whitespace-pre-wrap text-gray-700 max-h-96 overflow-y-auto">
                {transcription.content}
              </div>
            ) : (
              <div className="text-gray-500">No transcription content available.</div>
            )}
            
            <div className="mt-6 flex justify-between items-center">
              <div className="text-sm text-gray-500">
                Source: {transcription?.source || 'Unknown'} | 
                Status: <span className={`${
                  transcription?.status === 'completed' ? 'text-green-600' : 'text-yellow-600'
                }`}>{transcription?.status || 'Unknown'}</span>
              </div>
              
              <div className="flex space-x-2">
                <button className="px-3 py-1 bg-blue-100 text-blue-700 rounded hover:bg-blue-200 text-sm">
                  Export as TXT
                </button>
                <button className="px-3 py-1 bg-blue-100 text-blue-700 rounded hover:bg-blue-200 text-sm">
                  Export as SRT
                </button>
              </div>
            </div>
          </div>
        )}
        
        {activeTab === 'recognition' && (
          <div>
            <h3 className="text-lg font-semibold mb-4">Speaker Recognition</h3>
            
            {hasSpeakerIdentification ? (
              <div className="space-y-3 max-h-96 overflow-y-auto">
                {capture.speaker_identification_results.speakers.map((speaker: Speaker, index: number) => (
                  <div key={index} className="bg-gray-50 border border-gray-200 rounded-md p-3">
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
                      <Link href={`/capture/${captureId}?t=${Math.floor(speaker.start_time)}`}>
                        <span className="px-2 py-1 text-sm bg-blue-100 text-blue-700 rounded hover:bg-blue-200 cursor-pointer">
                          View in Video
                        </span>
                      </Link>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4">
                <div className="flex">
                  <div className="flex-shrink-0">
                    <svg className="h-5 w-5 text-yellow-400" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                    </svg>
                  </div>
                  <div className="ml-3">
                    <p className="text-sm text-yellow-700">
                      No speaker recognition data available for this capture.
                    </p>
                    <p className="text-sm text-yellow-700 mt-2">
                      <Link href={`/capture/${captureId}`}>
                        <span className="font-medium underline cursor-pointer">
                          Go to capture details
                        </span>
                      </Link>
                      {' '}to process speaker recognition.
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default TranscriptionWithRecognition;
