import React, { useEffect, useState, useRef } from 'react';
import Head from 'next/head';
import { useRouter } from 'next/router';
import Link from 'next/link';
import { api } from '../utils/api';

interface LogEntry {
  timestamp: string;
  message: string;
  type: 'info' | 'success' | 'error' | 'warning';
}

const DashboardDebug: React.FC = () => {
  const router = useRouter();
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [token, setToken] = useState<string | null>(null);
  const [userData, setUserData] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [redirectBlocked, setRedirectBlocked] = useState<boolean>(false);
  const logContainerRef = useRef<HTMLDivElement>(null);

  // Add a log entry
  const addLog = (message: string, type: 'info' | 'success' | 'error' | 'warning' = 'info') => {
    const timestamp = new Date().toISOString().substring(11, 23);
    setLogs(prevLogs => [...prevLogs, { timestamp, message, type }]);
    
    // Auto-scroll to bottom of logs
    setTimeout(() => {
      if (logContainerRef.current) {
        logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
      }
    }, 100);
  };

  // Override console methods to capture logs
  useEffect(() => {
    const originalConsoleLog = console.log;
    const originalConsoleError = console.error;
    const originalConsoleWarn = console.warn;
    
    console.log = (...args) => {
      originalConsoleLog(...args);
      addLog(args.map(arg => typeof arg === 'object' ? JSON.stringify(arg) : arg).join(' '), 'info');
    };
    
    console.error = (...args) => {
      originalConsoleError(...args);
      addLog(args.map(arg => typeof arg === 'object' ? JSON.stringify(arg) : arg).join(' '), 'error');
    };
    
    console.warn = (...args) => {
      originalConsoleWarn(...args);
      addLog(args.map(arg => typeof arg === 'object' ? JSON.stringify(arg) : arg).join(' '), 'warning');
    };
    
    // Override router.push to log and optionally block redirects
    const originalPush = router.push;
    router.push = (url, as, options) => {
      console.log(`Router redirect attempted to: ${url}`);
      
      if (redirectBlocked) {
        console.warn(`Redirect to ${url} was blocked`);
        return Promise.resolve(false);
      }
      
      return originalPush(url, as, options);
    };
    
    return () => {
      console.log = originalConsoleLog;
      console.error = originalConsoleError;
      console.warn = originalConsoleWarn;
      router.push = originalPush;
    };
  }, [redirectBlocked, router]);

  // Check authentication status
  useEffect(() => {
    const checkAuth = async () => {
      addLog('Starting authentication check...', 'info');
      
      // Get token from storage
      const localStorageToken = localStorage.getItem('token');
      const sessionStorageToken = sessionStorage.getItem('token');
      const storedToken = localStorageToken || sessionStorageToken;
      
      addLog(`Local storage token: ${localStorageToken ? 'Present' : 'None'}`, 'info');
      addLog(`Session storage token: ${sessionStorageToken ? 'Present' : 'None'}`, 'info');
      
      if (storedToken) {
        setToken(storedToken);
        addLog(`Token found, length: ${storedToken.length}`, 'success');
        
        // Try to validate token
        try {
          addLog(`Setting token in API client...`, 'info');
          api.setAuthToken(storedToken);
          
          addLog(`Fetching user data with token...`, 'info');
          const userData = await api.get('/auth/me');
          
          addLog(`User data fetched successfully: ${userData.email}`, 'success');
          setUserData(userData);
        } catch (error: any) {
          addLog(`Error fetching user data: ${error.message}`, 'error');
          setError(error.message);
        }
      } else {
        addLog(`No token found in storage`, 'warning');
      }
      
      // Check session storage flags
      const isLoggingIn = sessionStorage.getItem('loggingIn') === 'true';
      const justLoggedIn = sessionStorage.getItem('justLoggedIn') === 'true';
      const isRedirecting = sessionStorage.getItem('redirecting') === 'true';
      const isAuthenticated = sessionStorage.getItem('isAuthenticated') === 'true';
      
      addLog(`Session flags:`, 'info');
      addLog(`- isLoggingIn: ${isLoggingIn}`, isLoggingIn ? 'warning' : 'info');
      addLog(`- justLoggedIn: ${justLoggedIn}`, justLoggedIn ? 'success' : 'info');
      addLog(`- isRedirecting: ${isRedirecting}`, isRedirecting ? 'warning' : 'info');
      addLog(`- isAuthenticated: ${isAuthenticated}`, isAuthenticated ? 'success' : 'info');
      
      // Check AuthContext initialization
      addLog('Simulating AuthContext initialization...', 'info');
      
      try {
        // This simulates what happens in the AuthContext's initAuth function
        if (storedToken) {
          addLog('Found stored token, attempting to validate...', 'info');
          
          try {
            const userData = await api.get('/auth/me');
            addLog(`User authenticated successfully: ${userData.email}`, 'success');
          } catch (apiError: any) {
            addLog(`API error when fetching user data: ${apiError.message}`, 'error');
            throw apiError;
          }
        } else {
          addLog('No stored token found', 'warning');
        }
      } catch (error: any) {
        addLog(`Failed to authenticate with stored token: ${error.message}`, 'error');
      }
    };
    
    checkAuth();
  }, []);
  
  // Get log entry color
  const getLogColor = (type: string) => {
    switch (type) {
      case 'success': return 'text-green-500';
      case 'error': return 'text-red-500';
      case 'warning': return 'text-yellow-500';
      default: return 'text-blue-500';
    }
  };

  // Clear all tokens and flags
  const handleClearAuth = () => {
    localStorage.removeItem('token');
    sessionStorage.removeItem('token');
    sessionStorage.removeItem('isAuthenticated');
    sessionStorage.removeItem('justLoggedIn');
    sessionStorage.removeItem('loggingIn');
    sessionStorage.removeItem('redirecting');
    sessionStorage.removeItem('authSuccess');
    
    addLog(`Cleared all tokens and auth flags`, 'warning');
    setToken(null);
    setUserData(null);
    
    // Refresh the page
    window.location.reload();
  };
  
  // Toggle redirect blocking
  const toggleRedirectBlocking = () => {
    setRedirectBlocked(!redirectBlocked);
    addLog(`Redirect blocking ${!redirectBlocked ? 'enabled' : 'disabled'}`, !redirectBlocked ? 'success' : 'warning');
  };

  return (
    <>
      <Head>
        <title>Dashboard Debug | Parliament Video Clip Manager</title>
        <style>{`
          body {
            background-color: #1f2937;
            color: white;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
          }
        `}</style>
      </Head>

      <div className="container mx-auto p-6">
        <h1 className="text-2xl font-bold mb-6">Dashboard Debug Page</h1>
        
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div>
            <div className="bg-gray-800 rounded-lg p-6 mb-6">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-xl font-semibold">Authentication Status</h2>
                <div className="flex gap-2">
                  <button 
                    onClick={toggleRedirectBlocking}
                    className={`px-3 py-1 rounded text-sm ${redirectBlocked ? 'bg-green-600 hover:bg-green-700' : 'bg-gray-600 hover:bg-gray-700'}`}
                  >
                    {redirectBlocked ? 'Redirects Blocked' : 'Redirects Allowed'}
                  </button>
                </div>
              </div>
              
              {token ? (
                <div className="bg-green-900 p-4 rounded mb-4">
                  <p className="font-semibold text-green-400">Authenticated</p>
                  <p className="text-sm mt-2">Token found in storage</p>
                </div>
              ) : (
                <div className="bg-red-900 p-4 rounded mb-4">
                  <p className="font-semibold text-red-400">Not Authenticated</p>
                  <p className="text-sm mt-2">No token found in storage</p>
                </div>
              )}
              
              {userData && (
                <div className="bg-gray-700 p-4 rounded mb-4">
                  <h3 className="font-semibold mb-2">User Data</h3>
                  <p>Email: {userData.email}</p>
                  <p>Role: {userData.role}</p>
                </div>
              )}
              
              {token && (
                <div className="mt-4">
                  <h3 className="font-semibold mb-2">Token</h3>
                  <div className="bg-gray-900 p-2 rounded text-xs font-mono break-all">
                    {token}
                  </div>
                </div>
              )}
              
              {error && (
                <div className="mt-4 bg-red-900/30 p-4 rounded">
                  <h3 className="font-semibold mb-2 text-red-400">Error</h3>
                  <p>{error}</p>
                </div>
              )}
            </div>
            
            <div className="bg-gray-800 rounded-lg p-6">
              <h2 className="text-xl font-semibold mb-4">Actions</h2>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                <Link 
                  href="/direct-dashboard"
                  className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded text-center"
                >
                  Go to Direct Dashboard
                </Link>
                
                <Link 
                  href="/dashboard"
                  className="bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded text-center"
                >
                  Try Regular Dashboard
                </Link>
              </div>
              
              <div className="space-y-4">
                <div>
                  <h3 className="font-semibold mb-2">Fix Authentication</h3>
                  <button 
                    onClick={() => {
                      sessionStorage.setItem('isAuthenticated', 'true');
                      addLog('Fixed isAuthenticated flag: set to true', 'success');
                      window.location.reload();
                    }}
                    className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded w-full"
                  >
                    Fix isAuthenticated Flag
                  </button>
                </div>
                
                <div>
                  <h3 className="font-semibold mb-2">Clear Authentication</h3>
                  <button 
                    onClick={handleClearAuth}
                    className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded w-full"
                  >
                    Clear All Tokens & Flags
                  </button>
                </div>
              </div>
            </div>
          </div>
          
          <div className="bg-gray-800 rounded-lg p-6">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-semibold">Authentication Logs</h2>
              <button 
                onClick={() => setLogs([])}
                className="bg-gray-700 hover:bg-gray-600 text-white px-3 py-1 rounded text-sm"
              >
                Clear Logs
              </button>
            </div>
            
            <div 
              ref={logContainerRef}
              className="bg-gray-900 p-4 rounded h-[600px] overflow-y-auto font-mono text-sm"
            >
              {logs.length === 0 ? (
                <p className="text-gray-500">No logs yet...</p>
              ) : (
                logs.map((log, index) => (
                  <div key={index} className="mb-1">
                    <span className="text-gray-500">[{log.timestamp}]</span>{' '}
                    <span className={getLogColor(log.type)}>{log.message}</span>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </>
  );
};

// Ensure this page doesn't use the AuthContext
export async function getStaticProps() {
  return {
    props: {
      noAuth: true
    }
  };
}

export default DashboardDebug;
