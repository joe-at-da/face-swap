import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import Link from 'next/link';
import MainLayout from '../../../components/layout/MainLayout';
import { withAuth, useAuth } from '../../../contexts/AuthContext';
import { UserRole } from '../../../contexts/AuthContext';
import { api } from '../../../utils/api';
import UnifiedRecognitionPanel from '../../../components/recognition/UnifiedRecognitionPanel';
import { toast } from 'react-toastify';

// Types
interface Recognition {
  id: number;
  capture_id: number;
  status: string;
  type: 'facial' | 'voice' | 'combined';
  results: any;
  error_message: string | null;
  created_at: string;
  updated_at: string;
  confidence?: number;
}

interface CaptureSession {
  id: number;
  title: string;
  status: string;
  file_path: string;
  video_path?: string;
  created_at: string;
  recognition_status?: string;
  recognition_progress?: string;
  recognition_results?: string;
  recognition_started_at?: string;
  recognition_completed_at?: string;
}

interface RecognizedFace {
  name: string;
  confidence: number;
  timestamp: number;
  bbox: [number, number, number, number]; // [x, y, width, height]
}

interface RecognizedSpeaker {
  name: string;
  confidence: number;
  start_time: number;
  end_time: number;
  text?: string;
}

const RecognitionPage: React.FC = () => {
  const router = useRouter();
  const { id } = router.query;
  const queryClient = useQueryClient();
  const { token } = useAuth();
  
  const [activeTab, setActiveTab] = useState<string>('details');
  const [recognitionResults, setRecognitionResults] = useState<any>(null);
  const [facialResults, setFacialResults] = useState<RecognizedFace[]>([]);
  const [speakerResults, setSpeakerResults] = useState<RecognizedSpeaker[]>([]);

  // Fetch capture details
  const { data: capture, isLoading: isLoadingCapture } = useQuery({
    queryKey: ['capture', id],
    queryFn: async () => {
      if (!id) return null;
      return await api.get(`/capture/${id}`);
    },
    enabled: !!id,
  });

  // Fetch recognition status
  const { data: recognitionStatus, isLoading: isLoadingRecognition } = useQuery({
    queryKey: ['recognition-status', id],
    queryFn: async () => {
      if (!id) return null;
      return await api.get(`/recognition/recognition-status/${id}`);
    },
    enabled: !!id,
    refetchInterval: 5000, // Refetch every 5 seconds to get updated status
  });

  // Process recognition results when they're available
  useEffect(() => {
    // First check if we have results in the capture object
    if (capture && capture.recognition_results) {
      try {
        const results = typeof capture.recognition_results === 'string' 
          ? JSON.parse(capture.recognition_results) 
          : capture.recognition_results;
        
        console.log('Recognition results:', results);
        setRecognitionResults(results);
        
        // Extract facial recognition results - handle different possible formats
        let faces: RecognizedFace[] = [];
        
        // Format 1: results.facial_recognition.faces
        if (results.facial_recognition && Array.isArray(results.facial_recognition.faces)) {
          faces = results.facial_recognition.faces;
        }
        // Format 2: results.speaker_identification.results.speakers
        else if (results.speaker_identification && results.speaker_identification.results && 
                 Array.isArray(results.speaker_identification.results.speakers)) {
          faces = results.speaker_identification.results.speakers.map((speaker: any) => ({
            name: speaker.name || 'Unknown',
            confidence: speaker.confidence || 0,
            timestamp: speaker.timestamp || 0,
            bbox: speaker.bbox || [0, 0, 0, 0]
          }));
        }
        // Format 3: Direct speaker_identification with speakers array
        else if (results.speaker_identification && Array.isArray(results.speaker_identification.speakers)) {
          faces = results.speaker_identification.speakers.map((speaker: any) => ({
            name: speaker.name || 'Unknown',
            confidence: speaker.confidence || 0,
            timestamp: speaker.timestamp || 0,
            bbox: speaker.bbox || [0, 0, 0, 0]
          }));
        }
        
        setFacialResults(faces);
        
        // Extract speaker identification results
        let speakers: RecognizedSpeaker[] = [];
        
        // Format 1: results.speaker_identification.segments
        if (results.speaker_identification && Array.isArray(results.speaker_identification.segments)) {
          speakers = results.speaker_identification.segments.map((segment: any) => ({
            name: segment.speaker || 'Unknown',
            confidence: segment.confidence || 0,
            start_time: segment.start || 0,
            end_time: segment.end || 0,
            text: segment.text || ''
          }));
        }
        // Format 2: results.speaker_identification.results.segments
        else if (results.speaker_identification && results.speaker_identification.results && 
                 Array.isArray(results.speaker_identification.results.segments)) {
          speakers = results.speaker_identification.results.segments.map((segment: any) => ({
            name: segment.speaker || 'Unknown',
            confidence: segment.confidence || 0,
            start_time: segment.start || 0,
            end_time: segment.end || 0,
            text: segment.text || ''
          }));
        }
        // Format 3: results.segments (direct)
        else if (Array.isArray(results.segments)) {
          speakers = results.segments.map((segment: any) => ({
            name: segment.speaker || 'Unknown',
            confidence: segment.confidence || 0,
            start_time: segment.start || 0,
            end_time: segment.end || 0,
            text: segment.text || ''
          }));
        }
        
        setSpeakerResults(speakers);
      } catch (error) {
        console.error('Error processing recognition results:', error);
      }
    } else if (recognitionStatus?.results) {
      // If we have results in the recognition status
      try {
        const results = typeof recognitionStatus.results === 'string' 
          ? JSON.parse(recognitionStatus.results) 
          : recognitionStatus.results;
        
        setRecognitionResults(results);
        // Process results as above...
      } catch (error) {
        console.error('Error processing recognition status results:', error);
      }
    }
  }, [capture, recognitionStatus]);

  // Format time (convert seconds to MM:SS format)
  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };
  
  // Format date
  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleString();
  };
  
  // Get confidence color class based on confidence value
  const getConfidenceColorClass = (confidence: number): string => {
    if (confidence >= 0.8) return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300';
    if (confidence >= 0.6) return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300';
    return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300';
  };

  return (
    <MainLayout title={`Recognition Results | ${capture?.title || 'Capture'} | Parliament Video Clip Manager`}>
      <div className="container mx-auto p-6">
        <div className="mb-6">
          <Link href={`/capture/${id}`}>
            <span className="text-blue-600 hover:text-blue-800 cursor-pointer">
              &larr; Back to Capture Details
            </span>
          </Link>
        </div>

        {/* Unified Recognition Panel */}
        <div className="mb-8">
          {id ? (
            <UnifiedRecognitionPanel 
              captureId={parseInt(id as string, 10)} 
              onProcessingComplete={() => {
                toast.success('Recognition processing completed');
                queryClient.invalidateQueries({ queryKey: ['capture', id] });
                queryClient.invalidateQueries({ queryKey: ['recognition-status', id] });
              }}
            />
          ) : (
            <div className="bg-gray-800 rounded-lg shadow-lg p-6">
              <h2 className="text-xl font-bold mb-6 text-white">Recognition Results</h2>
              <div className="bg-yellow-900/30 border border-yellow-800 rounded-md p-4">
                <p className="text-yellow-300">Loading capture information...</p>
              </div>
            </div>
          )}
        </div>

        <div className="bg-gray-800 shadow overflow-hidden sm:rounded-lg">
          <div className="px-4 py-5 sm:px-6 bg-gray-900">
            <h3 className="text-lg leading-6 font-medium text-white">
              Detailed Recognition Results
            </h3>
            <p className="mt-1 max-w-2xl text-sm text-gray-400">
              {capture?.title}
            </p>
          </div>

          <div className="border-t border-gray-700 px-4 py-5 sm:p-6">
            {/* Tabs */}
            <div className="border-b border-gray-700 mb-6">
              <nav className="flex -mb-px">
                <button
                  onClick={() => setActiveTab('details')}
                  className={`py-4 px-6 text-center border-b-2 font-medium text-sm ${
                    activeTab === 'details'
                      ? 'border-blue-500 text-blue-500'
                      : 'border-transparent text-gray-400 hover:text-gray-300 hover:border-gray-600'
                  }`}
                >
                  Details
                </button>
                <button
                  onClick={() => setActiveTab('facial')}
                  className={`py-4 px-6 text-center border-b-2 font-medium text-sm ${
                    activeTab === 'facial'
                      ? 'border-blue-500 text-blue-500'
                      : 'border-transparent text-gray-400 hover:text-gray-300 hover:border-gray-600'
                  }`}
                >
                  Facial Recognition
                </button>
                <button
                  onClick={() => setActiveTab('speaker')}
                  className={`py-4 px-6 text-center border-b-2 font-medium text-sm ${
                    activeTab === 'speaker'
                      ? 'border-blue-500 text-blue-500'
                      : 'border-transparent text-gray-400 hover:text-gray-300 hover:border-gray-600'
                  }`}
                >
                  Speaker Identification
                </button>
              </nav>
            </div>
            
            {isLoadingCapture || isLoadingRecognition ? (
              <div className="flex justify-center items-center h-32">
                <div className="text-gray-400">Loading recognition results...</div>
              </div>
            ) : !capture || !recognitionStatus ? (
              <div className="bg-red-900 border-l-4 border-red-500 p-4">
                <div className="flex">
                  <div className="flex-shrink-0">
                    <svg className="h-5 w-5 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                  </div>
                  <div className="ml-3">
                    <p className="text-sm text-red-300">Error loading recognition results. The capture may not exist or recognition has not been performed.</p>
                  </div>
                </div>
              </div>
            ) : (
              <div>
                {/* Details Tab */}
                {activeTab === 'details' && (
                  <div>
                    <h3 className="text-lg font-medium text-white mb-4">Recognition Details</h3>
                    
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      <div className="bg-gray-900 p-4 rounded-lg">
                        <h4 className="text-md font-medium text-white mb-2">Status Information</h4>
                        <dl className="space-y-2">
                          <div className="flex justify-between">
                            <dt className="text-sm text-gray-400">Status</dt>
                            <dd className="text-sm text-gray-300">
                              <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                                recognitionStatus?.status?.status === 'completed' ? 'bg-green-900 text-green-300' : 
                                recognitionStatus?.status?.status === 'processing' ? 'bg-blue-900 text-blue-300' : 
                                recognitionStatus?.status?.status === 'failed' ? 'bg-red-900 text-red-300' : 
                                'bg-gray-700 text-gray-300'
                              }`}>
                                {recognitionStatus?.status?.status || capture?.recognition_status || 'Not Started'}
                              </span>
                            </dd>
                          </div>
                          <div className="flex justify-between">
                            <dt className="text-sm text-gray-400">Started At</dt>
                            <dd className="text-sm text-gray-300">
                              {recognitionStatus?.status?.started_at ? formatDate(recognitionStatus.status.started_at) : 
                               capture?.recognition_started_at ? formatDate(capture.recognition_started_at) : 'N/A'}
                            </dd>
                          </div>
                          <div className="flex justify-between">
                            <dt className="text-sm text-gray-400">Completed At</dt>
                            <dd className="text-sm text-gray-300">
                              {recognitionStatus?.status?.completed_at ? formatDate(recognitionStatus.status.completed_at) : 
                               capture?.recognition_completed_at ? formatDate(capture.recognition_completed_at) : 'N/A'}
                            </dd>
                          </div>
                          <div className="flex justify-between">
                            <dt className="text-sm text-gray-400">Duration</dt>
                            <dd className="text-sm text-gray-300">
                              {recognitionStatus?.status?.started_at && recognitionStatus?.status?.completed_at ? 
                                `${Math.round((new Date(recognitionStatus.status.completed_at).getTime() - new Date(recognitionStatus.status.started_at).getTime()) / 1000)} seconds` : 
                                capture?.recognition_started_at && capture?.recognition_completed_at ?
                                `${Math.round((new Date(capture.recognition_completed_at).getTime() - new Date(capture.recognition_started_at).getTime()) / 1000)} seconds` : 
                                'N/A'}
                            </dd>
                          </div>
                        </dl>
                      </div>
                      
                      <div className="bg-gray-900 p-4 rounded-lg">
                        <h4 className="text-md font-medium text-white mb-2">Recognition Results</h4>
                        <dl className="space-y-2">
                          <div className="flex justify-between">
                            <dt className="text-sm text-gray-400">Speakers Identified</dt>
                            <dd className="text-sm text-gray-300">
                              {recognitionResults?.speaker_identification?.results?.speakers?.length || 
                               recognitionResults?.speakers?.length || 0}
                            </dd>
                          </div>
                          <div className="flex justify-between">
                            <dt className="text-sm text-gray-400">Speaker Segments</dt>
                            <dd className="text-sm text-gray-300">
                              {recognitionResults?.speaker_identification?.results?.segments?.length || 
                               recognitionResults?.segments?.length || 0}
                            </dd>
                          </div>
                          <div className="flex justify-between">
                            <dt className="text-sm text-gray-400">Transcription Available</dt>
                            <dd className="text-sm text-gray-300">
                              {(recognitionResults?.transcription?.transcript || 
                                recognitionResults?.results_summary?.transcript_text) ? 'Yes' : 'No'}
                            </dd>
                          </div>
                          <div className="flex justify-between">
                            <dt className="text-sm text-gray-400">Facial Recognition</dt>
                            <dd className="text-sm text-gray-300">
                              {recognitionResults?.facial_recognition ? 'Available' : 'Not Available'}
                            </dd>
                          </div>
                        </dl>
                      </div>
                    </div>
                  </div>
                )}

                {/* Facial Recognition Tab */}
                {activeTab === 'facial' && (
                  <div>
                    <h3 className="text-lg font-medium text-white mb-4">Facial Recognition Results</h3>
                    
                    {facialResults.length > 0 ? (
                      <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-gray-700">
                          <thead className="bg-gray-900">
                            <tr>
                              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                                Name
                              </th>
                              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                                Confidence
                              </th>
                              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                                Timestamp
                              </th>
                              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                                Bounding Box
                              </th>
                            </tr>
                          </thead>
                          <tbody className="bg-gray-800 divide-y divide-gray-700">
                            {facialResults.map((face, index) => (
                              <tr key={index}>
                                <td className="px-6 py-4 whitespace-nowrap">
                                  <div className="text-sm font-medium text-white">
                                    {face.name}
                                  </div>
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap">
                                  <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${getConfidenceColorClass(face.confidence)}`}>
                                    {Math.round(face.confidence * 100)}%
                                  </span>
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-400">
                                  {formatTime(face.timestamp)}
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-400">
                                  {face.bbox ? `[${face.bbox.map(v => Math.round(v)).join(', ')}]` : 'N/A'}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    ) : (
                      <div className="bg-gray-900 p-6 text-center">
                        <p className="text-gray-400">
                          No facial recognition results available.
                        </p>
                      </div>
                    )}
                  </div>
                )}

                {/* Speaker Identification Tab */}
                {activeTab === 'speaker' && (
                  <div>
                    <h3 className="text-lg font-medium text-white mb-4">Speaker Identification Results</h3>
                    
                    {speakerResults.length > 0 ? (
                      <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-gray-700">
                          <thead className="bg-gray-900">
                            <tr>
                              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                                Speaker
                              </th>
                              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                                Confidence
                              </th>
                              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                                Time Range
                              </th>
                              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                                Text
                              </th>
                            </tr>
                          </thead>
                          <tbody className="bg-gray-800 divide-y divide-gray-700">
                            {speakerResults.map((speaker, index) => (
                              <tr key={index}>
                                <td className="px-6 py-4 whitespace-nowrap">
                                  <div className="text-sm font-medium text-white">
                                    {speaker.name}
                                  </div>
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap">
                                  <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${getConfidenceColorClass(speaker.confidence)}`}>
                                    {Math.round(speaker.confidence * 100)}%
                                  </span>
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-400">
                                  {formatTime(speaker.start_time)} - {formatTime(speaker.end_time)}
                                  <div className="text-xs text-gray-500">
                                    ({Math.round(speaker.end_time - speaker.start_time)} seconds)
                                  </div>
                                </td>
                                <td className="px-6 py-4 text-sm text-gray-400">
                                  {speaker.text || <span className="text-gray-500 italic">No text available</span>}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    ) : (
                      <div className="bg-gray-900 p-6 text-center">
                        <p className="text-gray-400">
                          No speaker identification results available.
                        </p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </MainLayout>
  );
};

export default withAuth(RecognitionPage, [UserRole.ADMIN, UserRole.MP, UserRole.STAFF]);
