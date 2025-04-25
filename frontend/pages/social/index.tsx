import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import MainLayout from '../../components/layout/MainLayout';
import { withAuth } from '../../contexts/AuthContext';
import { UserRole } from '../../contexts/AuthContext';
import { api } from '../../utils/api';

interface SocialPost {
  id: number;
  title: string;
  content: string;
  platform: 'twitter' | 'facebook' | 'instagram';
  status: 'draft' | 'scheduled' | 'published' | 'failed';
  scheduled_time: string | null;
  published_time: string | null;
  clip_id: number;
  clip: {
    id: number;
    title: string;
    thumbnail_url: string | null;
  };
  created_by_id: number;
  created_by: {
    id: number;
    name: string;
    email: string;
  };
  engagement: {
    likes: number;
    shares: number;
    comments: number;
    views: number;
  } | null;
  created_at: string;
  updated_at: string;
}

interface FilterState {
  platform: string;
  status: string;
  timeframe: string;
}

const SocialMediaDashboard: React.FC = () => {
  // Filter state
  const [filters, setFilters] = useState<FilterState>({
    platform: '',
    status: '',
    timeframe: '7days',
  });
  
  // Fetch social media posts
  const { data: socialPosts, isLoading, isError, refetch } = useQuery({
    queryKey: ['socialPosts', filters],
    queryFn: async () => {
      const params: Record<string, any> = {};
      
      if (filters.platform) {
        params.platform = filters.platform;
      }
      
      if (filters.status) {
        params.status = filters.status;
      }
      
      if (filters.timeframe) {
        params.timeframe = filters.timeframe;
      }
      
      return await api.get('/social/posts', params);
    },
  });
  
  // Fetch social media stats
  const { data: socialStats, isLoading: statsLoading } = useQuery({
    queryKey: ['socialStats', filters.timeframe],
    queryFn: async () => {
      return await api.get('/social/stats', { timeframe: filters.timeframe });
    },
  });
  
  // Handle filter changes
  const handleFilterChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFilters((prev) => ({ ...prev, [name]: value }));
  };
  
  // Format date to readable format
  const formatDate = (dateString: string | null): string => {
    if (!dateString) return '--';
    
    const date = new Date(dateString);
    return date.toLocaleDateString('en-GB', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };
  
  // Get platform badge color
  const getPlatformBadgeClass = (platform: string): string => {
    switch (platform) {
      case 'twitter':
        return 'bg-blue-100 text-blue-800';
      case 'facebook':
        return 'bg-indigo-100 text-indigo-800';
      case 'instagram':
        return 'bg-pink-100 text-pink-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };
  
  // Get status badge color
  const getStatusBadgeClass = (status: string): string => {
    switch (status) {
      case 'draft':
        return 'bg-gray-100 text-gray-800';
      case 'scheduled':
        return 'bg-purple-100 text-purple-800';
      case 'published':
        return 'bg-green-100 text-green-800';
      case 'failed':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };
  
  // Format number with K, M suffix
  const formatNumber = (num: number): string => {
    if (num >= 1000000) {
      return (num / 1000000).toFixed(1) + 'M';
    } else if (num >= 1000) {
      return (num / 1000).toFixed(1) + 'K';
    }
    return num.toString();
  };
  
  // Get platform icon
  const getPlatformIcon = (platform: string): JSX.Element => {
    switch (platform) {
      case 'twitter':
        return (
          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
            <path d="M23.953 4.57a10 10 0 01-2.825.775 4.958 4.958 0 002.163-2.723c-.951.555-2.005.959-3.127 1.184a4.92 4.92 0 00-8.384 4.482C7.69 8.095 4.067 6.13 1.64 3.162a4.822 4.822 0 00-.666 2.475c0 1.71.87 3.213 2.188 4.096a4.904 4.904 0 01-2.228-.616v.06a4.923 4.923 0 003.946 4.827 4.996 4.996 0 01-2.212.085 4.936 4.936 0 004.604 3.417 9.867 9.867 0 01-6.102 2.105c-.39 0-.779-.023-1.17-.067a13.995 13.995 0 007.557 2.209c9.053 0 13.998-7.496 13.998-13.985 0-.21 0-.42-.015-.63A9.935 9.935 0 0024 4.59z" />
          </svg>
        );
      case 'facebook':
        return (
          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
            <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z" />
          </svg>
        );
      case 'instagram':
        return (
          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
            <path d="M12 0C8.74 0 8.333.015 7.053.072 5.775.132 4.905.333 4.14.63c-.789.306-1.459.717-2.126 1.384S.935 3.35.63 4.14C.333 4.905.131 5.775.072 7.053.012 8.333 0 8.74 0 12s.015 3.667.072 4.947c.06 1.277.261 2.148.558 2.913.306.788.717 1.459 1.384 2.126.667.666 1.336 1.079 2.126 1.384.766.296 1.636.499 2.913.558C8.333 23.988 8.74 24 12 24s3.667-.015 4.947-.072c1.277-.06 2.148-.262 2.913-.558.788-.306 1.459-.718 2.126-1.384.666-.667 1.079-1.335 1.384-2.126.296-.765.499-1.636.558-2.913.06-1.28.072-1.687.072-4.947s-.015-3.667-.072-4.947c-.06-1.277-.262-2.149-.558-2.913-.306-.789-.718-1.459-1.384-2.126C21.319 1.347 20.651.935 19.86.63c-.765-.297-1.636-.499-2.913-.558C15.667.012 15.26 0 12 0zm0 2.16c3.203 0 3.585.016 4.85.071 1.17.055 1.805.249 2.227.415.562.217.96.477 1.382.896.419.42.679.819.896 1.381.164.422.36 1.057.413 2.227.057 1.266.07 1.646.07 4.85s-.015 3.585-.074 4.85c-.061 1.17-.256 1.805-.421 2.227-.224.562-.479.96-.897 1.382-.419.419-.824.679-1.38.896-.42.164-1.065.36-2.235.413-1.274.057-1.649.07-4.859.07-3.211 0-3.586-.015-4.859-.074-1.171-.061-1.816-.256-2.236-.421-.569-.224-.96-.479-1.379-.897-.421-.419-.69-.824-.9-1.38-.165-.42-.359-1.065-.42-2.235-.045-1.26-.061-1.649-.061-4.844 0-3.196.016-3.586.061-4.861.061-1.17.255-1.814.42-2.234.21-.57.479-.96.9-1.381.419-.419.81-.689 1.379-.898.42-.166 1.051-.361 2.221-.421 1.275-.045 1.65-.06 4.859-.06l.045.03zm0 3.678c-3.405 0-6.162 2.76-6.162 6.162 0 3.405 2.76 6.162 6.162 6.162 3.405 0 6.162-2.76 6.162-6.162 0-3.405-2.76-6.162-6.162-6.162zM12 16c-2.21 0-4-1.79-4-4s1.79-4 4-4 4 1.79 4 4-1.79 4-4 4zm7.846-10.405c0 .795-.646 1.44-1.44 1.44-.795 0-1.44-.646-1.44-1.44 0-.794.646-1.439 1.44-1.439.793-.001 1.44.645 1.44 1.439z" />
          </svg>
        );
      default:
        return <span className="w-5 h-5"></span>;
    }
  };
  
  return (
    <MainLayout title="Social Media Dashboard | Parliament Video Clip Manager">
      <div className="page-container">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-3xl font-bold text-gray-900">Social Media Dashboard</h1>
          <Link href="/social/new">
            <span className="btn-primary rounded-md px-4 py-2 text-center cursor-pointer inline-block">
              Create New Post
            </span>
          </Link>
        </div>
        
        {/* Stats cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
          {statsLoading ? (
            Array(4).fill(0).map((_, index) => (
              <div key={index} className="bg-white rounded-lg shadow p-6 animate-pulse">
                <div className="h-4 bg-gray-200 rounded w-1/2 mb-2"></div>
                <div className="h-8 bg-gray-200 rounded w-1/4"></div>
              </div>
            ))
          ) : socialStats ? (
            <>
              <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-sm font-medium text-gray-500">Total Posts</h3>
                <p className="mt-2 text-3xl font-bold text-gray-900">{socialStats.total_posts || 0}</p>
                <div className="mt-2 text-sm text-gray-500">
                  {filters.timeframe === 'all' ? 'All time' : `Last ${filters.timeframe.replace('days', ' days')}`}
                </div>
              </div>
              
              <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-sm font-medium text-gray-500">Total Engagement</h3>
                <p className="mt-2 text-3xl font-bold text-gray-900">{formatNumber(socialStats.total_engagement || 0)}</p>
                <div className="mt-2 text-sm text-gray-500">
                  Likes, shares, comments
                </div>
              </div>
              
              <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-sm font-medium text-gray-500">Total Views</h3>
                <p className="mt-2 text-3xl font-bold text-gray-900">{formatNumber(socialStats.total_views || 0)}</p>
                <div className="mt-2 text-sm text-gray-500">
                  Across all platforms
                </div>
              </div>
              
              <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-sm font-medium text-gray-500">Scheduled Posts</h3>
                <p className="mt-2 text-3xl font-bold text-gray-900">{socialStats.scheduled_posts || 0}</p>
                <div className="mt-2 text-sm text-gray-500">
                  Pending publication
                </div>
              </div>
            </>
          ) : (
            <div className="col-span-4 bg-white rounded-lg shadow p-6">
              <p className="text-gray-500">Error loading statistics</p>
            </div>
          )}
        </div>
        
        {/* Filters */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <div className="flex flex-col md:flex-row md:items-end space-y-4 md:space-y-0 md:space-x-4">
            <div>
              <label htmlFor="platform" className="block text-sm font-medium text-gray-700 mb-1">
                Platform
              </label>
              <select
                id="platform"
                name="platform"
                value={filters.platform}
                onChange={handleFilterChange}
                className="form-input w-full md:w-40"
              >
                <option value="">All Platforms</option>
                <option value="twitter">Twitter</option>
                <option value="facebook">Facebook</option>
                <option value="instagram">Instagram</option>
              </select>
            </div>
            
            <div>
              <label htmlFor="status" className="block text-sm font-medium text-gray-700 mb-1">
                Status
              </label>
              <select
                id="status"
                name="status"
                value={filters.status}
                onChange={handleFilterChange}
                className="form-input w-full md:w-40"
              >
                <option value="">All Statuses</option>
                <option value="draft">Draft</option>
                <option value="scheduled">Scheduled</option>
                <option value="published">Published</option>
                <option value="failed">Failed</option>
              </select>
            </div>
            
            <div>
              <label htmlFor="timeframe" className="block text-sm font-medium text-gray-700 mb-1">
                Timeframe
              </label>
              <select
                id="timeframe"
                name="timeframe"
                value={filters.timeframe}
                onChange={handleFilterChange}
                className="form-input w-full md:w-40"
              >
                <option value="7days">Last 7 days</option>
                <option value="30days">Last 30 days</option>
                <option value="90days">Last 90 days</option>
                <option value="all">All time</option>
              </select>
            </div>
            
            <div>
              <button
                type="button"
                onClick={() => refetch()}
                className="w-full md:w-auto px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
              >
                Refresh
              </button>
            </div>
          </div>
        </div>
        
        {/* Social posts table */}
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-medium text-gray-800">Social Media Posts</h2>
          </div>
          
          <div className="overflow-x-auto">
            {isLoading ? (
              <div className="p-6 text-center text-gray-500">Loading social media posts...</div>
            ) : isError ? (
              <div className="p-6 text-center text-red-500">Error loading social media posts</div>
            ) : !socialPosts || socialPosts.length === 0 ? (
              <div className="p-6 text-center text-gray-500">
                No social media posts found. Create a new post to share your clips on social media.
              </div>
            ) : (
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Post
                    </th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Platform
                    </th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Status
                    </th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Scheduled/Published
                    </th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Engagement
                    </th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {socialPosts.map((post: SocialPost) => (
                    <tr key={post.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4">
                        <div className="flex items-center">
                          {post.clip?.thumbnail_url ? (
                            <img
                              src={post.clip.thumbnail_url}
                              alt={post.title}
                              className="h-10 w-16 object-cover rounded mr-3"
                            />
                          ) : (
                            <div className="h-10 w-16 bg-gray-200 rounded mr-3 flex items-center justify-center text-gray-500 text-xs">
                              No image
                            </div>
                          )}
                          <div>
                            <div className="text-sm font-medium text-gray-900">{post.title}</div>
                            <div className="text-sm text-gray-500 truncate max-w-xs">
                              {post.content.length > 50 ? post.content.substring(0, 50) + '...' : post.content}
                            </div>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className={`flex items-center px-2 py-1 rounded-full ${getPlatformBadgeClass(post.platform)}`}>
                          <span className="mr-1.5">{getPlatformIcon(post.platform)}</span>
                          <span className="text-xs font-medium capitalize">
                            {post.platform}
                          </span>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${getStatusBadgeClass(post.status)}`}>
                          {post.status.charAt(0).toUpperCase() + post.status.slice(1)}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-500">
                          {post.status === 'scheduled'
                            ? formatDate(post.scheduled_time)
                            : post.status === 'published'
                            ? formatDate(post.published_time)
                            : '--'}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        {post.engagement ? (
                          <div className="flex space-x-3 text-sm text-gray-500">
                            <span title="Likes">{formatNumber(post.engagement.likes)} 👍</span>
                            <span title="Shares">{formatNumber(post.engagement.shares)} 🔄</span>
                            <span title="Comments">{formatNumber(post.engagement.comments)} 💬</span>
                          </div>
                        ) : (
                          <span className="text-sm text-gray-500">--</span>
                        )}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                        <Link href={`/social/${post.id}`}>
                          <span className="text-primary hover:text-primary-dark mr-3 cursor-pointer">
                            View
                          </span>
                        </Link>
                        {post.status === 'draft' && (
                          <Link href={`/social/${post.id}/edit`}>
                            <span className="text-primary hover:text-primary-dark cursor-pointer">
                              Edit
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

export default withAuth(SocialMediaDashboard, [UserRole.ADMIN, UserRole.MP, UserRole.STAFF]);
