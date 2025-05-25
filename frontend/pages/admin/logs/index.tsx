import React, { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { withAuth } from '../../../contexts/AuthContext';
import { UserRole } from '../../../contexts/AuthContext';
import DarkLayout from '../../../components/layout/DarkLayout';
import { Card, Button } from '../../../components/ui';
import { api } from '../../../utils/api';

interface LogEntry {
  id: number;
  timestamp: string;
  level: 'info' | 'warning' | 'error';
  message: string;
  source: string;
  user_id?: number;
  user_email?: string;
}

const SystemLogsPage: React.FC = () => {
  const [page, setPage] = useState(1);
  const [logLevel, setLogLevel] = useState<string>('all');
  const pageSize = 20;

  // Define the type for the logs response
  interface LogsResponse {
    items: LogEntry[];
    total: number;
  }

  // Fetch real logs from the API
  const {
    data: logsData,
    isLoading,
    isError,
    error,
    refetch
  } = useQuery<LogEntry[]>({
    queryKey: ['systemLogs', page, logLevel],
    queryFn: async () => {
      const params = new URLSearchParams({
        lines: String(pageSize * 5), // Fetch more logs to allow for filtering
      });
      
      if (logLevel !== 'all') {
        params.append('level', logLevel);
      }
      
      try {
        // Add debug logging
        console.log('Fetching logs with params:', params.toString());
        
        const response = await api.get(`/system/logs?${params.toString()}`);
        console.log('Raw logs response:', response);
        
        // Handle different response formats
        let logsArray: any[] = [];
        
        if (Array.isArray(response)) {
          logsArray = response;
        } else if (response && typeof response === 'object') {
          // Check if response has an items property that is an array
          if (Array.isArray(response.items)) {
            logsArray = response.items;
          } else {
            // Try to convert object to array if possible
            const possibleArray = Object.values(response);
            if (Array.isArray(possibleArray) && possibleArray.length > 0) {
              logsArray = possibleArray;
            }
          }
        }
        
        console.log('Processed logs array:', logsArray);
        
        if (!logsArray || logsArray.length === 0) {
          console.warn('No logs found in response');
          return [];
        }
        
        // Add unique IDs to logs if they don't have them
        return logsArray.map((log: any, index: number) => ({
          ...log,
          id: log.id || index + 1,
          level: log.level || 'info', // Ensure level is defined
          timestamp: log.timestamp || new Date().toISOString() // Ensure timestamp is defined
        }));
      } catch (error) {
        console.error('Error fetching logs:', error);
        throw error;
      }
    },
    staleTime: 30000, // Consider data fresh for 30 seconds
    refetchInterval: 30000, // Refresh every 30 seconds
    retry: 2, // Retry failed requests twice
  });
  
  // Process logs for pagination
  const filteredLogs = logsData || [];
  const totalLogs = filteredLogs.length;
  const paginatedLogs = filteredLogs.slice((page - 1) * pageSize, page * pageSize);
  const logs = { items: paginatedLogs, total: totalLogs };

  const totalPages = Math.ceil(logs.total / pageSize) || 1;

  const handlePrevPage = () => {
    setPage((prev) => Math.max(prev - 1, 1));
  };

  const handleNextPage = () => {
    setPage((prev) => Math.min(prev + 1, totalPages));
  };

  const getLevelBadgeColor = (level: string) => {
    switch (level) {
      case 'info':
        return 'bg-blue-100 text-blue-800';
      case 'warning':
        return 'bg-yellow-100 text-yellow-800';
      case 'error':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString();
  };

  return (
    <DarkLayout title="System Logs | Parliament Video Clip Manager">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-6 flex justify-between items-center">
          <h1 className="text-3xl font-bold text-white">System Logs</h1>
          <div className="flex space-x-4">
            <select
              value={logLevel}
              onChange={(e) => setLogLevel(e.target.value)}
              className="bg-gray-700 border border-gray-600 text-white rounded-md px-4 py-2"
            >
              <option value="all">All Levels</option>
              <option value="info">Info</option>
              <option value="warning">Warning</option>
              <option value="error">Error</option>
            </select>
            <Button onClick={() => refetch()} variant="primary">
              Refresh
            </Button>
          </div>
        </div>

        <Card className="overflow-hidden">
          {isLoading ? (
            <div className="text-center py-8">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
              <p className="mt-4 text-gray-300">Loading logs...</p>
            </div>
          ) : isError ? (
            <div className="bg-gray-800 border border-red-600 text-red-400 px-4 py-3 rounded relative mb-4" role="alert">
              <div className="flex items-center mb-2">
                <svg className="h-6 w-6 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <strong className="font-bold text-lg">Error Loading Logs</strong>
              </div>
              <p className="block sm:inline mb-2">Failed to load system logs. This could be due to:</p>
              <ul className="list-disc ml-6 mb-2">
                <li>Docker services not running properly</li>
                <li>Backend API connectivity issues</li>
                <li>Log files not being accessible</li>
              </ul>
              <p className="text-sm">Check the browser console for more details.</p>
              <div className="mt-4">
                <button 
                  onClick={() => refetch()} 
                  className="bg-red-800 hover:bg-red-700 text-white px-4 py-2 rounded mr-2"
                >
                  Retry
                </button>
              </div>
            </div>
          ) : logs?.items.length === 0 ? (
            <div className="text-center py-8 text-gray-300">
              <svg className="mx-auto h-12 w-12 text-gray-400 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <h3 className="text-lg font-medium text-white mb-2">No logs found</h3>
              <p className="mb-2">There are no system logs matching your current filters.</p>
              {logLevel !== 'all' && (
                <p className="mb-4">Try changing the log level filter to see more results.</p>
              )}
              <button 
                onClick={() => {
                  setLogLevel('all');
                  setPage(1);
                  refetch();
                }}
                className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded"
              >
                View All Logs
              </button>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-700">
                <thead className="bg-gray-800">
                  <tr>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                      Timestamp
                    </th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                      Level
                    </th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                      Source
                    </th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                      User
                    </th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                      Message
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-gray-700 divide-y divide-gray-600">
                  {logs?.items.map((log) => (
                    <tr key={log.id}>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">
                        {formatDate(log.timestamp)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${getLevelBadgeColor(log.level)}`}>
                          {log.level}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">
                        {log.source}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">
                        {log.user_email || 'System'}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-300">
                        <div className="max-w-lg break-words">{log.message}</div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>

        {logs && logs.total > 0 && (
          <div className="mt-4 flex justify-between items-center">
            <div className="text-sm text-gray-300">
              Showing {(page - 1) * pageSize + 1} to {Math.min(page * pageSize, logs.total)} of {logs.total} logs
            </div>
            <div className="flex space-x-2">
              <Button
                onClick={handlePrevPage}
                disabled={page === 1}
                variant="secondary"
              >
                Previous
              </Button>
              <Button
                onClick={handleNextPage}
                disabled={page === totalPages}
                variant="secondary"
              >
                Next
              </Button>
            </div>
          </div>
        )}
      </div>
    </DarkLayout>
  );
};

export default withAuth(SystemLogsPage, [UserRole.ADMIN]);
