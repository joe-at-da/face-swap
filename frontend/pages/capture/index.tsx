import React, { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import Link from 'next/link';
import DarkLayout from '../../components/layout/DarkLayout';
import { withAuth } from '../../contexts/AuthContext';
import { UserRole } from '../../contexts/AuthContext';
import { api } from '../../utils/api';
import ParliamentTVCapture from '../../components/parliament-tv/ParliamentTVCapture';
import { Card, Button, Badge, Table, TableHead, TableBody, TableRow, TableHeaderCell, TableCell, Select } from '../../components/ui';

interface CaptureSession {
  id: number;
  title: string;
  status: string;
  start_time: string;
  end_time: string | null;
  file_path: string | null;
  file_size: number | null;
  duration: number | null;
  created_by_id: number;
  created_by: {
    id: number;
    name: string;
    email: string;
  };
  created_at: string;
  updated_at: string;
}

const CaptureListPage: React.FC = () => {
  const [filterStatus, setFilterStatus] = useState<string>('');
  const [showCaptureForm, setShowCaptureForm] = useState<boolean>(false);
  
  // Fetch capture sessions
  const { data: captureSessions, isLoading, isError, refetch } = useQuery({
    queryKey: ['captureSessions', filterStatus],
    queryFn: async () => {
      const params: Record<string, any> = {};
      if (filterStatus) {
        params.status = filterStatus;
      }
      return await api.get('/capture', params);
    },
  });

  // Stop capture mutation
  const stopCaptureMutation = useMutation({
    mutationFn: async (captureId: number) => {
      return await api.post(`/capture/${captureId}/stop`);
    },
    onSuccess: () => {
      refetch();
    },
  });

  // Format duration in seconds to HH:MM:SS
  const formatDuration = (seconds: number | null): string => {
    if (seconds === null) return '--:--:--';
    
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const remainingSeconds = Math.floor(seconds % 60);
    
    return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
  };

  // Format date to readable format
  const formatDate = (dateString: string): string => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-GB', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  // Format file size
  const formatFileSize = (bytes: number | null): string => {
    if (bytes === null) return '--';
    
    if (bytes < 1024) return bytes + ' B';
    else if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB';
    else if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
    else return (bytes / (1024 * 1024 * 1024)).toFixed(2) + ' GB';
  };

  // Calculate capture duration for active captures
  const getCaptureDuration = (capture: CaptureSession): string => {
    if (capture.duration) {
      return formatDuration(capture.duration);
    }
    
    if (capture.status === 'active' && capture.start_time) {
      const startTime = new Date(capture.start_time).getTime();
      const now = new Date().getTime();
      const durationSeconds = (now - startTime) / 1000;
      return formatDuration(durationSeconds);
    }
    
    return '--:--:--';
  };

  // Handle stop capture
  const handleStopCapture = (captureId: number) => {
    if (confirm('Are you sure you want to stop this capture session?')) {
      stopCaptureMutation.mutate(captureId);
    }
  };

  // Get status badge variant
  const getStatusBadgeVariant = (status: string): 'success' | 'primary' | 'danger' | 'warning' | 'secondary' => {
    switch (status) {
      case 'active':
        return 'success';
      case 'completed':
        return 'primary';
      case 'failed':
        return 'danger';
      case 'processing':
        return 'warning';
      default:
        return 'secondary';
    }
  };

  return (
    <DarkLayout title="Capture Sessions | Parliament Video Clip Manager">
      <div className="page-container">
        <div className="mb-6 flex justify-between items-center">
          <h1 className="text-3xl font-bold text-white">Parliament TV Capture</h1>
          <div>
            <Button
              onClick={() => setShowCaptureForm(!showCaptureForm)}
              variant="primary"
            >
              {showCaptureForm ? 'Hide Capture Form' : 'Start New Capture'}
            </Button>
          </div>
        </div>
        
        {/* Capture Form Section */}
        {showCaptureForm && (
          <Card className="mb-6" title="Start a New Capture">
            <ParliamentTVCapture 
              onSuccess={() => {
                setShowCaptureForm(false);
                refetch();
              }}
              onError={(error) => {
                console.error('Capture error:', error);
              }}
            />
          </Card>
        )}

        {/* Filters */}
        <Card title="Capture Sessions">
          <div className="flex justify-between items-center mb-4">
            <div></div>
            <div className="flex items-center">
              <Select
                id="status-filter"
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value)}
                options={[
                  { value: '', label: 'All Statuses' },
                  { value: 'active', label: 'Active' },
                  { value: 'completed', label: 'Completed' },
                  { value: 'failed', label: 'Failed' },
                  { value: 'processing', label: 'Processing' }
                ]}
                className="w-48"
              />
              <Button
                onClick={() => refetch()}
                variant="secondary"
                className="ml-3"
              >
                Refresh
              </Button>
            </div>
          </div>
        </Card>

        {/* Active Captures Section */}
        <div className="bg-gray-800 rounded-lg shadow overflow-hidden border border-gray-700">
          <div className="px-6 py-4 border-b border-gray-700">
            <h2 className="text-lg font-medium text-white">All Capture Sessions</h2>
          </div>
          
          <div>
            {isLoading ? (
              <div className="py-4 text-center">
                <p className="text-gray-400">Loading capture sessions...</p>
              </div>
            ) : isError ? (
              <div className="py-4 text-center">
                <p className="text-red-400">Error loading capture sessions. Please try again.</p>
              </div>
            ) : !captureSessions || captureSessions.length === 0 ? (
              <div className="py-4 text-center">
                <p className="text-gray-400">No capture sessions found.</p>
              </div>
            ) : (
              <Table>
                <TableHead>
                  <TableRow>
                    <TableHeaderCell>Title</TableHeaderCell>
                    <TableHeaderCell>Started</TableHeaderCell>
                    <TableHeaderCell>Duration</TableHeaderCell>
                    <TableHeaderCell>File Size</TableHeaderCell>
                    <TableHeaderCell>Status</TableHeaderCell>
                    <TableHeaderCell>Actions</TableHeaderCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {captureSessions?.map((capture: CaptureSession) => (
                    <TableRow key={capture.id}>
                      <TableCell>
                        <div className="text-sm font-medium text-white truncate max-w-xs" title={capture.title}>{capture.title}</div>
                        <div className="text-sm text-gray-400">By {capture.created_by?.name || 'Unknown'}</div>
                      </TableCell>
                      <TableCell>
                        <div className="text-sm text-gray-300">{formatDate(capture.start_time)}</div>
                      </TableCell>
                      <TableCell>
                        <div className="text-sm text-gray-300">{getCaptureDuration(capture)}</div>
                      </TableCell>
                      <TableCell>
                        <div className="text-sm text-gray-300">{formatFileSize(capture.file_size)}</div>
                      </TableCell>
                      <TableCell>
                        <Badge variant={getStatusBadgeVariant(capture.status)}>
                          {capture.status.charAt(0).toUpperCase() + capture.status.slice(1)}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <div className="flex space-x-3">
                          <Link href={`/capture/${capture.id}`}>
                            <Button size="sm" variant="primary">View</Button>
                          </Link>
                          {capture.status === 'active' && (
                            <Button
                              size="sm"
                              variant="danger"
                              onClick={() => handleStopCapture(capture.id)}
                              disabled={stopCaptureMutation.isPending}
                            >
                              {stopCaptureMutation.isPending && stopCaptureMutation.variables === capture.id
                                ? 'Stopping...'
                                : 'Stop'}
                            </Button>
                          )}
                          {capture.status === 'completed' && (
                            <Link href={`/clips/new?source_type=capture&source_id=${capture.id}`}>
                              <Button size="sm" variant="secondary">Create Clip</Button>
                            </Link>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </div>
        </div>
      </div>
    </DarkLayout>
  );
};

export default withAuth(CaptureListPage, [UserRole.ADMIN, UserRole.MP, UserRole.STAFF]);
