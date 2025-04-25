import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Link from 'next/link';
import MainLayout from '../../../components/layout/MainLayout';
import { withAuth } from '../../../contexts/AuthContext';
import { UserRole } from '../../../contexts/AuthContext';
import { api } from '../../../utils/api';

interface StorageStats {
  total: number;
  used: number;
  available: number;
  usage_percent: number;
  categories: {
    clips: number;
    captures: number;
    thumbnails: number;
    transcriptions: number;
    other: number;
  };
  oldest_files: {
    clips: Array<{
      id: number;
      title: string;
      file_path: string;
      file_size: number;
      created_at: string;
      last_accessed: string | null;
    }>;
    captures: Array<{
      id: number;
      title: string;
      file_path: string;
      file_size: number;
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
  const { data: storageStats, isLoading: statsLoading } = useQuery({
    queryKey: ['storageStats'],
    queryFn: async () => {
      return await api.get('/admin/storage/stats');
    },
  });
  
  // Fetch cleanup settings
  const { data: settingsData, isLoading: settingsLoading } = useQuery({
    queryKey: ['cleanupSettings'],
    queryFn: async () => {
      return await api.get('/admin/storage/settings');
    },
    onSuccess: (data) => {
      setCleanupSettings(data);
    },
  });
  
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
    if (confirm('Are you sure you want to run storage cleanup? This will delete old files based on your settings.')) {
      runCleanupMutation.mutate();
    }
  };
  
  // Handle delete file
  const handleDeleteFile = (type: 'clip' | 'capture', id: number, title: string) => {
    if (confirm(`Are you sure you want to delete ${type} "${title}"? This action cannot be undone.`)) {
      deleteFileMutation.mutate({ type, id });
    }
  };
  
  // Calculate storage category percentages
  const calculateCategoryPercentage = (categorySize: number): number => {
    if (!storageStats || !storageStats.used || storageStats.used === 0) return 0;
    return Math.round((categorySize / storageStats.used) * 100);
  };
  
  return (
    <MainLayout title="Storage Management | Parliament Video Clip Manager">
      <div className="page-container">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-3xl font-bold text-gray-900">Storage Management</h1>
          <button
            type="button"
            onClick={handleRunCleanup}
            disabled={runCleanupMutation.isPending}
            className="btn-primary rounded-md px-4 py-2 text-center cursor-pointer inline-block disabled:opacity-50"
          >
            {runCleanupMutation.isPending ? 'Running Cleanup...' : 'Run Cleanup Now'}
          </button>
        </div>
        
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left column - Storage overview */}
          <div className="lg:col-span-2">
            <div className="bg-white rounded-lg shadow overflow-hidden mb-6">
              <div className="px-6 py-4 border-b border-gray-200">
                <h2 className="text-lg font-medium text-gray-800">Storage Overview</h2>
              </div>
              
              {statsLoading ? (
                <div className="p-6 text-center text-gray-500">Loading storage statistics...</div>
              ) : storageStats ? (
                <div className="p-6">
                  {/* Storage usage */}
                  <div className="mb-6">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium text-gray-700">
                        {formatBytes(storageStats.used)} of {formatBytes(storageStats.total)} used
                      </span>
                      <span className="text-sm font-medium text-gray-700">
                        {storageStats.usage_percent}%
                      </span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2.5">
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
                    <div className="mt-2 text-sm text-gray-500">
                      {formatBytes(storageStats.available)} available
                    </div>
                  </div>
                  
                  {/* Storage breakdown */}
                  <div>
                    <h3 className="text-sm font-medium text-gray-700 mb-4">Storage Breakdown</h3>
                    <div className="space-y-4">
                      <div>
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-sm text-gray-600">Video Clips</span>
                          <span className="text-sm text-gray-600">
                            {formatBytes(storageStats.categories.clips)} ({calculateCategoryPercentage(storageStats.categories.clips)}%)
                          </span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-1.5">
                          <div
                            className="h-1.5 rounded-full bg-blue-600"
                            style={{ width: `${calculateCategoryPercentage(storageStats.categories.clips)}%` }}
                          ></div>
                        </div>
                      </div>
                      
                      <div>
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-sm text-gray-600">Capture Sessions</span>
                          <span className="text-sm text-gray-600">
                            {formatBytes(storageStats.categories.captures)} ({calculateCategoryPercentage(storageStats.categories.captures)}%)
                          </span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-1.5">
                          <div
                            className="h-1.5 rounded-full bg-green-600"
                            style={{ width: `${calculateCategoryPercentage(storageStats.categories.captures)}%` }}
                          ></div>
                        </div>
                      </div>
                      
                      <div>
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-sm text-gray-600">Thumbnails</span>
                          <span className="text-sm text-gray-600">
                            {formatBytes(storageStats.categories.thumbnails)} ({calculateCategoryPercentage(storageStats.categories.thumbnails)}%)
                          </span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-1.5">
                          <div
                            className="h-1.5 rounded-full bg-yellow-500"
                            style={{ width: `${calculateCategoryPercentage(storageStats.categories.thumbnails)}%` }}
                          ></div>
                        </div>
                      </div>
                      
                      <div>
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-sm text-gray-600">Transcriptions</span>
                          <span className="text-sm text-gray-600">
                            {formatBytes(storageStats.categories.transcriptions)} ({calculateCategoryPercentage(storageStats.categories.transcriptions)}%)
                          </span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-1.5">
                          <div
                            className="h-1.5 rounded-full bg-purple-600"
                            style={{ width: `${calculateCategoryPercentage(storageStats.categories.transcriptions)}%` }}
                          ></div>
                        </div>
                      </div>
                      
                      <div>
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-sm text-gray-600">Other</span>
                          <span className="text-sm text-gray-600">
                            {formatBytes(storageStats.categories.other)} ({calculateCategoryPercentage(storageStats.categories.other)}%)
                          </span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-1.5">
                          <div
                            className="h-1.5 rounded-full bg-gray-600"
                            style={{ width: `${calculateCategoryPercentage(storageStats.categories.other)}%` }}
                          ></div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="p-6 text-center text-red-500">Error loading storage statistics</div>
              )}
            </div>
            
            {/* Oldest files */}
            {storageStats && (
              <div className="bg-white rounded-lg shadow overflow-hidden">
                <div className="px-6 py-4 border-b border-gray-200">
                  <h2 className="text-lg font-medium text-gray-800">Oldest Files</h2>
                </div>
                
                <div className="p-6">
                  <div className="mb-6">
                    <h3 className="text-sm font-medium text-gray-700 mb-3">Oldest Video Clips</h3>
                    {storageStats.oldest_files.clips.length === 0 ? (
                      <p className="text-sm text-gray-500">No video clips found</p>
                    ) : (
                      <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-gray-200">
                          <thead className="bg-gray-50">
                            <tr>
                              <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                Title
                              </th>
                              <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                Size
                              </th>
                              <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                Created
                              </th>
                              <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                Last Accessed
                              </th>
                              <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                Actions
                              </th>
                            </tr>
                          </thead>
                          <tbody className="bg-white divide-y divide-gray-200">
                            {storageStats.oldest_files.clips.map((clip) => (
                              <tr key={clip.id} className="hover:bg-gray-50">
                                <td className="px-4 py-3 whitespace-nowrap">
                                  <div className="text-sm font-medium text-gray-900">{clip.title}</div>
                                </td>
                                <td className="px-4 py-3 whitespace-nowrap">
                                  <div className="text-sm text-gray-500">{formatBytes(clip.file_size)}</div>
                                </td>
                                <td className="px-4 py-3 whitespace-nowrap">
                                  <div className="text-sm text-gray-500">{formatDate(clip.created_at)}</div>
                                </td>
                                <td className="px-4 py-3 whitespace-nowrap">
                                  <div className="text-sm text-gray-500">{formatDate(clip.last_accessed)}</div>
                                </td>
                                <td className="px-4 py-3 whitespace-nowrap text-sm font-medium">
                                  <Link href={`/clips/${clip.id}`}>
                                    <span className="text-primary hover:text-primary-dark mr-3 cursor-pointer">
                                      View
                                    </span>
                                  </Link>
                                  <button
                                    type="button"
                                    onClick={() => handleDeleteFile('clip', clip.id, clip.title)}
                                    disabled={deleteFileMutation.isPending}
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
                    )}
                  </div>
                  
                  <div>
                    <h3 className="text-sm font-medium text-gray-700 mb-3">Oldest Capture Sessions</h3>
                    {storageStats.oldest_files.captures.length === 0 ? (
                      <p className="text-sm text-gray-500">No capture sessions found</p>
                    ) : (
                      <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-gray-200">
                          <thead className="bg-gray-50">
                            <tr>
                              <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                Title
                              </th>
                              <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                Size
                              </th>
                              <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                Created
                              </th>
                              <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                Last Accessed
                              </th>
                              <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                Actions
                              </th>
                            </tr>
                          </thead>
                          <tbody className="bg-white divide-y divide-gray-200">
                            {storageStats.oldest_files.captures.map((capture) => (
                              <tr key={capture.id} className="hover:bg-gray-50">
                                <td className="px-4 py-3 whitespace-nowrap">
                                  <div className="text-sm font-medium text-gray-900">{capture.title}</div>
                                </td>
                                <td className="px-4 py-3 whitespace-nowrap">
                                  <div className="text-sm text-gray-500">{formatBytes(capture.file_size)}</div>
                                </td>
                                <td className="px-4 py-3 whitespace-nowrap">
                                  <div className="text-sm text-gray-500">{formatDate(capture.created_at)}</div>
                                </td>
                                <td className="px-4 py-3 whitespace-nowrap">
                                  <div className="text-sm text-gray-500">{formatDate(capture.last_accessed)}</div>
                                </td>
                                <td className="px-4 py-3 whitespace-nowrap text-sm font-medium">
                                  <Link href={`/capture/${capture.id}`}>
                                    <span className="text-primary hover:text-primary-dark mr-3 cursor-pointer">
                                      View
                                    </span>
                                  </Link>
                                  <button
                                    type="button"
                                    onClick={() => handleDeleteFile('capture', capture.id, capture.title)}
                                    disabled={deleteFileMutation.isPending}
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
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
          
          {/* Right column - Cleanup settings */}
          <div>
            <div className="bg-white rounded-lg shadow overflow-hidden sticky top-6">
              <div className="px-6 py-4 border-b border-gray-200">
                <h2 className="text-lg font-medium text-gray-800">Cleanup Settings</h2>
              </div>
              
              {settingsLoading ? (
                <div className="p-6 text-center text-gray-500">Loading settings...</div>
              ) : (
                <div className="p-6">
                  <div className="space-y-6">
                    <div className="flex items-start">
                      <div className="flex items-center h-5">
                        <input
                          id="auto_cleanup_enabled"
                          name="auto_cleanup_enabled"
                          type="checkbox"
                          checked={cleanupSettings.auto_cleanup_enabled}
                          onChange={handleSettingsChange}
                          className="h-4 w-4 text-primary focus:ring-primary border-gray-300 rounded"
                        />
                      </div>
                      <div className="ml-3 text-sm">
                        <label htmlFor="auto_cleanup_enabled" className="font-medium text-gray-700">
                          Enable Automatic Cleanup
                        </label>
                        <p className="text-gray-500">
                          Automatically delete old files based on settings below
                        </p>
                      </div>
                    </div>
                    
                    <div>
                      <label htmlFor="retention_days" className="block text-sm font-medium text-gray-700 mb-1">
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
                        className="form-input"
                      />
                      <p className="mt-1 text-sm text-gray-500">
                        Files older than this will be eligible for cleanup
                      </p>
                    </div>
                    
                    <div>
                      <label htmlFor="min_free_space_gb" className="block text-sm font-medium text-gray-700 mb-1">
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
                        className="form-input"
                      />
                      <p className="mt-1 text-sm text-gray-500">
                        Cleanup will run when free space falls below this threshold
                      </p>
                    </div>
                    
                    <div>
                      <label htmlFor="exclude_viewed_days" className="block text-sm font-medium text-gray-700 mb-1">
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
                        className="form-input"
                      />
                      <p className="mt-1 text-sm text-gray-500">
                        Files viewed within this period will not be deleted
                      </p>
                    </div>
                    
                    <div className="pt-4">
                      <button
                        type="button"
                        onClick={handleSaveSettings}
                        disabled={updateSettingsMutation.isPending}
                        className="w-full btn-primary rounded-md px-4 py-2 text-center cursor-pointer inline-block disabled:opacity-50"
                      >
                        {updateSettingsMutation.isPending ? 'Saving...' : 'Save Settings'}
                      </button>
                    </div>
                  </div>
                  
                  <div className="mt-6 p-4 bg-yellow-50 border-l-4 border-yellow-400 rounded-md">
                    <div className="flex">
                      <div className="flex-shrink-0">
                        <svg className="h-5 w-5 text-yellow-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                          <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                        </svg>
                      </div>
                      <div className="ml-3">
                        <h3 className="text-sm font-medium text-yellow-800">Important Note</h3>
                        <div className="mt-2 text-sm text-yellow-700">
                          <p>
                            Automatic cleanup will permanently delete files based on your settings.
                            Make sure to back up important content before enabling.
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </MainLayout>
  );
};

export default withAuth(StorageManagement, [UserRole.ADMIN]);
