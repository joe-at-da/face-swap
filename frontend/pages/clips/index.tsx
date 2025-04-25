import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useRouter } from 'next/router';
import Link from 'next/link';
import MainLayout from '../../components/layout/MainLayout';
import { withAuth } from '../../contexts/AuthContext';
import { api } from '../../utils/api';

interface VideoClip {
  id: number;
  title: string;
  description: string;
  duration: number;
  file_path: string;
  thumbnail_url: string;
  created_at: string;
  updated_at: string;
  created_by_id: number;
  has_transcription: boolean;
  status: string;
}

interface VideoClipsResponse {
  items: VideoClip[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

const VideoClipsPage: React.FC = () => {
  const router = useRouter();
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [searchTerm, setSearchTerm] = useState('');
  const [sortBy, setSortBy] = useState('created_at:desc');
  const [filterStatus, setFilterStatus] = useState('');

  // Fetch video clips
  const { data, isLoading, isError, refetch } = useQuery<VideoClipsResponse>({
    queryKey: ['videoClips', page, pageSize, searchTerm, sortBy, filterStatus],
    queryFn: async () => {
      const params: Record<string, any> = {
        page,
        size: pageSize,
        sort: sortBy,
      };

      if (searchTerm) {
        params.search = searchTerm;
      }

      if (filterStatus) {
        params.status = filterStatus;
      }

      return await api.get('/clips', params);
    },
  });

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

  // Handle search
  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1); // Reset to first page when searching
    refetch();
  };

  // Handle sort change
  const handleSortChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setSortBy(e.target.value);
    setPage(1); // Reset to first page when changing sort
  };

  // Handle filter change
  const handleFilterChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setFilterStatus(e.target.value);
    setPage(1); // Reset to first page when changing filter
  };

  // Handle pagination
  const handlePageChange = (newPage: number) => {
    setPage(newPage);
  };

  // Generate pagination buttons
  const renderPagination = () => {
    if (!data) return null;

    const { page: currentPage, pages: totalPages } = data;
    const pageButtons = [];

    // Previous button
    pageButtons.push(
      <button
        key="prev"
        onClick={() => handlePageChange(currentPage - 1)}
        disabled={currentPage === 1}
        className="relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        Previous
      </button>
    );

    // Page numbers
    const startPage = Math.max(1, currentPage - 2);
    const endPage = Math.min(totalPages, startPage + 4);

    for (let i = startPage; i <= endPage; i++) {
      pageButtons.push(
        <button
          key={i}
          onClick={() => handlePageChange(i)}
          className={`relative inline-flex items-center px-4 py-2 border text-sm font-medium rounded-md ${
            i === currentPage
              ? 'z-10 bg-primary text-white border-primary'
              : 'border-gray-300 text-gray-700 bg-white hover:bg-gray-50'
          }`}
        >
          {i}
        </button>
      );
    }

    // Next button
    pageButtons.push(
      <button
        key="next"
        onClick={() => handlePageChange(currentPage + 1)}
        disabled={currentPage === totalPages}
        className="relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        Next
      </button>
    );

    return (
      <div className="flex justify-between items-center mt-4">
        <div className="text-sm text-gray-700">
          Showing <span className="font-medium">{(currentPage - 1) * pageSize + 1}</span> to{' '}
          <span className="font-medium">
            {Math.min(currentPage * pageSize, data.total)}
          </span>{' '}
          of <span className="font-medium">{data.total}</span> results
        </div>
        <div className="flex space-x-2">{pageButtons}</div>
      </div>
    );
  };

  return (
    <MainLayout title="Video Clips | Parliament Video Clip Manager">
      <div className="page-container">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-3xl font-bold text-gray-900">Video Clips</h1>
          <Link href="/clips/new">
            <span className="btn-primary rounded-md px-4 py-2 text-center cursor-pointer inline-block">
              Create New Clip
            </span>
          </Link>
        </div>

        {/* Filters and Search */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <div className="flex flex-col md:flex-row md:items-end space-y-4 md:space-y-0 md:space-x-4">
            <div className="flex-1">
              <form onSubmit={handleSearch}>
                <label htmlFor="search" className="block text-sm font-medium text-gray-700 mb-1">
                  Search
                </label>
                <div className="flex">
                  <input
                    type="text"
                    id="search"
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    placeholder="Search by title or description"
                    className="form-input rounded-l-md"
                  />
                  <button
                    type="submit"
                    className="bg-primary text-white px-4 py-2 rounded-r-md hover:bg-primary-dark"
                  >
                    Search
                  </button>
                </div>
              </form>
            </div>

            <div className="w-full md:w-48">
              <label htmlFor="status" className="block text-sm font-medium text-gray-700 mb-1">
                Status
              </label>
              <select
                id="status"
                value={filterStatus}
                onChange={handleFilterChange}
                className="form-input"
              >
                <option value="">All Statuses</option>
                <option value="ready">Ready</option>
                <option value="processing">Processing</option>
                <option value="error">Error</option>
              </select>
            </div>

            <div className="w-full md:w-48">
              <label htmlFor="sort" className="block text-sm font-medium text-gray-700 mb-1">
                Sort By
              </label>
              <select
                id="sort"
                value={sortBy}
                onChange={handleSortChange}
                className="form-input"
              >
                <option value="created_at:desc">Newest First</option>
                <option value="created_at:asc">Oldest First</option>
                <option value="title:asc">Title (A-Z)</option>
                <option value="title:desc">Title (Z-A)</option>
                <option value="duration:desc">Longest First</option>
                <option value="duration:asc">Shortest First</option>
              </select>
            </div>

            <div className="w-full md:w-32">
              <label htmlFor="pageSize" className="block text-sm font-medium text-gray-700 mb-1">
                Per Page
              </label>
              <select
                id="pageSize"
                value={pageSize}
                onChange={(e) => {
                  setPageSize(Number(e.target.value));
                  setPage(1); // Reset to first page when changing page size
                }}
                className="form-input"
              >
                <option value="10">10</option>
                <option value="25">25</option>
                <option value="50">50</option>
                <option value="100">100</option>
              </select>
            </div>
          </div>
        </div>

        {/* Video Clips Table */}
        <div className="bg-white rounded-lg shadow overflow-hidden">
          {isLoading ? (
            <div className="p-6 text-center text-gray-500">Loading video clips...</div>
          ) : isError ? (
            <div className="p-6 text-center text-red-500">Error loading video clips</div>
          ) : data?.items.length === 0 ? (
            <div className="p-6 text-center text-gray-500">
              No video clips found. Try adjusting your search or filters.
            </div>
          ) : (
            <>
              <div className="overflow-x-auto">
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
                        Status
                      </th>
                      <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Actions
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {data?.items.map((clip) => (
                      <tr key={clip.id} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="w-24 h-14 bg-gray-200 rounded overflow-hidden">
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
                        <td className="px-6 py-4">
                          <div className="text-sm font-medium text-gray-900">{clip.title}</div>
                          <div className="text-sm text-gray-500 truncate max-w-xs">{clip.description}</div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm text-gray-500">{formatDuration(clip.duration)}</div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm text-gray-500">{formatDate(clip.created_at)}</div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                            clip.status === 'ready'
                              ? 'bg-green-100 text-green-800'
                              : clip.status === 'processing'
                              ? 'bg-yellow-100 text-yellow-800'
                              : 'bg-red-100 text-red-800'
                          }`}>
                            {clip.status.charAt(0).toUpperCase() + clip.status.slice(1)}
                          </span>
                          {clip.has_transcription && (
                            <span className="ml-2 px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-blue-100 text-blue-800">
                              Transcribed
                            </span>
                          )}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                          <Link href={`/clips/${clip.id}`}>
                            <span className="text-primary hover:text-primary-dark mr-3 cursor-pointer">
                              View
                            </span>
                          </Link>
                          <Link href={`/clips/${clip.id}/edit`}>
                            <span className="text-primary hover:text-primary-dark mr-3 cursor-pointer">
                              Edit
                            </span>
                          </Link>
                          <Link href={`/social/new?clipId=${clip.id}`}>
                            <span className="text-primary hover:text-primary-dark cursor-pointer">
                              Share
                            </span>
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {renderPagination()}
            </>
          )}
        </div>
      </div>
    </MainLayout>
  );
};

export default withAuth(VideoClipsPage);
