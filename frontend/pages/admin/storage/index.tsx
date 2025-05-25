import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Link from 'next/link';
import DarkLayout from '../../../components/layout/DarkLayout';
import { withAuth } from '../../../contexts/AuthContext';
import { UserRole } from '../../../contexts/AuthContext';
import { api } from '../../../utils/api';

interface StorageStats {
  total: number;
  used: number;
  available: number;
  usage_percent: number;
  file_count: number;
  average_file_size: number;
  categories: {
    clips: number;
    captures: number;
    thumbnails: number;
    transcriptions: number;
    other: number;
  };
  error?: string;
  oldest_files: {
    video_clips: Array<{
      id: number;
      name: string;
      file_path: string;
      size_bytes: number;
      created_at: string;
      last_accessed: string | null;
    }>;
    capture_sessions: Array<{
      id: number;
      name: string;
      file_path: string;
      size_bytes: number;
      created_at: string;
      last_accessed: string | null;
    }>;
  };
}

interface CleanupSettings {
  auto_cleanup_enabled: boolean;
  retention_days: number;
  min_free_space_gb: number;
  exclude_viewed_days: number;
}

const StorageManagement: React.FC = () => {
  const queryClient = useQueryClient();
  
  // Cleanup settings form state
  const [cleanupSettings, setCleanupSettings] = useState<CleanupSettings>({
    auto_cleanup_enabled: false,
    retention_days: 90,
    min_free_space_gb: 10,
    exclude_viewed_days: 30,
  });
  
  // Fetch storage stats
  const { data: storageStats, isLoading, isError } = useQuery<StorageStats>({
    queryKey: ['storageStats'],
    queryFn: async () => {
      return await api.get('/admin/storage/stats');
    },
  });
  
  // Fetch cleanup settings
  const { data: settingsData } = useQuery<CleanupSettings>({
    queryKey: ['cleanupSettings'],
    queryFn: async () => {
      return await api.get('/admin/storage/settings');
    },
  });
  
  // Set cleanup settings when data is fetched
  React.useEffect(() => {
    if (settingsData) {
      setCleanupSettings(settingsData);
    }
  }, [settingsData]);
  
  // Update cleanup settings mutation
  const updateSettingsMutation = useMutation({
    mutationFn: async (data: CleanupSettings) => {
      return await api.post('/admin/storage/settings', data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cleanupSettings'] });
    },
  });
  
  // Run cleanup mutation
  const runCleanupMutation = useMutation({
    mutationFn: async () => {
      return await api.post('/admin/storage/cleanup');
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['storageStats'] });
    },
  });
  
  // Delete file mutation
  const deleteFileMutation = useMutation({
    mutationFn: async ({ type, id }: { type: 'clip' | 'capture'; id: number }) => {
      return await api.delete(`/admin/${type === 'clip' ? 'clips' : 'capture'}/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['storageStats'] });
    },
  });
  
  // Format bytes to human-readable format
  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };
  
  // Format date to readable format
  const formatDate = (dateString: string | null): string => {
    if (!dateString) return 'Never';
    
    const date = new Date(dateString);
    return date.toLocaleDateString('en-GB', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    });
  };
  
  // Handle cleanup settings change
  const handleSettingsChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value, type, checked } = e.target;
    
    setCleanupSettings((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : type === 'number' ? parseInt(value) : value,
    }));
  };
  
  // Handle save settings
  const handleSaveSettings = () => {
    updateSettingsMutation.mutate(cleanupSettings);
  };
  
  // Handle run cleanup
  const handleRunCleanup = () => {
    if (window.confirm('Are you sure you want to run storage cleanup? This will delete files based on your settings.')) {
      runCleanupMutation.mutate();
    }
  };
  
  // Handle delete file
  const handleDeleteFile = (type: 'clip' | 'capture', id: number, title: string) => {
    if (window.confirm(`Are you sure you want to delete ${type} "${title}"? This action cannot be undone.`)) {
      deleteFileMutation.mutate({ type, id });
    }
  };
  
  // Calculate storage category percentages
  const calculateCategoryPercentage = (categorySize: number): number => {
    if (!storageStats || storageStats.used === 0) return 0;
    return Math.round((categorySize / storageStats.used) * 100);
  };
  
  return (
    <DarkLayout title="Storage Management | Parliament Video Clip Manager">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-3xl font-bold text-white">Storage Management</h1>
          <button
            onClick={handleRunCleanup}
            disabled={runCleanupMutation.isPending}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-gray-800 disabled:opacity-50"
          >
            {runCleanupMutation.isPending ? 'Running...' : 'Run Cleanup Now'}
          </button>
        </div>
        
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Storage overview */}
          <div className="lg:col-span-2">
            <div className="bg-gray-800 rounded-lg shadow overflow-hidden">
              <div className="px-6 py-4 border-b border-gray-700">
                <h2 className="text-lg font-medium text-white">Storage Overview</h2>
              </div>
              
              <div className="p-6">
                {isLoading ? (
                  <div className="flex justify-center items-center h-40">
                    <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
                  </div>
                ) : isError ? (
                  <div className="text-center py-8">
                    <svg className="mx-auto h-12 w-12 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <h3 className="text-lg font-medium mt-2 text-white">Error loading storage statistics</h3>
                    <p className="text-sm text-gray-400 mt-1">Please try refreshing the page or check system logs.</p>
                  </div>
                ) : !storageStats ? (
                  <div className="p-6 text-center text-gray-400">
                    <p>No storage statistics available</p>
                  </div>
                ) : storageStats.error ? (
                  <div className="text-center py-8">
                    <svg className="mx-auto h-12 w-12 text-yellow-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                    <h3 className="text-lg font-medium mt-2 text-white">Storage Metrics Unavailable</h3>
                    <p className="text-sm text-gray-400 mt-2">{storageStats.error}</p>
                    <p className="text-sm text-gray-400 mt-1">Check system logs for more details.</p>
                  </div>
                ) : (
                  <div>
                    <div className="mb-6">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-medium text-gray-400">
                          {formatBytes(storageStats.used)} of {formatBytes(storageStats.total)} used
                        </span>
                        <span className="text-sm font-medium text-gray-400">
                          {storageStats.usage_percent}%
                        </span>
                      </div>
                      <div className="w-full bg-gray-700 rounded-full h-2.5">
                        <div
                          className={`h-2.5 rounded-full ${
                            storageStats.usage_percent > 90
                              ? 'bg-red-600'
                              : storageStats.usage_percent > 70
                              ? 'bg-yellow-500'
                              : 'bg-green-600'
                          }`}
                          style={{ width: `${storageStats.usage_percent}%` }}
                        ></div>
                      </div>
                    </div>
                    
                    <div className="grid grid-cols-3 gap-4 mb-6">
                      <div className="bg-gray-700 rounded-lg p-4 text-center">
                        <p className="text-sm text-gray-400">Total</p>
                        <p className="text-xl font-semibold text-white">{formatBytes(storageStats.total)}</p>
                      </div>
                      <div className="bg-gray-700 rounded-lg p-4 text-center">
                        <p className="text-sm text-gray-400">Used</p>
                        <p className="text-xl font-semibold text-white">{formatBytes(storageStats.used)}</p>
                      </div>
                      <div className="bg-gray-700 rounded-lg p-4 text-center">
                        <p className="text-sm text-gray-400">Available</p>
                        <p className="text-xl font-semibold text-white">{formatBytes(storageStats.available)}</p>
                      </div>
                    </div>
                    
                    <div className="mb-6">
                      <h3 className="text-md font-medium text-white mb-3">Storage Breakdown</h3>
                      {Object.entries(storageStats.categories).map(([category, bytes]) => {
                        const categoryName = category.charAt(0).toUpperCase() + category.slice(1);
                        const percentage = calculateCategoryPercentage(bytes);
                        const formattedSize = formatBytes(bytes);
                        
                        return (
                          <div key={category} className="mb-3">
                            <div className="flex justify-between mb-1">
                              <span className="text-sm font-medium text-gray-400">{categoryName}</span>
                              <span className="text-sm font-medium text-gray-400">{formattedSize} ({percentage}%)</span>
                            </div>
                            <div className="w-full bg-gray-700 rounded-full h-1.5">
                              <div
                                className="h-1.5 rounded-full bg-blue-500"
                                style={{ width: `${percentage}%` }}
                              ></div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                    
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <h3 className="text-md font-medium text-white mb-3">File Statistics</h3>
                        <div className="bg-gray-700 rounded-lg p-4">
                          <div className="flex justify-between mb-2">
                            <span className="text-sm text-gray-400">Total Files</span>
                            <span className="text-sm font-medium text-white">{storageStats.file_count.toLocaleString()}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-sm text-gray-400">Average File Size</span>
                            <span className="text-sm font-medium text-white">{formatBytes(storageStats.average_file_size)}</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
            
            {/* Oldest files */}
            {storageStats && !isLoading && !isError && !storageStats.error && (
              <div className="mt-6 bg-gray-800 rounded-lg shadow overflow-hidden">
                <div className="px-6 py-4 border-b border-gray-700">
                  <h2 className="text-lg font-medium text-white">Oldest Files</h2>
                </div>
                
                <div className="p-6">
                  <div className="mb-6">
                    <h3 className="text-md font-medium text-white mb-3">Video Clips</h3>
                    {storageStats.oldest_files.video_clips.length === 0 ? (
                      <p className="text-sm text-gray-400">No video clips found</p>
                    ) : (
                      <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-gray-700">
                          <thead className="bg-gray-700">
                            <tr>
                              <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Name</th>
                              <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Size</th>
                              <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Created</th>
                              <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Last Accessed</th>
                              <th scope="col" className="px-4 py-3 text-right text-xs font-medium text-gray-300 uppercase tracking-wider">Actions</th>
                            </tr>
                          </thead>
                          <tbody className="bg-gray-800 divide-y divide-gray-700">
                            {storageStats.oldest_files.video_clips.map((clip) => (
                              <tr key={clip.id}>
                                <td className="px-4 py-3 whitespace-nowrap">
                                  <div className="text-sm font-medium text-white">{clip.name}</div>
                                  <div className="text-xs text-gray-400">{clip.file_path}</div>
                                </td>
                                <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-300">{formatBytes(clip.size_bytes)}</td>
                                <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-300">{formatDate(clip.created_at)}</td>
                                <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-300">{formatDate(clip.last_accessed)}</td>
                                <td className="px-4 py-3 whitespace-nowrap text-sm font-medium text-right">
                                  <Link href={`/clips/${clip.id}`}>
                                    <span className="text-blue-400 hover:text-blue-300 mr-3 cursor-pointer">
                                      View
                                    </span>
                                  </Link>
                                  <button
                                    type="button"
                                    onClick={() => handleDeleteFile('clip', clip.id, clip.name)}
                                    disabled={deleteFileMutation.isPending}
                                    className="text-red-400 hover:text-red-300"
                                  >
                                    Delete
                                  </button>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>
                  
                  <div>
                    <h3 className="text-md font-medium text-white mb-3">Capture Sessions</h3>
                    {storageStats.oldest_files.capture_sessions.length === 0 ? (
                      <p className="text-sm text-gray-400">No capture sessions found</p>
                    ) : (
                      <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-gray-700">
                          <thead className="bg-gray-700">
                            <tr>
                              <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Name</th>
                              <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Size</th>
                              <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Created</th>
                              <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Last Accessed</th>
                              <th scope="col" className="px-4 py-3 text-right text-xs font-medium text-gray-300 uppercase tracking-wider">Actions</th>
                            </tr>
                          </thead>
                          <tbody className="bg-gray-800 divide-y divide-gray-700">
                            {storageStats.oldest_files.capture_sessions.map((capture) => (
                              <tr key={capture.id}>
                                <td className="px-4 py-3 whitespace-nowrap">
                                  <div className="text-sm font-medium text-white">{capture.name}</div>
                                  <div className="text-xs text-gray-400">{capture.file_path}</div>
                                </td>
                                <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-300">{formatBytes(capture.size_bytes)}</td>
                                <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-300">{formatDate(capture.created_at)}</td>
                                <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-300">{formatDate(capture.last_accessed)}</td>
                                <td className="px-4 py-3 whitespace-nowrap text-sm font-medium text-right">
                                  <Link href={`/capture/${capture.id}`}>
                                    <span className="text-blue-400 hover:text-blue-300 mr-3 cursor-pointer">
                                      View
                                    </span>
                                  </Link>
                                  <button
                                    type="button"
                                    onClick={() => handleDeleteFile('capture', capture.id, capture.name)}
                                    disabled={deleteFileMutation.isPending}
                                    className="text-red-400 hover:text-red-300"
                                  >
                                    Delete
                                  </button>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
          
          {/* Cleanup settings */}
          <div>
            <div className="bg-gray-800 rounded-lg shadow overflow-hidden">
              <div className="px-6 py-4 border-b border-gray-700">
                <h2 className="text-lg font-medium text-white">Cleanup Settings</h2>
              </div>
              
              <div className="p-6">
                <div className="space-y-4">
                  <div>
                    <label className="flex items-center">
                      <input
                        type="checkbox"
                        name="auto_cleanup_enabled"
                        checked={cleanupSettings.auto_cleanup_enabled}
                        onChange={handleSettingsChange}
                        className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-600 rounded"
                      />
                      <span className="ml-2 text-sm font-medium text-white">Enable Automatic Cleanup</span>
                    </label>
                    <p className="mt-1 text-sm text-gray-400">
                      Automatically cleans old files when storage is low
                    </p>
                  </div>
                  
                  <div>
                    <label htmlFor="retention_days" className="block text-sm font-medium text-white mb-1">
                      Retention Period (days)
                    </label>
                    <input
                      type="number"
                      id="retention_days"
                      name="retention_days"
                      min="1"
                      max="365"
                      value={cleanupSettings.retention_days}
                      onChange={handleSettingsChange}
                      className="bg-gray-700 border border-gray-600 text-white rounded-md px-4 py-2 w-full"
                    />
                    <p className="mt-1 text-sm text-gray-400">
                      Files older than this will be eligible for cleanup
                    </p>
                  </div>
                  
                  <div>
                    <label htmlFor="min_free_space_gb" className="block text-sm font-medium text-white mb-1">
                      Minimum Free Space (GB)
                    </label>
                    <input
                      type="number"
                      id="min_free_space_gb"
                      name="min_free_space_gb"
                      min="1"
                      max="1000"
                      value={cleanupSettings.min_free_space_gb}
                      onChange={handleSettingsChange}
                      className="bg-gray-700 border border-gray-600 text-white rounded-md px-4 py-2 w-full"
                    />
                    <p className="mt-1 text-sm text-gray-400">
                      Cleanup will run when free space falls below this threshold
                    </p>
                  </div>
                  
                  <div>
                    <label htmlFor="exclude_viewed_days" className="block text-sm font-medium text-white mb-1">
                      Exclude Recently Viewed (days)
                    </label>
                    <input
                      type="number"
                      id="exclude_viewed_days"
                      name="exclude_viewed_days"
                      min="0"
                      max="90"
                      value={cleanupSettings.exclude_viewed_days}
                      onChange={handleSettingsChange}
                      className="bg-gray-700 border border-gray-600 text-white rounded-md px-4 py-2 w-full"
                    />
                    <p className="mt-1 text-sm text-gray-400">
                      Files viewed within this period will not be deleted
                    </p>
                  </div>
                  
                  <div className="pt-4">
                    <button
                      type="button"
                      onClick={handleSaveSettings}
                      disabled={updateSettingsMutation.isPending}
                      className="w-full bg-blue-600 hover:bg-blue-700 text-white rounded-md px-4 py-2 text-center cursor-pointer inline-block disabled:opacity-50"
                    >
                      {updateSettingsMutation.isPending ? 'Saving...' : 'Save Settings'}
                    </button>
                  </div>
                </div>
                
                <div className="mt-6 p-4 bg-gray-700 border-l-4 border-yellow-400 rounded-md">
                  <div className="flex">
                    <div className="flex-shrink-0">
                      <svg className="h-5 w-5 text-yellow-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                        <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                      </svg>
                    </div>
                    <div className="ml-3">
                      <h3 className="text-sm font-medium text-yellow-300">Important Note</h3>
                      <div className="mt-2 text-sm text-gray-300">
                        <p>
                          Automatic cleanup will permanently delete files based on your settings.
                          Make sure to back up important content before enabling.
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </DarkLayout>
  );
};

export default withAuth(StorageManagement, [UserRole.ADMIN]);
