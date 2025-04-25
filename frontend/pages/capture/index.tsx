import React, { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import Link from 'next/link';
import MainLayout from '../../components/layout/MainLayout';
import { withAuth } from '../../contexts/AuthContext';
import { UserRole } from '../../contexts/AuthContext';
import { api } from '../../utils/api';

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

  // Get status badge color
  const getStatusBadgeClass = (status: string): string => {
    switch (status) {
      case 'active':
        return 'bg-green-100 text-green-800';
      case 'completed':
        return 'bg-blue-100 text-blue-800';
      case 'failed':
        return 'bg-red-100 text-red-800';
      case 'processing':
        return 'bg-yellow-100 text-yellow-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <MainLayout title="Capture Sessions | Parliament Video Clip Manager">
      <div className="page-container">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-3xl font-bold text-gray-900">Capture Sessions</h1>
          <Link href="/capture/new">
            <span className="btn-primary rounded-md px-4 py-2 text-center cursor-pointer inline-block">
              Start New Capture
            </span>
          </Link>
        </div>

        {/* Filters */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <div className="flex flex-col md:flex-row md:items-end space-y-4 md:space-y-0 md:space-x-4">
            <div className="w-full md:w-48">
              <label htmlFor="status" className="block text-sm font-medium text-gray-700 mb-1">
                Status
              </label>
              <select
                id="status"
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value)}
                className="form-input"
              >
                <option value="">All Statuses</option>
                <option value="active">Active</option>
                <option value="completed">Completed</option>
                <option value="processing">Processing</option>
                <option value="failed">Failed</option>
              </select>
            </div>
            
            <div>
              <button
                type="button"
                onClick={() => refetch()}
                className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
              >
                Refresh
              </button>
            </div>
          </div>
        </div>

        {/* Active Captures Section */}
        <div className="bg-white rounded-lg shadow mb-6 overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-medium text-gray-800">Active Captures</h2>
          </div>
          
          <div className="overflow-x-auto">
            {isLoading ? (
              <div className="p-6 text-center text-gray-500">Loading capture sessions...</div>
            ) : isError ? (
              <div className="p-6 text-center text-red-500">Error loading capture sessions</div>
            ) : (
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Title
                    </th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Started
                    </th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Duration
                    </th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Status
                    </th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {captureSessions?.filter((capture: CaptureSession) => capture.status === 'active').length === 0 ? (
                    <tr>
                      <td colSpan={5} className="px-6 py-4 text-center text-gray-500">
                        No active capture sessions
                      </td>
                    </tr>
                  ) : (
                    captureSessions
                      ?.filter((capture: CaptureSession) => capture.status === 'active')
                      .map((capture: CaptureSession) => (
                        <tr key={capture.id} className="hover:bg-gray-50">
                          <td className="px-6 py-4">
                            <div className="text-sm font-medium text-gray-900">{capture.title}</div>
                            <div className="text-sm text-gray-500">By {capture.created_by?.name || 'Unknown'}</div>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <div className="text-sm text-gray-500">{formatDate(capture.start_time)}</div>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <div className="text-sm text-gray-500">{getCaptureDuration(capture)}</div>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${getStatusBadgeClass(capture.status)}`}>
                              {capture.status.charAt(0).toUpperCase() + capture.status.slice(1)}
                            </span>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                            <Link href={`/capture/${capture.id}`}>
                              <span className="text-primary hover:text-primary-dark mr-3 cursor-pointer">
                                View
                              </span>
                            </Link>
                            <button
                              type="button"
                              onClick={() => handleStopCapture(capture.id)}
                              className="text-red-600 hover:text-red-900"
                              disabled={stopCaptureMutation.isPending}
                            >
                              {stopCaptureMutation.isPending && stopCaptureMutation.variables === capture.id
                                ? 'Stopping...'
                                : 'Stop'}
                            </button>
                          </td>
                        </tr>
                      ))
                  )}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {/* All Captures Section */}
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-medium text-gray-800">All Capture Sessions</h2>
          </div>
          
          <div className="overflow-x-auto">
            {isLoading ? (
              <div className="p-6 text-center text-gray-500">Loading capture sessions...</div>
            ) : isError ? (
              <div className="p-6 text-center text-red-500">Error loading capture sessions</div>
            ) : captureSessions?.length === 0 ? (
              <div className="p-6 text-center text-gray-500">
                No capture sessions found. Start a new capture to begin recording from Parliament TV.
              </div>
            ) : (
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Title
                    </th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Started
                    </th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Duration
                    </th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      File Size
                    </th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Status
                    </th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {captureSessions?.map((capture: CaptureSession) => (
                    <tr key={capture.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4">
                        <div className="text-sm font-medium text-gray-900">{capture.title}</div>
                        <div className="text-sm text-gray-500">By {capture.created_by?.name || 'Unknown'}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-500">{formatDate(capture.start_time)}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-500">{getCaptureDuration(capture)}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-500">{formatFileSize(capture.file_size)}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${getStatusBadgeClass(capture.status)}`}>
                          {capture.status.charAt(0).toUpperCase() + capture.status.slice(1)}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                        <Link href={`/capture/${capture.id}`}>
                          <span className="text-primary hover:text-primary-dark mr-3 cursor-pointer">
                            View
                          </span>
                        </Link>
                        {capture.status === 'active' && (
                          <button
                            type="button"
                            onClick={() => handleStopCapture(capture.id)}
                            className="text-red-600 hover:text-red-900 mr-3"
                            disabled={stopCaptureMutation.isPending}
                          >
                            {stopCaptureMutation.isPending && stopCaptureMutation.variables === capture.id
                              ? 'Stopping...'
                              : 'Stop'}
                          </button>
                        )}
                        {capture.status === 'completed' && (
                          <Link href={`/clips/new?source_type=capture&source_id=${capture.id}`}>
                            <span className="text-primary hover:text-primary-dark cursor-pointer">
                              Create Clip
                            </span>
                          </Link>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </div>
    </MainLayout>
  );
};

export default withAuth(CaptureListPage, [UserRole.ADMIN, UserRole.MP, UserRole.STAFF]);
