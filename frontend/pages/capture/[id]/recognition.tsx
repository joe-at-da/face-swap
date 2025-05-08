import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Link from 'next/link';
import MainLayout from '../../../components/layout/MainLayout';
import { withAuth, useAuth } from '../../../contexts/AuthContext';
import { UserRole } from '../../../contexts/AuthContext';
import { api } from '../../../utils/api';

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
  const { id, recognitionId } = router.query;
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
        
        setRecognitionResults(results);
        
        // Extract facial recognition results
        if (results.facial_recognition && Array.isArray(results.facial_recognition.faces)) {
          setFacialResults(results.facial_recognition.faces);
        }
        
        // Extract speaker recognition results
        if (results.speaker_identification && Array.isArray(results.speaker_identification.segments)) {
          setSpeakerResults(results.speaker_identification.segments);
        }
      } catch (error) {
        console.error('Error parsing recognition results:', error);
      }
    } 
    // If recognition status indicates there are results but we don't have them in the capture object,
    // we need to fetch them directly
    else if (recognitionStatus?.status?.has_results && recognitionStatus?.status?.status === 'completed') {
      // Fetch recognition results directly
      const fetchRecognitionResults = async () => {
        try {
          const response = await api.get(`/recognition/results/${id}`);
          if (response && response.results) {
            setRecognitionResults(response.results);
            
            // Extract facial recognition results
            if (response.results.facial_recognition && Array.isArray(response.results.facial_recognition.faces)) {
              setFacialResults(response.results.facial_recognition.faces);
            }
            
            // Extract speaker recognition results
            if (response.results.speaker_identification && Array.isArray(response.results.speaker_identification.segments)) {
              setSpeakerResults(response.results.speaker_identification.segments);
            }
          }
        } catch (error) {
          console.error('Error fetching recognition results:', error);
        }
      };
      
      fetchRecognitionResults();
    }
  }, [capture, recognitionStatus, id]);

  // Format time (convert seconds to MM:SS format)
  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  // Format date
  const formatDate = (dateString: string): string => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleString();
  };

  // Get confidence color class based on confidence value
  const getConfidenceColorClass = (confidence: number): string => {
    if (confidence >= 0.8) return 'bg-green-100 text-green-800';
    if (confidence >= 0.6) return 'bg-yellow-100 text-yellow-800';
    return 'bg-red-100 text-red-800';
  };

  return (
    <MainLayout title={`Recognition Results | ${capture?.title || `Capture ${id}`}`}>
      <div className="container mx-auto px-4 py-8">
        <div className="mb-6">
          <div className="flex justify-between items-center">
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
              Recognition Results: {capture?.title || `Capture ${id}`}
            </h1>
            <Link href={`/capture/${id}`} className="text-primary hover:text-primary-dark">
              Back to Capture
            </Link>
          </div>
          <p className="text-gray-600 dark:text-gray-400 mt-1">
            View facial and speaker recognition results
          </p>
        </div>

        {isLoadingCapture || isLoadingRecognition ? (
          <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
            <div className="animate-pulse flex space-x-4">
              <div className="flex-1 space-y-4 py-1">
                <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4"></div>
                <div className="space-y-2">
                  <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded"></div>
                  <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-5/6"></div>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="bg-white dark:bg-gray-800 shadow rounded-lg overflow-hidden">
            {/* Status Bar */}
            <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900">
              <div className="flex flex-wrap items-center justify-between">
                <div className="flex items-center">
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300 mr-2">Status:</span>
                  <span className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full 
                    ${recognitionStatus?.status?.status === 'completed' ? 'bg-green-100 text-green-800' : 
                      recognitionStatus?.status?.status === 'processing' ? 'bg-blue-100 text-blue-800' : 
                      recognitionStatus?.status?.status === 'error' ? 'bg-red-100 text-red-800' : 
                      'bg-gray-100 text-gray-800'}`}>
                    {recognitionStatus?.status?.status || capture?.recognition_status || 'Not Started'}
                  </span>
                </div>
                <div className="text-sm text-gray-600 dark:text-gray-400">
                  {recognitionStatus?.status?.completed_at ? (
                    <span>Completed: {formatDate(recognitionStatus.status.completed_at)}</span>
                  ) : recognitionStatus?.status?.started_at ? (
                    <span>Started: {formatDate(recognitionStatus.status.started_at)}</span>
                  ) : capture?.recognition_completed_at ? (
                    <span>Completed: {formatDate(capture.recognition_completed_at)}</span>
                  ) : capture?.recognition_started_at ? (
                    <span>Started: {formatDate(capture.recognition_started_at)}</span>
                  ) : (
                    <span>Not processed yet</span>
                  )}
                </div>
              </div>
            </div>

            {/* Tabs */}
            <div className="border-b border-gray-200 dark:border-gray-700">
              <nav className="flex -mb-px">
                <button
                  onClick={() => setActiveTab('details')}
                  className={`py-4 px-6 text-center border-b-2 font-medium text-sm ${
                    activeTab === 'details'
                      ? 'border-primary text-primary'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  Details
                </button>
                <button
                  onClick={() => setActiveTab('facial')}
                  className={`py-4 px-6 text-center border-b-2 font-medium text-sm ${
                    activeTab === 'facial'
                      ? 'border-primary text-primary'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  Facial Recognition
                </button>
                <button
                  onClick={() => setActiveTab('speaker')}
                  className={`py-4 px-6 text-center border-b-2 font-medium text-sm ${
                    activeTab === 'speaker'
                      ? 'border-primary text-primary'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  Speaker Identification
                </button>
              </nav>
            </div>

            {/* Tab Content */}
            <div className="p-6">
              {/* Details Tab */}
              {activeTab === 'details' && (
                <div>
                  <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Recognition Details</h3>
                  
                  {/* Recognition Progress */}
                  {capture?.recognition_progress && (
                    <div className="mb-6">
                      <h4 className="text-md font-medium mb-2">Progress</h4>
                      <div className="bg-gray-50 dark:bg-gray-900 rounded-md p-4">
                        {(() => {
                          try {
                            const progress = JSON.parse(capture.recognition_progress);
                            return (
                              <div>
                                <div className="mb-2">
                                  <span className="font-medium">Status:</span> {progress.status}
                                </div>
                                {progress.steps && progress.steps.length > 0 && (
                                  <div>
                                    <div className="font-medium mb-1">Steps:</div>
                                    <ul className="list-disc pl-5 space-y-1">
                                      {progress.steps.map((step: any, index: number) => (
                                        <li key={index} className="text-sm">
                                          <span className="font-medium">{step.name}:</span> {step.status}
                                          {step.timestamp && <span className="text-gray-500 ml-2">({new Date(step.timestamp).toLocaleTimeString()})</span>}
                                        </li>
                                      ))}
                                    </ul>
                                  </div>
                                )}
                                {progress.error && (
                                  <div className="mt-2 text-red-600">
                                    <span className="font-medium">Error:</span> {progress.error}
                                  </div>
                                )}
                              </div>
                            );
                          } catch (e) {
                            return <div className="text-gray-500">Progress information not available</div>;
                          }
                        })()}
                      </div>
                    </div>
                  )}

                  {/* Summary of Results */}
                  {recognitionResults && (
                    <div>
                      <h4 className="text-md font-medium mb-2">Summary</h4>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="bg-gray-50 dark:bg-gray-900 rounded-md p-4">
                          <h5 className="font-medium mb-2">Facial Recognition</h5>
                          {facialResults.length > 0 ? (
                            <div>
                              <p className="text-sm">{facialResults.length} faces detected</p>
                              <div className="mt-2">
                                <span className="text-sm font-medium">Recognized Individuals:</span>
                                <div className="flex flex-wrap gap-2 mt-1">
                                  {Array.from(new Set(facialResults.map(face => face.name))).map((name, index) => (
                                    <span key={index} className="px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded-full">
                                      {name}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            </div>
                          ) : (
                            <p className="text-sm text-gray-500">No facial recognition results available</p>
                          )}
                        </div>
                        
                        <div className="bg-gray-50 dark:bg-gray-900 rounded-md p-4">
                          <h5 className="font-medium mb-2">Speaker Identification</h5>
                          {speakerResults.length > 0 ? (
                            <div>
                              <p className="text-sm">{speakerResults.length} speaker segments identified</p>
                              <div className="mt-2">
                                <span className="text-sm font-medium">Recognized Speakers:</span>
                                <div className="flex flex-wrap gap-2 mt-1">
                                  {Array.from(new Set(speakerResults.map(speaker => speaker.name))).map((name, index) => (
                                    <span key={index} className="px-2 py-1 text-xs bg-purple-100 text-purple-800 rounded-full">
                                      {name}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            </div>
                          ) : (
                            <p className="text-sm text-gray-500">No speaker identification results available</p>
                          )}
                        </div>
                      </div>
                    </div>
                  )}

                  {/* No Results Message */}
                  {!recognitionResults && (
                    <div className={`border-l-4 p-4 ${recognitionStatus?.status?.status === 'error' || capture?.recognition_status === 'error' ? 'bg-red-50 border-red-400' : recognitionStatus?.status?.status === 'completed' ? 'bg-blue-50 border-blue-400' : 'bg-yellow-50 border-yellow-400'}`}>
                      <div className="flex">
                        <div className="ml-3">
                          <p className={`text-sm ${recognitionStatus?.status?.status === 'error' || capture?.recognition_status === 'error' ? 'text-red-700' : recognitionStatus?.status?.status === 'completed' ? 'text-blue-700' : 'text-yellow-700'}`}>
                            {recognitionStatus?.status?.status === 'completed' || capture?.recognition_status === 'completed' ?
                              'Recognition completed successfully, but no faces or speakers were detected in the media.' :
                              recognitionStatus?.status?.status === 'error' || capture?.recognition_status === 'error' ?
                                'An error occurred during the recognition process.' :
                                'No recognition results available. Try starting the recognition process.'}
                          </p>
                          {(recognitionStatus?.status?.status === 'error' || capture?.recognition_status === 'error') && (recognitionStatus?.status?.progress || capture?.recognition_progress) && (
                            <p className="text-sm text-red-600 mt-2">
                              {(() => {
                                try {
                                  const progress = recognitionStatus?.status?.progress || 
                                    (capture?.recognition_progress ? JSON.parse(capture.recognition_progress) : {});
                                  return progress.error || 'Unknown error occurred during recognition';
                                } catch (e) {
                                  return 'Error parsing recognition progress';
                                }
                              })()}
                            </p>
                          )}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Facial Recognition Tab */}
              {activeTab === 'facial' && (
                <div>
                  <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Facial Recognition Results</h3>
                  
                  {facialResults.length > 0 ? (
                    <div>
                      <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                          <thead className="bg-gray-50 dark:bg-gray-900">
                            <tr>
                              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                                Person
                              </th>
                              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                                Confidence
                              </th>
                              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                                Timestamp
                              </th>
                              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                                Position
                              </th>
                            </tr>
                          </thead>
                          <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                            {facialResults.map((face, index) => (
                              <tr key={index}>
                                <td className="px-6 py-4 whitespace-nowrap">
                                  <div className="text-sm font-medium text-gray-900 dark:text-white">
                                    {face.name}
                                  </div>
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap">
                                  <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${getConfidenceColorClass(face.confidence)}`}>
                                    {Math.round(face.confidence * 100)}%
                                  </span>
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                                  {formatTime(face.timestamp)}
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                                  {`(${Math.round(face.bbox[0])}, ${Math.round(face.bbox[1])}) - ${Math.round(face.bbox[2])}x${Math.round(face.bbox[3])}`}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  ) : (
                    <div className="bg-gray-50 dark:bg-gray-900 p-6 text-center">
                      <p className="text-gray-500 dark:text-gray-400">
                        No facial recognition results available.
                      </p>
                    </div>
                  )}
                </div>
              )}

              {/* Speaker Identification Tab */}
              {activeTab === 'speaker' && (
                <div>
                  <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Speaker Identification Results</h3>
                  
                  {speakerResults.length > 0 ? (
                    <div>
                      <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                          <thead className="bg-gray-50 dark:bg-gray-900">
                            <tr>
                              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                                Speaker
                              </th>
                              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                                Confidence
                              </th>
                              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                                Time Range
                              </th>
                              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                                Text
                              </th>
                            </tr>
                          </thead>
                          <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                            {speakerResults.map((speaker, index) => (
                              <tr key={index}>
                                <td className="px-6 py-4 whitespace-nowrap">
                                  <div className="text-sm font-medium text-gray-900 dark:text-white">
                                    {speaker.name}
                                  </div>
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap">
                                  <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${getConfidenceColorClass(speaker.confidence)}`}>
                                    {Math.round(speaker.confidence * 100)}%
                                  </span>
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                                  {formatTime(speaker.start_time)} - {formatTime(speaker.end_time)}
                                  <div className="text-xs text-gray-400">
                                    ({Math.round(speaker.end_time - speaker.start_time)} seconds)
                                  </div>
                                </td>
                                <td className="px-6 py-4 text-sm text-gray-500 dark:text-gray-400">
                                  {speaker.text || <span className="text-gray-400 italic">No text available</span>}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  ) : (
                    <div className="bg-gray-50 dark:bg-gray-900 p-6 text-center">
                      <p className="text-gray-500 dark:text-gray-400">
                        No speaker identification results available.
                      </p>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </MainLayout>
  );
};

export default withAuth(RecognitionPage, [UserRole.ADMIN, UserRole.MP, UserRole.STAFF]);
