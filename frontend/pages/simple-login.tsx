import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import Head from 'next/head';

const SimpleLogin: React.FC = () => {
  // Prevent redirects from middleware
  useEffect(() => {
    // Clear any redirect flags
    sessionStorage.removeItem('redirectUrl');
    sessionStorage.removeItem('isRedirecting');
    
    // Clear any auth context flags that might cause redirects
    sessionStorage.removeItem('isAuthenticated');
    sessionStorage.removeItem('isAuthenticating');
    sessionStorage.removeItem('authChecked');
    
    console.log('Simple login page loaded, cleared redirect flags');
  }, []);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      // Create form data for OAuth2 login
      const formData = new URLSearchParams();
      formData.append('username', email);
      formData.append('password', password);
      
      console.log('Attempting login with simple form');
      
      // Make the login request directly
      const response = await fetch('http://localhost:8000/api/v1/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'Accept': 'application/json',
        },
        body: formData,
        credentials: 'same-origin',
      });
      
      console.log('Login response status:', response.status);
      
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(errorText || `Login failed: ${response.status}`);
      }
      
      const data = await response.json();
      console.log('Login successful, received token');
      
      // Store token in localStorage
      localStorage.setItem('token', data.access_token);
      
      // Store token in sessionStorage as well for redundancy
      sessionStorage.setItem('token', data.access_token);
      
      // Set auth flags
      sessionStorage.setItem('isAuthenticated', 'true');
      
      // Redirect to dashboard
      console.log('Redirecting to dashboard');
      router.push('/dashboard');
    } catch (error: any) {
      console.error('Login failed:', error.message || error);
      setError(error.message || 'Failed to login. Please check your credentials.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <>
      <Head>
        <title>Simple Login | Parliament Video Clip Manager</title>
      </Head>

      <div className="min-h-screen flex flex-col justify-center py-12 sm:px-6 lg:px-8 bg-gray-900 text-white">
        <div className="sm:mx-auto sm:w-full sm:max-w-md">
          <h2 className="mt-6 text-center text-3xl font-extrabold">
            Parliament Video Clip Manager
          </h2>
          <p className="mt-2 text-center text-sm text-gray-300">
            Simple Login Page
          </p>
        </div>

        <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
          <div className="py-8 px-4 shadow sm:rounded-lg sm:px-10 bg-gray-800 border border-gray-700">
            {error && (
              <div className="mb-4 bg-red-900/20 border border-red-800 text-red-400 px-4 py-3 rounded relative" role="alert">
                <span className="block sm:inline">{error}</span>
              </div>
            )}

            <form className="space-y-6" onSubmit={handleSubmit}>
              <div>
                <label htmlFor="email" className="block text-sm font-medium text-gray-200">
                  Email address
                </label>
                <div className="mt-1">
                  <input
                    id="email"
                    name="email"
                    type="email"
                    autoComplete="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="appearance-none block w-full px-3 py-2 rounded-md shadow-sm sm:text-sm border border-gray-600 bg-gray-700 text-white focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
              </div>

              <div>
                <label htmlFor="password" className="block text-sm font-medium text-gray-200">
                  Password
                </label>
                <div className="mt-1">
                  <input
                    id="password"
                    name="password"
                    type="password"
                    autoComplete="current-password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="appearance-none block w-full px-3 py-2 rounded-md shadow-sm sm:text-sm border border-gray-600 bg-gray-700 text-white focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
              </div>

              <div>
                <button
                  type="submit"
                  disabled={isLoading}
                  className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
                >
                  {isLoading ? 'Signing in...' : 'Sign in'}
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </>
  );
};

export default SimpleLogin;
