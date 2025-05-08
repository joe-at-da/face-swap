import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import MainLayout from '../../components/layout/MainLayout';
import { useAuth, withAuth, UserRole } from '../../contexts/AuthContext';
import { api } from '../../utils/api';

// Types
interface Transcription {
  id: number;
  capture_id: number;
  status: string;
  language: string;
  text: string;
  segments: any[];
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

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

interface CombinedResult {
  id: number;
  capture_id: number;
  status: string;
  type: 'transcription' | 'recognition';
  subtype?: 'facial' | 'voice' | 'combined';
  language?: string;
  text?: string;
  segments?: any[];
  results?: any;
  error_message: string | null;
  created_at: string;
  updated_at: string;
  confidence?: number;
  originalId: number; // Original ID from the source object
}

interface CaptureSession {
  id: number;
  title: string;
  status: string;
  file_path: string;
  created_at: string;
  metadata: any;
}

const TranscriptionsPage: React.FC = () => {
  const router = useRouter();
  const { user } = useAuth();
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedStatus, setSelectedStatus] = useState('all');
  
  // Fetch all parliament TV captures
  const { data: captures, isLoading: isLoadingCaptures } = useQuery({
    queryKey: ['parliament-tv-captures'],
    queryFn: async () => {
      const response = await api.get('/parliament-tv/all-captures');
      return response.captures || [];
    },
  });
  
  // Fetch all transcriptions
  const { data: allTranscriptions, isLoading: isLoadingTranscriptions } = useQuery({
    queryKey: ['transcriptions'],
    queryFn: async () => {
      const response = await api.get('/transcription/list/parliament-tv');
      return response.transcriptions || [];
    },
  });
  
  // Fetch all recognition results
  const { data: allRecognitions, isLoading: isLoadingRecognitions } = useQuery({
    queryKey: ['recognitions'],
    queryFn: async () => {
      const response = await api.get('/recognition/list/parliament-tv');
      return response.recognitions || [];
    },
  });
  
  // Combine transcriptions and recognitions into a single list
  const combinedResults = React.useMemo(() => {
    const combined: CombinedResult[] = [];
    
    // Add transcriptions
    if (allTranscriptions) {
      allTranscriptions.forEach((transcription: Transcription) => {
        combined.push({
          id: combined.length + 1, // Generate a unique ID for the combined list
          originalId: transcription.id,
          capture_id: transcription.capture_id,
          status: transcription.status,
          type: 'transcription',
          language: transcription.language,
          text: transcription.text,
          segments: transcription.segments,
          error_message: transcription.error_message,
          created_at: transcription.created_at,
          updated_at: transcription.updated_at
        });
      });
    }
    
    // Add recognitions
    if (allRecognitions) {
      allRecognitions.forEach((recognition: Recognition) => {
        combined.push({
          id: combined.length + 1, // Generate a unique ID for the combined list
          originalId: recognition.id,
          capture_id: recognition.capture_id,
          status: recognition.status,
          type: 'recognition',
          subtype: recognition.type,
          results: recognition.results,
          error_message: recognition.error_message,
          created_at: recognition.created_at,
          updated_at: recognition.updated_at,
          confidence: recognition.confidence
        });
      });
    }
    
    return combined;
  }, [allTranscriptions, allRecognitions]);
  
  // Filter combined results based on search term and status
  const filteredResults = React.useMemo(() => {
    if (!combinedResults.length) return [];
    
    return combinedResults.filter((result: CombinedResult) => {
      // Find the associated capture
      const capture = captures?.find((c: CaptureSession) => c.id === result.capture_id);
      const captureTitle = capture?.title || `Capture ${result.capture_id}`;
      
      // Filter by search term
      const matchesSearch = searchTerm === '' || 
        captureTitle.toLowerCase().includes(searchTerm.toLowerCase()) ||
        (result.language && result.language.toLowerCase().includes(searchTerm.toLowerCase())) ||
        (result.type && result.type.toLowerCase().includes(searchTerm.toLowerCase())) ||
        (result.subtype && result.subtype.toLowerCase().includes(searchTerm.toLowerCase()));
      
      // Filter by status
      const matchesStatus = selectedStatus === 'all' || result.status === selectedStatus;
      
      return matchesSearch && matchesStatus;
    });
  }, [combinedResults, captures, searchTerm, selectedStatus]);
  
  // Get status counts for filtering
  const statusCounts = React.useMemo(() => {
    if (!combinedResults.length) return { all: 0, completed: 0, processing: 0, error: 0, failed: 0 };
    
    return combinedResults.reduce((counts: any, result: CombinedResult) => {
      counts.all += 1;
      // Normalize status names for consistency
      const normalizedStatus = result.status === 'ready' || result.status === 'completed' ? 'completed' : 
                              result.status === 'error' ? 'failed' : result.status;
      counts[normalizedStatus] = (counts[normalizedStatus] || 0) + 1;
      return counts;
    }, { all: 0, completed: 0, processing: 0, error: 0, failed: 0 });
  }, [combinedResults]);
  
  // Format date for display
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString();
  };
  
  // Get status badge color
  const getStatusBadgeColor = (status: string) => {
    switch (status) {
      case 'ready':
      case 'completed':
        return 'bg-green-100 text-green-800';
      case 'processing':
        return 'bg-blue-100 text-blue-800';
      case 'failed':
      case 'error':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };
  
  // Get type badge color
  const getTypeBadgeColor = (type: string, subtype?: string) => {
    if (type === 'transcription') {
      return 'bg-purple-100 text-purple-800';
    } else if (type === 'recognition') {
      switch (subtype) {
        case 'facial':
          return 'bg-indigo-100 text-indigo-800';
        case 'voice':
          return 'bg-pink-100 text-pink-800';
        case 'combined':
          return 'bg-teal-100 text-teal-800';
        default:
          return 'bg-gray-100 text-gray-800';
      }
    }
    return 'bg-gray-100 text-gray-800';
  };

  return (
    <MainLayout title="Transcriptions | Parliament Video Clip Manager">
      <div className="container mx-auto px-4 py-8">
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Transcriptions</h1>
          <Link href="/capture" className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-primary hover:bg-primary-dark focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary">
            View Captures
          </Link>
        </div>
        
        {isLoadingCaptures || isLoadingTranscriptions ? (
          <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
            <div className="animate-pulse flex space-x-4">
              <div className="flex-1 space-y-4 py-1">
                <div className="h-4 bg-gray-200 rounded w-3/4"></div>
                <div className="space-y-2">
                  <div className="h-4 bg-gray-200 rounded"></div>
                  <div className="h-4 bg-gray-200 rounded w-5/6"></div>
                </div>
              </div>
            </div>
          </div>
        ) : !isLoadingTranscriptions && !isLoadingRecognitions && combinedResults.length > 0 ? (
          <div className="bg-white dark:bg-gray-800 shadow rounded-lg overflow-hidden">
            {/* Filters */}
            <div className="p-4 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900">
              <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                <div className="flex-1">
                  <input
                    type="text"
                    placeholder="Search transcriptions..."
                    className="w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                  />
                </div>
                <div className="flex space-x-2">
                  <button
                    className={`px-3 py-1 rounded-md ${selectedStatus === 'all' ? 'bg-primary text-white' : 'bg-gray-100 text-gray-800'}`}
                    onClick={() => setSelectedStatus('all')}
                  >
                    All ({statusCounts.all})
                  </button>
                  <button
                    className={`px-3 py-1 rounded-md ${selectedStatus === 'ready' ? 'bg-primary text-white' : 'bg-green-100 text-green-800'}`}
                    onClick={() => setSelectedStatus('ready')}
                  >
                    Ready ({statusCounts.ready})
                  </button>
                  <button
                    className={`px-3 py-1 rounded-md ${selectedStatus === 'processing' ? 'bg-primary text-white' : 'bg-blue-100 text-blue-800'}`}
                    onClick={() => setSelectedStatus('processing')}
                  >
                    Processing ({statusCounts.processing})
                  </button>
                  <button
                    className={`px-3 py-1 rounded-md ${selectedStatus === 'failed' ? 'bg-primary text-white' : 'bg-red-100 text-red-800'}`}
                    onClick={() => setSelectedStatus('failed')}
                  >
                    Failed ({statusCounts.failed})
                  </button>
                </div>
              </div>
            </div>
            
            {/* Transcription List */}
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                <thead className="bg-gray-50 dark:bg-gray-800">
                  <tr>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Capture
                    </th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Type
                    </th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Details
                    </th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Status
                    </th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Created
                    </th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200 dark:bg-gray-900 dark:divide-gray-700">
                  {filteredResults.map((result: CombinedResult) => {
                    // Find the associated capture
                    const capture = captures?.find((c: CaptureSession) => c.id === result.capture_id);
                    const captureTitle = capture?.title || `Capture ${result.capture_id}`;
                    
                    return (
                      <tr key={result.id}>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm font-medium text-gray-900 dark:text-white">
                            {captureTitle}
                          </div>
                          <div className="text-sm text-gray-500 dark:text-gray-400">
                            ID: {result.capture_id}
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${getTypeBadgeColor(result.type, result.subtype)}`}>
                            {result.type.charAt(0).toUpperCase() + result.type.slice(1)}
                            {result.subtype && ` (${result.subtype})`}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          {result.type === 'transcription' && (
                            <div className="text-sm text-gray-900 dark:text-white">
                              {result.language?.toUpperCase()}
                              {result.segments && (
                                <div className="text-xs text-gray-500 mt-1">
                                  {result.segments.length} segments
                                </div>
                              )}
                            </div>
                          )}
                          {result.type === 'recognition' && (
                            <div className="text-sm text-gray-900 dark:text-white">
                              {result.subtype === 'facial' ? 'Face Recognition' : 
                               result.subtype === 'voice' ? 'Voice Recognition' : 
                               'Combined Recognition'}
                              {result.confidence !== undefined && (
                                <div className="text-xs text-gray-500 mt-1">
                                  {Math.round(result.confidence * 100)}% confidence
                                </div>
                              )}
                            </div>
                          )}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${getStatusBadgeColor(result.status)}`}>
                            {result.status}
                          </span>
                          {result.error_message && (
                            <div className="text-xs text-red-600 mt-1 truncate max-w-xs" title={result.error_message}>
                              {result.error_message}
                            </div>
                          )}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                          {formatDate(result.created_at)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                          {result.type === 'transcription' ? (
                            <Link href={`/capture/${result.capture_id}/transcription?id=${result.originalId}`} className="text-primary hover:text-primary-dark mr-3">
                              View
                            </Link>
                          ) : (
                            <Link href={`/capture/${result.capture_id}/recognition?id=${result.originalId}`} className="text-primary hover:text-primary-dark mr-3">
                              View
                            </Link>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            
            {filteredResults.length === 0 && (
              <div className="p-6 text-center">
                <p className="text-gray-500 dark:text-gray-400">
                  No transcriptions match your filters. Try adjusting your search criteria.
                </p>
              </div>
            )}
          </div>
        ) : (
          <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
            <div className="text-center py-12">
              <svg
                className="mx-auto h-16 w-16 text-gray-400 dark:text-gray-500"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                xmlns="http://www.w3.org/2000/svg"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                ></path>
              </svg>
              <h3 className="mt-4 text-lg font-medium text-gray-900 dark:text-white">
                No Transcriptions Found
              </h3>
              <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
                Start by creating a transcription for one of your Parliament TV captures.
              </p>
              <div className="mt-6">
                <Link href="/capture" className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-primary hover:bg-primary-dark focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary">
                  Go to Captures
                </Link>
              </div>
            </div>
          </div>
        )}
      </div>
    </MainLayout>
  );
};

export default TranscriptionsPage;
