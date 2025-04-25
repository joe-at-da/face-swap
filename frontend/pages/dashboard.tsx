import React, { useEffect, useState } from 'react';
import MainLayout from '../components/layout/MainLayout';
import { withAuth } from '../contexts/AuthContext';
import { api } from '../utils/api';
import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';

interface DashboardStats {
  totalClips: number;
  recentClips: number;
  pendingCaptures: number;
  scheduledPosts: number;
  storageUsed: string;
  storageTotal: string;
}

interface RecentClip {
  id: number;
  title: string;
  duration: number;
  created_at: string;
  thumbnail_url: string;
}

const Dashboard: React.FC = () => {
  const [stats, setStats] = useState<DashboardStats>({
    totalClips: 0,
    recentClips: 0,
    pendingCaptures: 0,
    scheduledPosts: 0,
    storageUsed: '0 GB',
    storageTotal: '0 GB',
  });

  // Fetch dashboard stats
  const { data: statsData, isLoading: statsLoading } = useQuery({
    queryKey: ['dashboardStats'],
    queryFn: async () => {
      try {
        return await api.get('/dashboard/stats');
      } catch (error) {
        console.error('Failed to fetch dashboard stats:', error);
        return null;
      }
    },
  });

  // Fetch recent clips
  const { data: recentClipsData, isLoading: clipsLoading } = useQuery({
    queryKey: ['recentClips'],
    queryFn: async () => {
      try {
        return await api.get('/clips', { limit: 5, sort: 'created_at:desc' });
      } catch (error) {
        console.error('Failed to fetch recent clips:', error);
        return { items: [] };
      }
    },
  });

  useEffect(() => {
    if (statsData) {
      setStats(statsData);
    }
  }, [statsData]);

  const recentClips: RecentClip[] = recentClipsData?.items || [];

  // Format duration in seconds to MM:SS
  const formatDuration = (seconds: number): string => {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
  };

  // Format date to readable format
  const formatDate = (dateString: string): string => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-GB', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    });
  };

  return (
    <MainLayout title="Dashboard | Parliament Video Clip Manager">
      <div className="page-container">
        <h1 className="text-3xl font-bold text-gray-900 mb-6">Dashboard</h1>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <div className="p-3 rounded-full bg-blue-100 text-blue-500 mr-4">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"></path>
                </svg>
              </div>
              <div>
                <p className="text-gray-500 text-sm">Total Clips</p>
                <p className="text-2xl font-semibold text-gray-800">
                  {statsLoading ? '...' : stats.totalClips}
                </p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <div className="p-3 rounded-full bg-green-100 text-green-500 mr-4">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                </svg>
              </div>
              <div>
                <p className="text-gray-500 text-sm">Pending Captures</p>
                <p className="text-2xl font-semibold text-gray-800">
                  {statsLoading ? '...' : stats.pendingCaptures}
                </p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <div className="p-3 rounded-full bg-purple-100 text-purple-500 mr-4">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z"></path>
                </svg>
              </div>
              <div>
                <p className="text-gray-500 text-sm">Scheduled Posts</p>
                <p className="text-2xl font-semibold text-gray-800">
                  {statsLoading ? '...' : stats.scheduledPosts}
                </p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <div className="p-3 rounded-full bg-yellow-100 text-yellow-500 mr-4">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4"></path>
                </svg>
              </div>
              <div>
                <p className="text-gray-500 text-sm">Storage</p>
                <p className="text-2xl font-semibold text-gray-800">
                  {statsLoading ? '...' : `${stats.storageUsed} / ${stats.storageTotal}`}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="bg-white rounded-lg shadow mb-8">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-medium text-gray-800">Quick Actions</h2>
          </div>
          <div className="p-6 grid grid-cols-1 md:grid-cols-3 gap-4">
            <Link href="/capture/new">
              <span className="btn-primary rounded-md px-4 py-2 text-center cursor-pointer block">
                Start New Capture
              </span>
            </Link>
            <Link href="/clips/new">
              <span className="bg-secondary text-white hover:bg-secondary-dark rounded-md px-4 py-2 text-center cursor-pointer block">
                Create New Clip
              </span>
            </Link>
            <Link href="/social/new">
              <span className="bg-gray-700 text-white hover:bg-gray-800 rounded-md px-4 py-2 text-center cursor-pointer block">
                Create Social Post
              </span>
            </Link>
          </div>
        </div>

        {/* Recent Clips */}
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
            <h2 className="text-lg font-medium text-gray-800">Recent Clips</h2>
            <Link href="/clips">
              <span className="text-primary hover:text-primary-dark text-sm cursor-pointer">
                View All
              </span>
            </Link>
          </div>
          <div className="overflow-x-auto">
            {clipsLoading ? (
              <div className="p-6 text-center text-gray-500">Loading recent clips...</div>
            ) : recentClips.length === 0 ? (
              <div className="p-6 text-center text-gray-500">No clips found</div>
            ) : (
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Thumbnail
                    </th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Title
                    </th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Duration
                    </th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Created
                    </th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {recentClips.map((clip) => (
                    <tr key={clip.id}>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="w-16 h-9 bg-gray-200 rounded overflow-hidden">
                          {clip.thumbnail_url ? (
                            <img
                              src={clip.thumbnail_url}
                              alt={clip.title}
                              className="w-full h-full object-cover"
                            />
                          ) : (
                            <div className="w-full h-full flex items-center justify-center text-gray-400">
                              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"></path>
                              </svg>
                            </div>
                          )}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-medium text-gray-900">{clip.title}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-500">{formatDuration(clip.duration)}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-500">{formatDate(clip.created_at)}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                        <Link href={`/clips/${clip.id}`}>
                          <span className="text-primary hover:text-primary-dark mr-4 cursor-pointer">
                            View
                          </span>
                        </Link>
                        <Link href={`/clips/${clip.id}/edit`}>
                          <span className="text-primary hover:text-primary-dark cursor-pointer">
                            Edit
                          </span>
                        </Link>
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

export default withAuth(Dashboard);
