import React, { useEffect, useState } from 'react';
import Head from 'next/head';
import { useRouter } from 'next/router';

interface DashboardStats {
  totalClips: number;
  recentClips: number;
  pendingCaptures: number;
  scheduledPosts: number;
  storageUsed: string;
  storageTotal: string;
}

const SimpleDashboard: React.FC = () => {
  const router = useRouter();
  const [stats, setStats] = useState<DashboardStats>({
    totalClips: 5,
    recentClips: 3,
    pendingCaptures: 1,
    scheduledPosts: 2,
    storageUsed: '2.4 GB',
    storageTotal: '100 GB'
  });
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    // Check if user is authenticated
    const token = localStorage.getItem('token') || sessionStorage.getItem('token');
    
    if (!token) {
      console.log('No token found, redirecting to simple login');
      router.push('/simple-login');
      return;
    }
    
    // Fetch dashboard stats
    const fetchStats = async () => {
      try {
        const response = await fetch('http://localhost:8000/api/v1/dashboard/stats', {
          method: 'GET',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
          }
        });
        
        if (!response.ok) {
          if (response.status === 401) {
            console.log('Token expired, redirecting to login');
            localStorage.removeItem('token');
            sessionStorage.removeItem('token');
            router.push('/simple-login');
            return;
          }
          
          throw new Error(`Failed to fetch stats: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('Dashboard stats:', data);
        setStats(data);
      } catch (error) {
        console.error('Error fetching dashboard stats:', error);
        setError('Failed to load dashboard data. Using placeholder data.');
        // Keep using the default stats
      } finally {
        setIsLoading(false);
      }
    };
    
    fetchStats();
  }, [router]);
  
  const handleLogout = () => {
    localStorage.removeItem('token');
    sessionStorage.removeItem('token');
    sessionStorage.removeItem('isAuthenticated');
    router.push('/simple-login');
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-900 text-white">
        <div className="text-2xl">Loading dashboard...</div>
      </div>
    );
  }

  return (
    <>
      <Head>
        <title>Simple Dashboard | Parliament Video Clip Manager</title>
      </Head>

      <div className="min-h-screen bg-gray-900 text-white">
        <header className="bg-gray-800 shadow-md">
          <div className="max-w-7xl mx-auto px-4 py-4 sm:px-6 lg:px-8 flex justify-between items-center">
            <h1 className="text-2xl font-bold">Parliament Video Clip Manager</h1>
            <button
              onClick={handleLogout}
              className="px-4 py-2 bg-red-600 hover:bg-red-700 rounded-md text-white"
            >
              Logout
            </button>
          </div>
        </header>

        <main className="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
          <div className="mb-6">
            <h2 className="text-3xl font-bold mb-6">Dashboard</h2>
            
            {error && (
              <div className="mb-4 bg-red-900/20 border border-red-800 text-red-400 px-4 py-3 rounded relative">
                {error}
              </div>
            )}

            {/* Stats Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
              <div className="bg-gray-800 rounded-lg shadow p-6 border border-gray-700">
                <div className="flex items-center">
                  <div className="p-3 rounded-full bg-blue-900 text-blue-300 mr-4">
                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"></path>
                    </svg>
                  </div>
                  <div>
                    <div className="text-sm font-medium text-gray-400">Total Clips</div>
                    <div className="text-2xl font-semibold">{stats.totalClips}</div>
                  </div>
                </div>
              </div>

              <div className="bg-gray-800 rounded-lg shadow p-6 border border-gray-700">
                <div className="flex items-center">
                  <div className="p-3 rounded-full bg-green-900 text-green-300 mr-4">
                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                    </svg>
                  </div>
                  <div>
                    <div className="text-sm font-medium text-gray-400">Recent Clips</div>
                    <div className="text-2xl font-semibold">{stats.recentClips}</div>
                  </div>
                </div>
              </div>

              <div className="bg-gray-800 rounded-lg shadow p-6 border border-gray-700">
                <div className="flex items-center">
                  <div className="p-3 rounded-full bg-yellow-900 text-yellow-300 mr-4">
                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"></path>
                    </svg>
                  </div>
                  <div>
                    <div className="text-sm font-medium text-gray-400">Pending Captures</div>
                    <div className="text-2xl font-semibold">{stats.pendingCaptures}</div>
                  </div>
                </div>
              </div>

              <div className="bg-gray-800 rounded-lg shadow p-6 border border-gray-700">
                <div className="flex items-center">
                  <div className="p-3 rounded-full bg-purple-900 text-purple-300 mr-4">
                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"></path>
                    </svg>
                  </div>
                  <div>
                    <div className="text-sm font-medium text-gray-400">Scheduled Posts</div>
                    <div className="text-2xl font-semibold">{stats.scheduledPosts}</div>
                  </div>
                </div>
              </div>
            </div>

            {/* Storage Card */}
            <div className="bg-gray-800 rounded-lg shadow p-6 border border-gray-700 mb-8">
              <h3 className="text-xl font-semibold mb-4">Storage Usage</h3>
              <div className="flex items-center mb-2">
                <div className="text-sm font-medium text-gray-400 w-32">Used:</div>
                <div className="text-lg font-semibold">{stats.storageUsed}</div>
              </div>
              <div className="flex items-center mb-4">
                <div className="text-sm font-medium text-gray-400 w-32">Total:</div>
                <div className="text-lg font-semibold">{stats.storageTotal}</div>
              </div>
              <div className="w-full bg-gray-700 rounded-full h-4">
                <div
                  className="bg-blue-600 h-4 rounded-full"
                  style={{
                    width: `${(parseFloat(stats.storageUsed) / parseFloat(stats.storageTotal)) * 100}%`,
                  }}
                ></div>
              </div>
            </div>
          </div>
        </main>
      </div>
    </>
  );
};

export default SimpleDashboard;
