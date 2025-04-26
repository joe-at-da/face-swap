import React, { useEffect, useState } from 'react';
import Head from 'next/head';
import { useRouter } from 'next/router';
import { api } from '../utils/api';

interface LogEntry {
  timestamp: string;
  message: string;
  type: 'info' | 'success' | 'error' | 'warning';
}

const AuthDebug: React.FC = () => {
  const router = useRouter();
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [token, setToken] = useState<string | null>(null);
  const [userData, setUserData] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  // Add a log entry
  const addLog = (message: string, type: 'info' | 'success' | 'error' | 'warning' = 'info') => {
    const timestamp = new Date().toISOString().substring(11, 23);
    setLogs(prevLogs => [...prevLogs, { timestamp, message, type }]);
  };

  // Check authentication status
  useEffect(() => {
    const checkAuth = async () => {
      // Get token from storage
      const localStorageToken = localStorage.getItem('token');
      const sessionStorageToken = sessionStorage.getItem('token');
      const storedToken = localStorageToken || sessionStorageToken;
      
      addLog(`Checking authentication status...`, 'info');
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
    };
    
    checkAuth();
  }, []);
  
  // Handle direct login
  const handleDirectLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    const email = (document.getElementById('email') as HTMLInputElement).value;
    const password = (document.getElementById('password') as HTMLInputElement).value;
    
    addLog(`Attempting direct login for: ${email}`, 'info');
    
    try {
      // Create form data for OAuth2 login
      const formData = new URLSearchParams();
      formData.append('username', email);
      formData.append('password', password);
      
      addLog(`Making login request to API...`, 'info');
      
      const response = await fetch('http://localhost:8000/api/v1/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'Accept': 'application/json',
        },
        body: formData,
        credentials: 'same-origin',
      });
      
      addLog(`Login response status: ${response.status}`, response.ok ? 'success' : 'error');
      
      if (!response.ok) {
        const errorText = await response.text();
        let errorDetail = 'Unknown error';
        
        try {
          const errorData = JSON.parse(errorText);
          errorDetail = errorData.detail || `Login failed: ${response.status}`;
        } catch (parseError) {
          errorDetail = errorText || `Login failed: ${response.status}`;
        }
        
        addLog(`Login error: ${errorDetail}`, 'error');
        setError(errorDetail);
        return;
      }
      
      const data = await response.json();
      addLog(`Login successful, received token`, 'success');
      
      // Store token
      localStorage.setItem('token', data.access_token);
      sessionStorage.setItem('token', data.access_token);
      setToken(data.access_token);
      
      // Set auth flags
      sessionStorage.setItem('isAuthenticated', 'true');
      sessionStorage.setItem('justLoggedIn', 'true');
      
      addLog(`Token stored in localStorage and sessionStorage`, 'success');
      addLog(`Auth flags set in sessionStorage`, 'success');
      
      // Refresh the page to show the new auth status
      window.location.reload();
    } catch (err: any) {
      addLog(`Login error: ${err.message}`, 'error');
      setError(err.message);
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
  
  // Get log entry color
  const getLogColor = (type: string) => {
    switch (type) {
      case 'success': return 'text-green-500';
      case 'error': return 'text-red-500';
      case 'warning': return 'text-yellow-500';
      default: return 'text-blue-500';
    }
  };

  return (
    <>
      <Head>
        <title>Auth Debug | Parliament Video Clip Manager</title>
        <style>{`
          body {
            background-color: #1f2937;
            color: white;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
          }
        `}</style>
      </Head>

      <div className="container mx-auto p-6">
        <h1 className="text-2xl font-bold mb-6">Authentication Debug Page</h1>
        
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div>
            <div className="bg-gray-800 rounded-lg p-6 mb-6">
              <h2 className="text-xl font-semibold mb-4">Authentication Status</h2>
              
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
            </div>
            
            <div className="bg-gray-800 rounded-lg p-6">
              <h2 className="text-xl font-semibold mb-4">Actions</h2>
              
              <form onSubmit={handleDirectLogin} className="mb-6">
                <h3 className="font-semibold mb-2">Direct Login</h3>
                <div className="mb-4">
                  <label htmlFor="email" className="block text-sm mb-1">Email</label>
                  <input 
                    type="email" 
                    id="email" 
                    className="w-full p-2 rounded bg-gray-700 text-white" 
                    defaultValue="admin@parliament.uk"
                  />
                </div>
                <div className="mb-4">
                  <label htmlFor="password" className="block text-sm mb-1">Password</label>
                  <input 
                    type="password" 
                    id="password" 
                    className="w-full p-2 rounded bg-gray-700 text-white" 
                    defaultValue="admin123"
                  />
                </div>
                <button 
                  type="submit" 
                  className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded"
                >
                  Login
                </button>
              </form>
              
              <div>
                <h3 className="font-semibold mb-2">Clear Authentication</h3>
                <button 
                  onClick={handleClearAuth}
                  className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded"
                >
                  Clear All Tokens & Flags
                </button>
              </div>
            </div>
          </div>
          
          <div className="bg-gray-800 rounded-lg p-6">
            <h2 className="text-xl font-semibold mb-4">Authentication Logs</h2>
            
            <div className="bg-gray-900 p-4 rounded h-[500px] overflow-y-auto font-mono text-sm">
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
            
            <div className="mt-4 flex justify-between">
              <button 
                onClick={() => setLogs([])}
                className="bg-gray-700 hover:bg-gray-600 text-white px-3 py-1 rounded text-sm"
              >
                Clear Logs
              </button>
              
              <div className="flex gap-2">
                <button 
                  onClick={() => router.push('/direct-dashboard')}
                  className="bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded text-sm"
                >
                  Go to Direct Dashboard
                </button>
                <button 
                  onClick={() => router.push('/dashboard')}
                  className="bg-purple-600 hover:bg-purple-700 text-white px-3 py-1 rounded text-sm"
                >
                  Try Regular Dashboard
                </button>
              </div>
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

export default AuthDebug;
