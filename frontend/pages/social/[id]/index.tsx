import React, { useState } from 'react';
import { useRouter } from 'next/router';
import { useQuery, useMutation } from '@tanstack/react-query';
import Link from 'next/link';
import MainLayout from '../../../components/layout/MainLayout';
import { withAuth } from '../../../contexts/AuthContext';
import { UserRole } from '../../../contexts/AuthContext';
import { api } from '../../../utils/api';

interface SocialPost {
  id: number;
  title: string;
  content: string;
  platform: 'twitter' | 'facebook' | 'instagram';
  status: 'draft' | 'scheduled' | 'published' | 'failed';
  scheduled_time: string | null;
  published_time: string | null;
  external_url: string | null;
  clip_id: number;
  clip: {
    id: number;
    title: string;
    thumbnail_url: string | null;
    file_url: string;
    duration: number;
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
    last_updated: string;
  } | null;
  created_at: string;
  updated_at: string;
}

const SocialPostDetailPage: React.FC = () => {
  const router = useRouter();
  const { id } = router.query;
  
  // Fetch social post details
  const { data: post, isLoading, isError, refetch } = useQuery({
    queryKey: ['socialPost', id],
    queryFn: async () => {
      if (!id) return null;
      return await api.get(`/social/posts/${id}`);
    },
    enabled: !!id,
  });
  
  // Publish now mutation
  const publishMutation = useMutation({
    mutationFn: async (postId: number) => {
      return await api.post(`/social/posts/${postId}/publish`);
    },
    onSuccess: () => {
      refetch();
    },
  });
  
  // Delete post mutation
  const deleteMutation = useMutation({
    mutationFn: async (postId: number) => {
      return await api.delete(`/social/posts/${postId}`);
    },
    onSuccess: () => {
      router.push('/social');
    },
  });
  
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
  
  // Format number with K, M suffix
  const formatNumber = (num: number): string => {
    if (num >= 1000000) {
      return (num / 1000000).toFixed(1) + 'M';
    } else if (num >= 1000) {
      return (num / 1000).toFixed(1) + 'K';
    }
    return num.toString();
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
  
  // Handle publish now
  const handlePublishNow = () => {
    if (!post) return;
    
    if (confirm('Are you sure you want to publish this post now?')) {
      publishMutation.mutate(post.id);
    }
  };
  
  // Handle delete post
  const handleDeletePost = () => {
    if (!post) return;
    
    if (confirm('Are you sure you want to delete this post? This action cannot be undone.')) {
      deleteMutation.mutate(post.id);
    }
  };
  
  if (isLoading) {
    return (
      <MainLayout title="Social Media Post | Parliament Video Clip Manager">
        <div className="page-container">
          <div className="flex justify-center items-center h-64">
            <div className="text-gray-500">Loading post details...</div>
          </div>
        </div>
      </MainLayout>
    );
  }
  
  if (isError || !post) {
    return (
      <MainLayout title="Social Media Post | Parliament Video Clip Manager">
        <div className="page-container">
          <div className="bg-red-50 border-l-4 border-red-500 p-4">
            <div className="flex">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
              </div>
              <div className="ml-3">
                <p className="text-sm text-red-700">Error loading post details. The post may not exist or you don't have permission to view it.</p>
              </div>
            </div>
          </div>
          <div className="mt-4">
            <Link href="/social">
              <span className="text-primary hover:text-primary-dark cursor-pointer">
                Back to Social Media Dashboard
              </span>
            </Link>
          </div>
        </div>
      </MainLayout>
    );
  }
  
  return (
    <MainLayout title={`${post.title} | Social Media Post | Parliament Video Clip Manager`}>
      <div className="page-container">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:justify-between md:items-center mb-6 space-y-4 md:space-y-0">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">{post.title}</h1>
            <div className="flex items-center mt-2">
              <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${getPlatformBadgeClass(post.platform)}`}>
                <span className="mr-1">{getPlatformIcon(post.platform)}</span>
                <span className="capitalize">{post.platform}</span>
              </span>
              <span className={`ml-2 px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${getStatusBadgeClass(post.status)}`}>
                {post.status.charAt(0).toUpperCase() + post.status.slice(1)}
              </span>
            </div>
          </div>
          
          <div className="flex space-x-3">
            {post.status === 'draft' && (
              <>
                <Link href={`/social/${post.id}/edit`}>
                  <span className="px-3 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 cursor-pointer inline-block">
                    Edit
                  </span>
                </Link>
                <button
                  type="button"
                  onClick={handlePublishNow}
                  disabled={publishMutation.isPending}
                  className="px-3 py-2 border border-primary rounded-md text-sm font-medium text-primary bg-white hover:bg-primary-50 disabled:opacity-50"
                >
                  {publishMutation.isPending ? 'Publishing...' : 'Publish Now'}
                </button>
              </>
            )}
            
            {post.status === 'scheduled' && (
              <>
                <Link href={`/social/${post.id}/edit`}>
                  <span className="px-3 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 cursor-pointer inline-block">
                    Edit
                  </span>
                </Link>
                <button
                  type="button"
                  onClick={handlePublishNow}
                  disabled={publishMutation.isPending}
                  className="px-3 py-2 border border-primary rounded-md text-sm font-medium text-primary bg-white hover:bg-primary-50 disabled:opacity-50"
                >
                  {publishMutation.isPending ? 'Publishing...' : 'Publish Now'}
                </button>
              </>
            )}
            
            {post.status === 'published' && post.external_url && (
              <a
                href={post.external_url}
                target="_blank"
                rel="noopener noreferrer"
                className="px-3 py-2 border border-primary rounded-md text-sm font-medium text-primary bg-white hover:bg-primary-50"
              >
                View on {post.platform.charAt(0).toUpperCase() + post.platform.slice(1)}
              </a>
            )}
            
            <Link href="/social">
              <span className="px-3 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 cursor-pointer inline-block">
                Back
              </span>
            </Link>
            
            <button
              type="button"
              onClick={handleDeletePost}
              disabled={deleteMutation.isPending}
              className="px-3 py-2 border border-red-300 rounded-md text-sm font-medium text-red-700 bg-white hover:bg-red-50 disabled:opacity-50"
            >
              {deleteMutation.isPending ? 'Deleting...' : 'Delete'}
            </button>
          </div>
        </div>
        
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left column - Post details */}
          <div className="lg:col-span-2">
            <div className="bg-white rounded-lg shadow overflow-hidden mb-6">
              <div className="px-6 py-4 border-b border-gray-200">
                <h2 className="text-lg font-medium text-gray-800">Post Details</h2>
              </div>
              
              <div className="p-6">
                {/* Post content */}
                <div className="mb-6">
                  <h3 className="text-sm font-medium text-gray-500 mb-2">Content</h3>
                  <div className="p-4 bg-gray-50 rounded-lg">
                    <p className="text-gray-900 whitespace-pre-line">{post.content}</p>
                  </div>
                </div>
                
                {/* Post metadata */}
                <dl className="grid grid-cols-1 md:grid-cols-2 gap-x-4 gap-y-6">
                  <div>
                    <dt className="text-sm font-medium text-gray-500">Status</dt>
                    <dd className="mt-1 text-sm text-gray-900">
                      <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${getStatusBadgeClass(post.status)}`}>
                        {post.status.charAt(0).toUpperCase() + post.status.slice(1)}
                      </span>
                    </dd>
                  </div>
                  
                  <div>
                    <dt className="text-sm font-medium text-gray-500">Platform</dt>
                    <dd className="mt-1 text-sm text-gray-900">
                      <span className={`flex items-center px-2 py-1 rounded-full w-fit ${getPlatformBadgeClass(post.platform)}`}>
                        <span className="mr-1.5">{getPlatformIcon(post.platform)}</span>
                        <span className="capitalize">{post.platform}</span>
                      </span>
                    </dd>
                  </div>
                  
                  <div>
                    <dt className="text-sm font-medium text-gray-500">Created</dt>
                    <dd className="mt-1 text-sm text-gray-900">{formatDate(post.created_at)}</dd>
                  </div>
                  
                  <div>
                    <dt className="text-sm font-medium text-gray-500">Created By</dt>
                    <dd className="mt-1 text-sm text-gray-900">{post.created_by?.name || 'Unknown'}</dd>
                  </div>
                  
                  {post.status === 'scheduled' && (
                    <div>
                      <dt className="text-sm font-medium text-gray-500">Scheduled For</dt>
                      <dd className="mt-1 text-sm text-gray-900">{formatDate(post.scheduled_time)}</dd>
                    </div>
                  )}
                  
                  {post.status === 'published' && (
                    <div>
                      <dt className="text-sm font-medium text-gray-500">Published</dt>
                      <dd className="mt-1 text-sm text-gray-900">{formatDate(post.published_time)}</dd>
                    </div>
                  )}
                  
                  {post.external_url && (
                    <div className="md:col-span-2">
                      <dt className="text-sm font-medium text-gray-500">External URL</dt>
                      <dd className="mt-1 text-sm text-gray-900">
                        <a
                          href={post.external_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-primary hover:text-primary-dark break-all"
                        >
                          {post.external_url}
                        </a>
                      </dd>
                    </div>
                  )}
                </dl>
              </div>
            </div>
            
            {/* Video clip details */}
            <div className="bg-white rounded-lg shadow overflow-hidden mb-6">
              <div className="px-6 py-4 border-b border-gray-200">
                <h2 className="text-lg font-medium text-gray-800">Video Clip</h2>
              </div>
              
              <div className="aspect-w-16 aspect-h-9 bg-black">
                <video
                  src={post.clip.file_url}
                  controls
                  poster={post.clip.thumbnail_url || undefined}
                  className="w-full h-full object-contain"
                />
              </div>
              
              <div className="p-6">
                <h3 className="text-lg font-medium text-gray-900">{post.clip.title}</h3>
                <div className="mt-2 flex items-center text-sm text-gray-500">
                  <span>Duration: {Math.floor(post.clip.duration / 60)}:{(post.clip.duration % 60).toString().padStart(2, '0')}</span>
                </div>
                <div className="mt-4">
                  <Link href={`/clips/${post.clip_id}`}>
                    <span className="text-primary hover:text-primary-dark cursor-pointer">
                      View Clip Details
                    </span>
                  </Link>
                </div>
              </div>
            </div>
          </div>
          
          {/* Right column - Engagement */}
          <div>
            {post.status === 'published' && post.engagement ? (
              <div className="bg-white rounded-lg shadow overflow-hidden sticky top-6">
                <div className="px-6 py-4 border-b border-gray-200">
                  <h2 className="text-lg font-medium text-gray-800">Engagement</h2>
                </div>
                
                <div className="p-6">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="bg-blue-50 rounded-lg p-4 text-center">
                      <div className="text-3xl font-bold text-blue-600">{formatNumber(post.engagement.views)}</div>
                      <div className="mt-1 text-sm text-blue-800">Views</div>
                    </div>
                    
                    <div className="bg-green-50 rounded-lg p-4 text-center">
                      <div className="text-3xl font-bold text-green-600">{formatNumber(post.engagement.likes)}</div>
                      <div className="mt-1 text-sm text-green-800">Likes</div>
                    </div>
                    
                    <div className="bg-purple-50 rounded-lg p-4 text-center">
                      <div className="text-3xl font-bold text-purple-600">{formatNumber(post.engagement.shares)}</div>
                      <div className="mt-1 text-sm text-purple-800">Shares</div>
                    </div>
                    
                    <div className="bg-yellow-50 rounded-lg p-4 text-center">
                      <div className="text-3xl font-bold text-yellow-600">{formatNumber(post.engagement.comments)}</div>
                      <div className="mt-1 text-sm text-yellow-800">Comments</div>
                    </div>
                  </div>
                  
                  <div className="mt-4 text-xs text-gray-500 text-center">
                    Last updated: {formatDate(post.engagement.last_updated)}
                  </div>
                  
                  <div className="mt-6 p-4 bg-gray-50 rounded-lg">
                    <h3 className="text-sm font-medium text-gray-700 mb-2">Engagement Rate</h3>
                    <div className="relative pt-1">
                      <div className="flex mb-2 items-center justify-between">
                        <div>
                          <span className="text-xs font-semibold inline-block text-primary">
                            {post.engagement.views > 0
                              ? (((post.engagement.likes + post.engagement.shares + post.engagement.comments) / post.engagement.views) * 100).toFixed(2)
                              : '0.00'}%
                          </span>
                        </div>
                      </div>
                      <div className="overflow-hidden h-2 mb-4 text-xs flex rounded bg-primary-100">
                        <div
                          style={{
                            width: post.engagement.views > 0
                              ? `${Math.min(((post.engagement.likes + post.engagement.shares + post.engagement.comments) / post.engagement.views) * 100, 100)}%`
                              : '0%'
                          }}
                          className="shadow-none flex flex-col text-center whitespace-nowrap text-white justify-center bg-primary"
                        ></div>
                      </div>
                    </div>
                    <p className="text-xs text-gray-500">
                      Engagement rate is calculated as (likes + shares + comments) / views
                    </p>
                  </div>
                </div>
              </div>
            ) : (
              <div className="bg-white rounded-lg shadow overflow-hidden">
                <div className="px-6 py-4 border-b border-gray-200">
                  <h2 className="text-lg font-medium text-gray-800">Engagement</h2>
                </div>
                
                <div className="p-6 text-center">
                  {post.status === 'published' ? (
                    <div className="text-gray-500">
                      <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                      </svg>
                      <p className="mt-2">No engagement data available yet</p>
                      <p className="mt-1 text-sm">Engagement data will be available after the post has been published for some time</p>
                    </div>
                  ) : (
                    <div className="text-gray-500">
                      <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      <p className="mt-2">Post not published yet</p>
                      <p className="mt-1 text-sm">Engagement data will be available after the post is published</p>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </MainLayout>
  );
};

export default withAuth(SocialPostDetailPage, [UserRole.ADMIN, UserRole.MP, UserRole.STAFF]);
