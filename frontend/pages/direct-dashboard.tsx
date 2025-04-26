import React, { useEffect, useState } from 'react';
import Head from 'next/head';

interface DashboardStats {
  totalClips: number;
  recentClips: number;
  pendingCaptures: number;
  scheduledPosts: number;
  storageUsed: string;
  storageTotal: string;
}

const DirectDashboard: React.FC = () => {
  const [stats, setStats] = useState<DashboardStats>({
    totalClips: 0,
    recentClips: 0,
    pendingCaptures: 0,
    scheduledPosts: 0,
    storageUsed: '0 GB',
    storageTotal: '0 GB'
  });
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [token, setToken] = useState<string | null>(null);

  useEffect(() => {
    // Get token from localStorage or sessionStorage
    const storedToken = localStorage.getItem('token') || sessionStorage.getItem('token');
    setToken(storedToken);
    
    if (!storedToken) {
      setError('No authentication token found. Please login first.');
      setIsLoading(false);
      return;
    }
    
    // Fetch dashboard stats
    const fetchStats = async () => {
      try {
        console.log('Fetching dashboard stats with token:', storedToken ? 'Present' : 'None');
        
        const response = await fetch('http://localhost:8000/api/v1/dashboard/stats', {
          method: 'GET',
          headers: {
            'Authorization': `Bearer ${storedToken}`,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
          }
        });
        
        console.log('Dashboard stats response status:', response.status);
        
        if (!response.ok) {
          if (response.status === 401) {
            throw new Error('Authentication token expired or invalid. Please login again.');
          }
          throw new Error(`Failed to fetch dashboard stats: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('Dashboard stats fetched successfully:', data);
        setStats(data);
      } catch (error: any) {
        console.error('Error fetching dashboard stats:', error);
        setError(error.message || 'Failed to load dashboard data');
      } finally {
        setIsLoading(false);
      }
    };
    
    fetchStats();
  }, []);
  
  const handleLogout = () => {
    localStorage.removeItem('token');
    sessionStorage.removeItem('token');
    window.location.href = '/direct-login';
  };

  return (
    <>
      <Head>
        <title>Direct Dashboard | Parliament Video Clip Manager</title>
        <style>{`
          body {
            background-color: #1f2937;
            color: white;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            margin: 0;
            padding: 0;
          }
          .container {
            min-height: 100vh;
            display: flex;
            flex-direction: column;
          }
          .header {
            background-color: #111827;
            padding: 1rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
          }
          .title {
            font-size: 1.25rem;
            font-weight: 600;
          }
          .header-actions {
            display: flex;
            gap: 0.5rem;
          }
          .dashboard-button {
            background-color: #3b82f6;
            color: white;
            border: none;
            border-radius: 0.375rem;
            padding: 0.5rem 1rem;
            font-size: 0.875rem;
            cursor: pointer;
          }
          .dashboard-button:hover {
            background-color: #2563eb;
          }
          .logout-button {
            background-color: #ef4444;
            color: white;
            border: none;
            border-radius: 0.375rem;
            padding: 0.5rem 1rem;
            font-size: 0.875rem;
            cursor: pointer;
          }
          .logout-button:hover {
            background-color: #dc2626;
          }
          .main {
            padding: 2rem;
            flex: 1;
          }
          .page-title {
            font-size: 1.875rem;
            font-weight: 700;
            margin-bottom: 1rem;
          }
          .info-banner {
            background-color: rgba(59, 130, 246, 0.1);
            border: 1px solid #3b82f6;
            color: #60a5fa;
            padding: 0.75rem 1rem;
            border-radius: 0.375rem;
            margin-bottom: 1.5rem;
          }
          .info-banner p {
            margin: 0.5rem 0;
          }
          .error {
            background-color: rgba(220, 38, 38, 0.1);
            border: 1px solid #ef4444;
            color: #f87171;
            padding: 0.75rem 1rem;
            border-radius: 0.375rem;
            margin-bottom: 1.5rem;
          }
          .loading {
            display: flex;
            justify-content: center;
            align-items: center;
            height: 200px;
            font-size: 1.125rem;
            color: #9ca3af;
          }
          .stats-grid {
            display: grid;
            grid-template-columns: repeat(1, minmax(0, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
          }
          @media (min-width: 640px) {
            .stats-grid {
              grid-template-columns: repeat(2, minmax(0, 1fr));
            }
          }
          @media (min-width: 1024px) {
            .stats-grid {
              grid-template-columns: repeat(4, minmax(0, 1fr));
            }
          }
          .stat-card {
            background-color: #111827;
            border-radius: 0.5rem;
            padding: 1.5rem;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
          }
          .stat-header {
            display: flex;
            align-items: center;
            margin-bottom: 1rem;
          }
          .stat-icon {
            width: 2.5rem;
            height: 2.5rem;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 9999px;
            margin-right: 1rem;
          }
          .icon-clips {
            background-color: rgba(59, 130, 246, 0.2);
            color: #60a5fa;
          }
          .icon-recent {
            background-color: rgba(16, 185, 129, 0.2);
            color: #34d399;
          }
          .icon-pending {
            background-color: rgba(245, 158, 11, 0.2);
            color: #fbbf24;
          }
          .icon-scheduled {
            background-color: rgba(139, 92, 246, 0.2);
            color: #a78bfa;
          }
          .stat-label {
            font-size: 0.875rem;
            color: #9ca3af;
          }
          .stat-value {
            font-size: 1.5rem;
            font-weight: 600;
          }
          .storage-card {
            background-color: #111827;
            border-radius: 0.5rem;
            padding: 1.5rem;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
          }
          .storage-title {
            font-size: 1.125rem;
            font-weight: 600;
            margin-bottom: 1rem;
          }
          .storage-item {
            display: flex;
            justify-content: space-between;
            margin-bottom: 0.5rem;
          }
          .storage-label {
            color: #9ca3af;
          }
          .storage-bar {
            height: 0.5rem;
            background-color: #374151;
            border-radius: 9999px;
            margin-top: 1rem;
            overflow: hidden;
          }
          .storage-progress {
            height: 100%;
            background-color: #3b82f6;
            border-radius: 9999px;
          }
          .token-section {
            margin-top: 2rem;
            background-color: #111827;
            border-radius: 0.5rem;
            padding: 1.5rem;
          }
          .token-title {
            font-size: 1.125rem;
            font-weight: 600;
            margin-bottom: 1rem;
          }
          .token-display {
            background-color: #374151;
            border-radius: 0.375rem;
            padding: 1rem;
            font-family: monospace;
            font-size: 0.75rem;
            word-break: break-all;
          }
        `}</style>
      </Head>

      <div className="container">
        <header className="header">
          <div className="title">Parliament Video Clip Manager</div>
          <div className="header-actions">
            <button className="dashboard-button" onClick={() => window.location.href = '/dashboard'}>Try Regular Dashboard</button>
            <button className="logout-button" onClick={handleLogout}>Logout</button>
          </div>
        </header>

        <main className="main">
          <h1 className="page-title">Direct Dashboard (No Auth Provider)</h1>
          <div className="info-banner">
            <p>This dashboard bypasses the AuthContext completely and uses direct token authentication.</p>
            <p>If you're seeing this page, it means your login was successful and the token is valid.</p>
          </div>
          
          {error && (
            <div className="error">{error}</div>
          )}
          
          {isLoading ? (
            <div className="loading">Loading dashboard data...</div>
          ) : (
            <>
              <div className="stats-grid">
                <div className="stat-card">
                  <div className="stat-header">
                    <div className="stat-icon icon-clips">
                      <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"></path>
                      </svg>
                    </div>
                    <div>
                      <div className="stat-label">Total Clips</div>
                      <div className="stat-value">{stats.totalClips}</div>
                    </div>
                  </div>
                </div>
                
                <div className="stat-card">
                  <div className="stat-header">
                    <div className="stat-icon icon-recent">
                      <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                      </svg>
                    </div>
                    <div>
                      <div className="stat-label">Recent Clips</div>
                      <div className="stat-value">{stats.recentClips}</div>
                    </div>
                  </div>
                </div>
                
                <div className="stat-card">
                  <div className="stat-header">
                    <div className="stat-icon icon-pending">
                      <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"></path>
                      </svg>
                    </div>
                    <div>
                      <div className="stat-label">Pending Captures</div>
                      <div className="stat-value">{stats.pendingCaptures}</div>
                    </div>
                  </div>
                </div>
                
                <div className="stat-card">
                  <div className="stat-header">
                    <div className="stat-icon icon-scheduled">
                      <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"></path>
                      </svg>
                    </div>
                    <div>
                      <div className="stat-label">Scheduled Posts</div>
                      <div className="stat-value">{stats.scheduledPosts}</div>
                    </div>
                  </div>
                </div>
              </div>
              
              <div className="storage-card">
                <h3 className="storage-title">Storage Usage</h3>
                <div className="storage-item">
                  <span className="storage-label">Used:</span>
                  <span>{stats.storageUsed}</span>
                </div>
                <div className="storage-item">
                  <span className="storage-label">Total:</span>
                  <span>{stats.storageTotal}</span>
                </div>
                <div className="storage-bar">
                  <div 
                    className="storage-progress" 
                    style={{ 
                      width: `${(parseFloat(stats.storageUsed) / parseFloat(stats.storageTotal)) * 100}%` 
                    }}
                  ></div>
                </div>
              </div>
              
              {token && (
                <div className="token-section">
                  <h3 className="token-title">Authentication Token</h3>
                  <div className="token-display">{token}</div>
                </div>
              )}
            </>
          )}
        </main>
      </div>
    </>
  );
};

// Define the correct type for Next.js pages with getInitialProps
interface PageWithNoAuthProps {
  noAuth: boolean;
}

// This ensures the page is rendered without the global AuthProvider
export async function getStaticProps() {
  return {
    props: {
      noAuth: true
    }
  };
}

export default DirectDashboard;
