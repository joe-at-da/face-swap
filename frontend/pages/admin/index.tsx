import React from 'react';
import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import DarkLayout from '../../components/layout/DarkLayout';
import { withAuth } from '../../contexts/AuthContext';
import { UserRole } from '../../contexts/AuthContext';
import { api } from '../../utils/api';

interface SystemStats {
  storage: {
    total: number;
    used: number;
    available: number;
  };
  clips: {
    total: number;
    processing: number;
    completed: number;
    failed: number;
  };
  captures: {
    total: number;
    active: number;
    completed: number;
    failed: number;
  };
  users: {
    total: number;
    active: number;
    inactive: number;
  };
  social: {
    total_posts: number;
    scheduled_posts: number;
    published_posts: number;
  };
}

const AdminDashboard: React.FC = () => {
  // Define the SystemStats type
  interface SystemStats {
    storage: {
      total: number;
      used: number;
      available: number;
    };
    clips: {
      total: number;
      processing: number;
      completed: number;
      failed: number;
    };
    captures: {
      total: number;
      active: number;
      completed: number;
      failed: number;
    };
    users: {
      total: number;
      active: number;
      inactive: number;
    };
    social: {
      total: number;
      scheduled: number;
      published: number;
    };
  }

  // Default empty stats for initial state
  const emptyStats: SystemStats = {
    storage: { total: 0, used: 0, available: 0 },
    clips: { total: 0, processing: 0, completed: 0, failed: 0 },
    captures: { total: 0, active: 0, completed: 0, failed: 0 },
    users: { total: 0, active: 0, inactive: 0 },
    social: { total: 0, scheduled: 0, published: 0 }
  };

  // Fetch system stats with proper typing
  const { data: systemStats = emptyStats, isLoading: statsLoading, isError: statsError, refetch } = useQuery<SystemStats>({
    queryKey: ['systemStats'],
    queryFn: async () => {
      console.log('Fetching system stats from API...');
      try {
        const response = await api.get('/admin/stats');
        console.log('System stats API response:', response);
        return response as SystemStats;
      } catch (error) {
        console.error('Error fetching system stats:', error);
        throw error;
      }
    },
    refetchOnWindowFocus: true,
    refetchOnMount: true,
    staleTime: 0, // Always consider data stale
    retry: 2,
  });
  
  // Format bytes to human-readable format
  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };
  
  // Calculate storage usage percentage
  const calculateStoragePercentage = (stats: SystemStats): number => {
    if (!stats || !stats.storage || stats.storage.total === 0) return 0;
    return Math.round((stats.storage.used / stats.storage.total) * 100);
  };
  
  return (
    <DarkLayout title="Admin Dashboard | Parliament Video Clip Manager">
      <div className="page-container">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-3xl font-bold text-white">Admin Dashboard</h1>
          <button 
            onClick={() => {
              console.log('Manually refreshing system stats...');
              refetch();
            }}
            className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded flex items-center"
          >
            <svg className="h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Refresh Data
          </button>
        </div>
        
        {/* Quick links */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
          <Link href="/admin/users">
            <div className="bg-gray-800 rounded-lg shadow p-6 hover:shadow-md transition-shadow cursor-pointer border border-gray-700">
              <div className="flex items-center">
                <div className="p-3 rounded-full bg-gray-700 text-blue-400">
                  <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
                  </svg>
                </div>
                <div className="ml-4">
                  <h2 className="text-lg font-medium text-white">User Management</h2>
                  <p className="text-sm text-gray-400">Manage users, roles and permissions</p>
                </div>
              </div>
            </div>
          </Link>
          
          <Link href="/admin/storage">
            <div className="bg-gray-800 rounded-lg shadow p-6 hover:shadow-md transition-shadow cursor-pointer border border-gray-700">
              <div className="flex items-center">
                <div className="p-3 rounded-full bg-gray-700 text-blue-400">
                  <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4" />
                  </svg>
                </div>
                <div className="ml-4">
                  <h2 className="text-lg font-medium text-white">Storage Management</h2>
                  <p className="text-sm text-gray-400">Manage storage and file retention</p>
                </div>
              </div>
            </div>
          </Link>
          
          <Link href="/admin/system">
            <div className="bg-gray-800 rounded-lg shadow p-6 hover:shadow-md transition-shadow cursor-pointer border border-gray-700">
              <div className="flex items-center">
                <div className="p-3 rounded-full bg-gray-700 text-green-400">
                  <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  </svg>
                </div>
                <div className="ml-4">
                  <h2 className="text-lg font-medium text-white">System Settings</h2>
                  <p className="text-sm text-gray-400">Configure application settings</p>
                </div>
              </div>
            </div>
          </Link>
        </div>
        
        {/* System overview */}
        <div className="bg-gray-800 rounded-lg shadow overflow-hidden mb-6 border border-gray-700">
          <div className="px-6 py-4 border-b border-gray-700">
            <h2 className="text-lg font-medium text-white">System Overview</h2>
          </div>
          
          <div className="p-6">
            {statsLoading ? (
              <div className="flex justify-center items-center h-40">
                <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
              </div>
            ) : statsError ? (
              <div className="text-center py-8">
                <svg className="mx-auto h-12 w-12 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <h3 className="text-lg font-medium mt-2 text-white">Error loading system statistics</h3>
                <p className="text-sm text-gray-400 mt-1">Please try refreshing the page or check system logs.</p>
                <button 
                  onClick={() => window.location.reload()} 
                  className="mt-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
                >
                  Refresh Page
                </button>
              </div>
            ) : !systemStats ? (
              <div className="p-6 text-center text-gray-400">
                <p>No system statistics available</p>
              </div>
            ) : systemStats.storage && systemStats.storage.total === 0 ? (
              <div className="text-center py-8">
                <svg className="mx-auto h-12 w-12 text-yellow-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
                <h3 className="text-lg font-medium mt-2 text-white">Storage Metrics Unavailable</h3>
                <p className="text-sm text-gray-400 mt-2">Unable to retrieve storage metrics. Docker may not be available.</p>
                <p className="text-sm text-gray-400 mt-1">Check system logs for more details.</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Storage usage */}
                <div className="bg-gray-900 rounded-lg p-6">
                  <h3 className="text-lg font-medium text-white mb-4">Storage Usage</h3>
                  {!systemStats.storage || systemStats.storage.total === 0 ? (
                    <div className="text-center py-4">
                      <svg className="mx-auto h-10 w-10 text-yellow-400 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                      </svg>
                      <p className="text-sm text-gray-400">Storage metrics unavailable</p>
                      <p className="text-xs text-gray-500 mt-1">Docker may not be available</p>
                    </div>
                  ) : (
                    <>
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-medium text-gray-400">
                          {formatBytes(systemStats.storage.used)} of {formatBytes(systemStats.storage.total)} used
                        </span>
                        <span className="text-sm font-medium text-gray-500">
                          {calculateStoragePercentage(systemStats)}%
                        </span>
                      </div>
                      <div className="w-full bg-gray-700 rounded-full h-2.5">
                        <div
                          className={`h-2.5 rounded-full ${
                            calculateStoragePercentage(systemStats) > 90
                              ? 'bg-red-600'
                              : calculateStoragePercentage(systemStats) > 70
                              ? 'bg-yellow-500'
                              : 'bg-green-600'
                          }`}
                          style={{ width: `${calculateStoragePercentage(systemStats)}%` }}
                        ></div>
                      </div>
                      <div className="mt-4 grid grid-cols-3 gap-2 text-center">
                        <div>
                          <p className="text-sm font-medium text-gray-400">Total</p>
                          <p className="text-lg font-semibold text-white">{formatBytes(systemStats.storage.total)}</p>
                        </div>
                        <div>
                          <p className="text-sm font-medium text-gray-400">Used</p>
                          <p className="text-lg font-semibold text-white">{formatBytes(systemStats.storage.used)}</p>
                        </div>
                        <div>
                          <p className="text-sm font-medium text-gray-400">Available</p>
                          <p className="text-lg font-semibold text-white">{formatBytes(systemStats.storage.available)}</p>
                        </div>
                      </div>
                    </>
                  )}
                  <div className="mt-4">
                    <Link href="/admin/storage">
                      <button className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded text-sm">
                        Manage Storage
                      </button>
                    </Link>
                  </div>
                </div>
                
                {/* User stats */}
                <div className="bg-gray-900 rounded-lg p-6">
                  <h3 className="text-lg font-medium text-white mb-4">User Statistics</h3>
                  <div className="grid grid-cols-3 gap-4 mb-4">
                    <div className="bg-gray-800 p-4 rounded-lg text-center">
                      <p className="text-2xl font-bold text-white">{systemStats.users.total}</p>
                      <p className="text-sm text-gray-400">Total Users</p>
                    </div>
                    <div className="bg-gray-800 p-4 rounded-lg text-center">
                      <p className="text-2xl font-bold text-green-400">{systemStats.users.active}</p>
                      <p className="text-sm text-gray-400">Active</p>
                    </div>
                    <div className="bg-gray-800 p-4 rounded-lg text-center">
                      <p className="text-2xl font-bold text-gray-500">{systemStats.users.inactive}</p>
                      <p className="text-sm text-gray-400">Inactive</p>
                    </div>
                  </div>
                  <div className="mt-4">
                    <Link href="/admin/users">
                      <span className="text-blue-400 hover:text-blue-300 text-sm cursor-pointer">
                        Manage Users →
                      </span>
                    </Link>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
        
        {/* Content stats */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
          {/* Clip stats */}
          <div className="bg-gray-800 rounded-lg shadow overflow-hidden border border-gray-700">
            <div className="px-6 py-4 border-b border-gray-700">
              <h2 className="text-lg font-medium text-white">Content Statistics</h2>
            </div>
            <div className="p-6">
              {statsLoading ? (
                <div className="flex justify-center items-center h-40">
                  <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-blue-500"></div>
                </div>
              ) : !systemStats ? (
                <div className="p-6 text-center text-gray-400">
                  <p>No content statistics available</p>
                </div>
              ) : (
                <div>
                  <div className="mb-6">
                    <h3 className="text-md font-medium text-white mb-3">Video Clips</h3>
                    <div className="grid grid-cols-4 gap-2">
                      <div className="bg-gray-900 p-3 rounded-lg text-center">
                        <p className="text-xl font-bold text-white">{systemStats.clips.total}</p>
                        <p className="text-xs text-gray-400">Total</p>
                      </div>
                      <div className="bg-gray-900 p-3 rounded-lg text-center">
                        <p className="text-xl font-bold text-green-400">{systemStats.clips.completed}</p>
                        <p className="text-xs text-gray-400">Completed</p>
                      </div>
                      <div className="bg-gray-900 p-3 rounded-lg text-center">
                        <p className="text-xl font-bold text-blue-400">{systemStats.clips.processing}</p>
                        <p className="text-xs text-gray-400">Processing</p>
                      </div>
                      <div className="bg-gray-900 p-3 rounded-lg text-center">
                        <p className="text-xl font-bold text-red-400">{systemStats.clips.failed}</p>
                        <p className="text-xs text-gray-400">Failed</p>
                      </div>
                    </div>
                  </div>
                  
                  <div>
                    <h3 className="text-md font-medium text-white mb-3">Capture Sessions</h3>
                    <div className="grid grid-cols-4 gap-2">
                      <div className="bg-gray-900 p-3 rounded-lg text-center">
                        <p className="text-xl font-bold text-white">{systemStats.captures.total}</p>
                        <p className="text-xs text-gray-400">Total</p>
                      </div>
                      <div className="bg-gray-900 p-3 rounded-lg text-center">
                        <p className="text-xl font-bold text-green-400">{systemStats.captures.completed}</p>
                        <p className="text-xs text-gray-400">Completed</p>
                      </div>
                      <div className="bg-gray-900 p-3 rounded-lg text-center">
                        <p className="text-xl font-bold text-blue-400">{systemStats.captures.active}</p>
                        <p className="text-xs text-gray-400">Active</p>
                      </div>
                      <div className="bg-gray-900 p-3 rounded-lg text-center">
                        <p className="text-xl font-bold text-red-400">{systemStats.captures.failed}</p>
                        <p className="text-xs text-gray-400">Failed</p>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
          
          {/* Social media stats */}
          <div className="bg-gray-800 rounded-lg shadow overflow-hidden border border-gray-700">
            <div className="px-6 py-4 border-b border-gray-700">
              <h2 className="text-lg font-medium text-white">Social Media</h2>
            </div>
            <div className="p-6">
              {statsLoading ? (
                <div className="flex justify-center items-center h-40">
                  <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-blue-500"></div>
                </div>
              ) : !systemStats ? (
                <div className="p-6 text-center text-gray-400">
                  <p>No social media statistics available</p>
                </div>
              ) : (
                <div>
                  <div className="grid grid-cols-3 gap-4 mb-4">
                    <div className="bg-gray-900 p-4 rounded-lg text-center">
                      <p className="text-2xl font-bold text-white">{systemStats.social.total}</p>
                      <p className="text-sm text-gray-400">Total Posts</p>
                    </div>
                    <div className="bg-gray-900 p-4 rounded-lg text-center">
                      <p className="text-2xl font-bold text-blue-400">{systemStats.social.scheduled}</p>
                      <p className="text-sm text-gray-400">Scheduled</p>
                    </div>
                    <div className="bg-gray-900 p-4 rounded-lg text-center">
                      <p className="text-2xl font-bold text-green-400">{systemStats.social.published}</p>
                      <p className="text-sm text-gray-400">Published</p>
                    </div>
                  </div>
                  <div className="mt-4">
                    <Link href="/social">
                      <span className="text-blue-400 hover:text-blue-300 text-sm cursor-pointer">
                        View Social Media Dashboard →
                      </span>
                    </Link>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
        
        {/* Quick actions */}
        <div className="bg-gray-800 rounded-lg shadow overflow-hidden border border-gray-700">
          <div className="px-6 py-4 border-b border-gray-700">
            <h2 className="text-lg font-medium text-white">Quick Actions</h2>
          </div>
          
          <div className="p-6">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <Link href="/admin/users/new">
                <span className="block p-4 bg-gray-900 rounded-lg text-center hover:bg-gray-700 transition-colors cursor-pointer">
                  <svg className="h-6 w-6 mx-auto text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z" />
                  </svg>
                  <span className="mt-2 block text-sm font-medium text-white">Add New User</span>
                </span>
              </Link>
              
              <Link href="/admin/storage/cleanup">
                <span className="block p-4 bg-gray-900 rounded-lg text-center hover:bg-gray-700 transition-colors cursor-pointer">
                  <svg className="h-6 w-6 mx-auto text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                  <span className="mt-2 block text-sm font-medium text-white">Storage Cleanup</span>
                </span>
              </Link>
              
              {/* TODO: Setup API doc and link to it from here */}
              <Link href="/admin/settings/api">
                <span className="block p-4 bg-gray-900 rounded-lg text-center hover:bg-gray-700 transition-colors cursor-pointer">
                  <svg className="h-6 w-6 mx-auto text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
                  </svg>
                  <span className="mt-2 block text-sm font-medium text-white">API Settings</span>
                </span>
              </Link>
              
              <Link href="/admin/logs">
                <span className="block p-4 bg-gray-900 rounded-lg text-center hover:bg-gray-700 transition-colors cursor-pointer">
                  <svg className="h-6 w-6 mx-auto text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  <span className="mt-2 block text-sm font-medium text-white">System Logs</span>
                </span>
              </Link>
            </div>
          </div>
        </div>
      </div>
    </DarkLayout>
  );
};

export default withAuth(AdminDashboard, [UserRole.ADMIN]);
