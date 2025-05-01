import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Link from 'next/link';
import MainLayout from '../../../components/layout/MainLayout';
import { withAuth } from '../../../contexts/AuthContext';
import { api } from '../../../utils/api';

interface SpeakerIdentification {
  id: number;
  capture_id: number;
  status: string;
  created_at: string;
  updated_at: string;
  results: any;
  output_file: string;
  threshold: number;
}

interface SpeakerInfo {
  name: string;
  frames: number;
  average_confidence: number;
  metadata?: {
    id: string;
    name: string;
    party: string;
    constituency: string;
  };
}

interface TimelineEntry {
  speaker: string;
  start_time: number;
  end_time: number;
  duration: number;
}

const SpeakerIdentificationPage: React.FC = () => {
  const router = useRouter();
  const { id } = router.query;
  const queryClient = useQueryClient();
  const [threshold, setThreshold] = useState(0.6);
  const [updateDb, setUpdateDb] = useState(false);

  // Fetch capture details
  const {
    data: capture,
    isLoading: captureLoading,
    error: captureError
  } = useQuery({
    queryKey: ['capture', id],
    queryFn: async () => {
      if (!id) return null;
      return await api.get(`/capture/${id}`);
    },
    enabled: !!id
  });

  // Fetch speaker identifications for this capture
  const {
    data: identifications,
    isLoading: identificationsLoading,
    error: identificationsError,
    refetch: refetchIdentifications
  } = useQuery({
    queryKey: ['speakerIdentifications', id],
    queryFn: async () => {
      if (!id) return [];
      return await api.get('/speakers', { capture_id: id });
    },
    enabled: !!id
  });

  // Start speaker identification mutation
  const startIdentification = useMutation({
    mutationFn: async () => {
      if (!id) return null;
      return await api.post('/speakers', {
        capture_id: Number(id),
        threshold,
        update_db: updateDb
      });
    },
    onSuccess: () => {
      console.log('Speaker identification started');
      refetchIdentifications();
    },
    onError: (error: any) => {
      console.error(`Error starting speaker identification: ${error.message}`);
    }
  });

  // Delete speaker identification mutation
  const deleteIdentification = useMutation({
    mutationFn: async (identificationId: number) => {
      return await api.delete(`/speakers/${identificationId}`);
    },
    onSuccess: () => {
      console.log('Speaker identification deleted');
      refetchIdentifications();
    },
    onError: (error: any) => {
      console.error(`Error deleting speaker identification: ${error.message}`);
    }
  });

  // Format time in seconds to MM:SS
  const formatTime = (seconds: number): string => {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.floor(seconds % 60);
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
  };

  // Handle form submission
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    startIdentification.mutate();
  };

  // Handle delete confirmation
  const handleDelete = (identificationId: number) => {
    if (window.confirm('Are you sure you want to delete this speaker identification?')) {
      deleteIdentification.mutate(identificationId);
    }
  };

  // Poll for updates if there are any processing identifications
  useEffect(() => {
    if (!identifications) return;
    
    const processingIdentifications = identifications.filter(
      (identification: SpeakerIdentification) => identification.status === 'pending' || identification.status === 'processing'
    );
    
    if (processingIdentifications.length > 0) {
      const interval = setInterval(() => {
        refetchIdentifications();
      }, 5000);
      
      return () => clearInterval(interval);
    }
  }, [identifications, refetchIdentifications]);

  if (captureLoading || identificationsLoading) {
    return (
      <MainLayout>
        <div className="container mx-auto px-4 py-8">
          <div className="flex justify-center items-center h-64">
            <div className="spinner"></div>
          </div>
        </div>
      </MainLayout>
    );
  }

  if (captureError || identificationsError) {
    return (
      <MainLayout>
        <div className="container mx-auto px-4 py-8">
          <div className="bg-red-100 border-l-4 border-red-500 text-red-700 p-4 mb-4">
            <p>Error loading data. Please try again.</p>
          </div>
          <button
            onClick={() => router.back()}
            className="bg-gray-200 hover:bg-gray-300 text-gray-800 font-semibold py-2 px-4 rounded"
          >
            Go Back
          </button>
        </div>
      </MainLayout>
    );
  }

  return (
    <MainLayout>
      <div className="container mx-auto px-4 py-8">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-2xl font-bold">Speaker Identification</h1>
          <Link href={`/capture/${id}`}>
            <span className="bg-gray-200 hover:bg-gray-300 text-gray-800 font-semibold py-2 px-4 rounded cursor-pointer">
              Back to Capture
            </span>
          </Link>
        </div>

        {capture && (
          <div className="bg-white shadow-md rounded-lg p-6 mb-6">
            <h2 className="text-xl font-semibold mb-4">Capture Details</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <p><span className="font-semibold">Title:</span> {capture.title}</p>
                <p><span className="font-semibold">Status:</span> {capture.status}</p>
                <p><span className="font-semibold">Created:</span> {new Date(capture.created_at).toLocaleString()}</p>
              </div>
              <div>
                <p><span className="font-semibold">ID:</span> {capture.id}</p>
                <p><span className="font-semibold">Duration:</span> {capture.duration ? formatTime(capture.duration) : 'N/A'}</p>
                <p><span className="font-semibold">File:</span> {capture.file_path ? capture.file_path.split('/').pop() : 'N/A'}</p>
              </div>
            </div>
          </div>
        )}

        <div className="bg-white shadow-md rounded-lg p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">Start New Speaker Identification</h2>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Recognition Threshold (lower is stricter)
              </label>
              <input
                type="range"
                min="0.4"
                max="0.8"
                step="0.05"
                value={threshold}
                onChange={(e) => setThreshold(parseFloat(e.target.value))}
                className="w-full"
              />
              <div className="flex justify-between text-xs text-gray-500">
                <span>Strict (0.4)</span>
                <span>Current: {threshold}</span>
                <span>Lenient (0.8)</span>
              </div>
            </div>
            
            <div className="flex items-center">
              <input
                type="checkbox"
                id="updateDb"
                checked={updateDb}
                onChange={(e) => setUpdateDb(e.target.checked)}
                className="h-4 w-4 text-primary focus:ring-primary border-gray-300 rounded"
              />
              <label htmlFor="updateDb" className="ml-2 block text-sm text-gray-700">
                Update MP database before processing
              </label>
            </div>
            
            <button
              type="submit"
              disabled={startIdentification.isLoading || !capture || capture.status !== 'completed'}
              className={`bg-primary hover:bg-primary-dark text-white font-bold py-2 px-4 rounded ${
                startIdentification.isLoading || !capture || capture.status !== 'completed'
                  ? 'opacity-50 cursor-not-allowed'
                  : ''
              }`}
            >
              {startIdentification.isLoading ? 'Starting...' : 'Start Speaker Identification'}
            </button>
            
            {!capture || capture.status !== 'completed' ? (
              <p className="text-sm text-red-500">
                Speaker identification can only be performed on completed captures.
              </p>
            ) : null}
          </form>
        </div>

        <div className="bg-white shadow-md rounded-lg p-6">
          <h2 className="text-xl font-semibold mb-4">Speaker Identifications</h2>
          
          {identifications && identifications.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">ID</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Created</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Primary Speaker</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {identifications.map((identification: SpeakerIdentification) => (
                    <tr key={identification.id}>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                        {identification.id}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                          identification.status === 'completed'
                            ? 'bg-green-100 text-green-800'
                            : identification.status === 'processing'
                            ? 'bg-yellow-100 text-yellow-800'
                            : identification.status === 'pending'
                            ? 'bg-blue-100 text-blue-800'
                            : 'bg-red-100 text-red-800'
                        }`}>
                          {identification.status.charAt(0).toUpperCase() + identification.status.slice(1)}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {new Date(identification.created_at).toLocaleString()}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {identification.results && identification.results.primary_speaker
                          ? identification.results.primary_speaker
                          : 'N/A'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                        {identification.status === 'completed' && (
                          <>
                            <button
                              onClick={() => router.push(`/capture/${id}/speakers/${identification.id}`)}
                              className="text-primary hover:text-primary-dark mr-3"
                            >
                              View
                            </button>
                            {identification.output_file && (
                              <a
                                href={identification.output_file}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-primary hover:text-primary-dark mr-3"
                              >
                                Download
                              </a>
                            )}
                          </>
                        )}
                        <button
                          onClick={() => handleDelete(identification.id)}
                          className="text-red-600 hover:text-red-900"
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-center py-4">
              <p className="text-gray-500">No speaker identifications found.</p>
            </div>
          )}
        </div>
      </div>
    </MainLayout>
  );
};

export default withAuth(SpeakerIdentificationPage);
