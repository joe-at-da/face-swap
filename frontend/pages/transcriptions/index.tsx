import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import MainLayout from '../../components/layout/MainLayout';
import { useAuth, withAuth, UserRole } from '../../contexts/AuthContext';
import { api } from '../../utils/api';
import { Card, Button, Badge, Table, TableHead, TableBody, TableRow, TableHeaderCell, TableCell, Input, Select } from '../../components/ui';

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
  
  // Get status badge variant
  const getStatusBadgeVariant = (status: string): 'success' | 'primary' | 'danger' | 'warning' | 'secondary' => {
    switch (status.toLowerCase()) {
      case 'completed':
        return 'success';
      case 'processing':
        return 'warning';
      case 'failed':
        return 'danger';
      case 'pending':
        return 'primary';
      default:
        return 'secondary';
    }
  };
  
  // Get type badge variant
  const getTypeBadgeVariant = (type: string, subtype?: string): 'primary' | 'success' | 'info' | 'warning' | 'secondary' => {
    if (type === 'transcription') {
      return 'info';
    }
    
    if (type === 'recognition') {
      switch (subtype) {
        case 'facial':
          return 'primary';
        case 'voice':
          return 'success';
        case 'combined':
          return 'warning';
        default:
          return 'secondary';
      }
    }
    
    return 'secondary';
  };

  return (
    <MainLayout title="Transcriptions | Parliament Video Clip Manager">
      <div className="page-container">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-6 space-y-4 md:space-y-0">
          <h1 className="text-3xl font-bold text-white">Transcriptions & Recognitions</h1>
          
          <div className="flex space-x-2">
            <Link href="/recognition">
              <Button variant="primary">Start Recognition</Button>
            </Link>
          </div>
        </div>
        {isLoadingTranscriptions || isLoadingRecognitions || isLoadingCaptures ? (
          <Card>
            <div className="flex justify-center items-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
            </div>
          </Card>
        ) : combinedResults && combinedResults.length > 0 ? (
          <Card>
            <div className="flex flex-col md:flex-row md:items-end space-y-4 md:space-y-0 md:space-x-4 mb-6">
              <div className="w-full md:w-64">
                <Input
                  type="text"
                  id="search"
                  label="Search"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  placeholder="Search by title..."
                  fullWidth
                />
              </div>
              
              <div className="w-full md:w-48">
                <Select
                  id="status"
                  label="Status"
                  value={selectedStatus}
                  onChange={(e) => setSelectedStatus(e.target.value)}
                  options={[
                    { value: 'all', label: 'All Statuses' },
                    { value: 'completed', label: 'Completed' },
                    { value: 'processing', label: 'Processing' },
                    { value: 'failed', label: 'Failed' },
                    { value: 'pending', label: 'Pending' }
                  ]}
                  fullWidth
                />
              </div>
            </div>
            
            {/* Transcription List */}
            <Table>
              <TableHead>
                <TableRow>
                  <TableHeaderCell>Capture</TableHeaderCell>
                  <TableHeaderCell>Type</TableHeaderCell>
                  <TableHeaderCell>Status</TableHeaderCell>
                  <TableHeaderCell>Created</TableHeaderCell>
                  <TableHeaderCell>Actions</TableHeaderCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {filteredResults.map((result) => {
                  const captureTitle = captures?.find((c: CaptureSession) => c.id === result.capture_id)?.title || `Capture #${result.capture_id}`;
                  
                  return (
                    <TableRow key={`${result.type}-${result.originalId}`}>
                      <TableCell>
                        <div className="text-sm font-medium text-white">{captureTitle}</div>
                        <div className="text-sm text-gray-400">ID: {result.capture_id}</div>
                      </TableCell>
                      <TableCell>
                        <Badge variant={getTypeBadgeVariant(result.type, result.subtype)}>
                          {result.type === 'transcription' ? 'Transcription' : 
                           result.subtype === 'facial' ? 'Facial Recognition' : 
                           result.subtype === 'voice' ? 'Voice Recognition' : 
                           'Combined Recognition'}
                        </Badge>
                        {result.type === 'transcription' && (
                          <div className="text-xs text-gray-400 mt-1">
                            Language: {result.language || 'Unknown'}
                          </div>
                        )}
                        {result.type === 'recognition' && result.confidence !== undefined && (
                          <div className="text-xs text-gray-400 mt-1">
                            {Math.round(result.confidence * 100)}% confidence
                          </div>
                        )}
                      </TableCell>
                      <TableCell>
                        <Badge variant={getStatusBadgeVariant(result.status)}>
                          {result.status}
                        </Badge>
                        {result.error_message && (
                          <div className="text-xs text-red-400 mt-1 truncate max-w-xs" title={result.error_message}>
                            {result.error_message}
                          </div>
                        )}
                      </TableCell>
                      <TableCell>
                        <div className="text-sm text-gray-300">{formatDate(result.created_at)}</div>
                      </TableCell>
                      <TableCell>
                        {result.type === 'transcription' ? (
                          <Link href={`/capture/${result.capture_id}/transcription?id=${result.originalId}`}>
                            <Button size="sm" variant="primary">View</Button>
                          </Link>
                        ) : (
                          <Link href={`/capture/${result.capture_id}/recognition?id=${result.originalId}`}>
                            <Button size="sm" variant="primary">View</Button>
                          </Link>
                        )}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
            
            {filteredResults.length === 0 && (
              <div className="p-6 text-center">
                <p className="text-gray-400">
                  No transcriptions match your filters. Try adjusting your search criteria.
                </p>
              </div>
            )}
          </Card>
        ) : (
          <Card>
            <div className="text-center py-12">
              <svg
                className="mx-auto h-16 w-16 text-gray-500"
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
              <h3 className="mt-4 text-lg font-medium text-white">
                No Transcriptions Found
              </h3>
              <p className="mt-2 text-sm text-gray-400">
                Start by creating a transcription for one of your Parliament TV captures.
              </p>
              <div className="mt-6">
                <Link href="/capture">
                  <Button variant="primary">Go to Captures</Button>
                </Link>
              </div>
            </div>
          </Card>
        )}
      </div>
    </MainLayout>
  );
};

export default TranscriptionsPage;
