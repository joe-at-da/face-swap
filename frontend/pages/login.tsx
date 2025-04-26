import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import Head from 'next/head';
import Image from 'next/image';
import { useTheme } from '../contexts/ThemeContext';
import ThemeToggle from '../components/common/ThemeToggle';

const Login: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const { theme } = useTheme();
  const router = useRouter();
  
  // Force dark mode class on body when component mounts
  useEffect(() => {
    // This ensures the body has the correct classes even if ThemeContext hasn't fully initialized
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
      document.body.style.backgroundColor = '#111827';
      document.body.style.color = '#ffffff';
    }
    
    // Check if user is already authenticated
    const token = localStorage.getItem('token') || sessionStorage.getItem('token');
    if (token) {
      console.log('User already has token, redirecting to direct-dashboard');
      router.push('/direct-dashboard');
    }
  }, [theme, router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      // Create form data for OAuth2 login
      const formData = new URLSearchParams();
      formData.append('username', email); // OAuth2 expects 'username' even though we're using email
      formData.append('password', password);
      
      console.log('Attempting direct login from login page');
      
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
      
      if (!response.ok) {
        const errorText = await response.text();
        let errorDetail = 'Unknown error';
        
        try {
          // Try to parse as JSON
          const errorData = JSON.parse(errorText);
          errorDetail = errorData.detail || `Login failed: ${response.status}`;
        } catch (parseError) {
          // If not JSON, use the raw text
          errorDetail = errorText || `Login failed: ${response.status}`;
        }
        
        throw new Error(errorDetail);
      }
      
      const data = await response.json();
      console.log('Login successful, received token');
      
      // Store token in both localStorage and sessionStorage
      localStorage.setItem('token', data.access_token);
      sessionStorage.setItem('token', data.access_token);
      
      // Redirect to regular dashboard on successful login
      router.push('/dashboard');
    } catch (err: any) {
      setError(err.message || 'Failed to login. Please check your credentials.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <>
      <Head>
        <title>Login | Parliament Video Clip Manager</title>
        <meta name="description" content="Login to the Parliament Video Clip Manager" />
      </Head>

      <div className="min-h-screen flex flex-col justify-center py-12 sm:px-6 lg:px-8 bg-gray-900 dark:bg-gray-900 text-white dark:text-white transition-colors duration-200">
        <div className="absolute top-4 right-4">
          <ThemeToggle />
        </div>
        <div className="sm:mx-auto sm:w-full sm:max-w-md">
          <div className="flex justify-center">
            <Image
              src="/logo.svg"
              alt="Parliament Video Clip Manager"
              width={80}
              height={80}
            />
          </div>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900 dark:text-white">
            Parliament Video Clip Manager
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600 dark:text-gray-300">
            Sign in to your account
          </p>
        </div>

        <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
          <div className="py-8 px-4 shadow sm:rounded-lg sm:px-10 bg-gray-800 border border-gray-700 transition-colors duration-200">
            {error && (
              <div className="mb-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 px-4 py-3 rounded relative" role="alert">
                <span className="block sm:inline">{error}</span>
              </div>
            )}

            <form className="space-y-6" onSubmit={handleSubmit}>
              <div>
                <label htmlFor="email" className="block text-sm font-medium text-gray-700 dark:text-gray-200">
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
                    className="appearance-none block w-full px-3 py-2 rounded-md shadow-sm sm:text-sm border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-primary focus:border-primary transition-colors duration-200"
                  />
                </div>
              </div>

              <div>
                <label htmlFor="password" className="block text-sm font-medium text-gray-700 dark:text-gray-200">
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
                    className="appearance-none block w-full px-3 py-2 rounded-md shadow-sm sm:text-sm border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-primary focus:border-primary transition-colors duration-200"
                  />
                </div>
              </div>

              <div className="flex items-center justify-between">
                <div className="flex items-center">
                  <input
                    id="remember_me"
                    name="remember_me"
                    type="checkbox"
                    className="h-4 w-4 text-primary dark:text-blue-500 focus:ring-primary dark:focus:ring-blue-500 rounded border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700"
                  />
                  <label htmlFor="remember_me" className="ml-2 block text-sm text-gray-600 dark:text-gray-300">
                    Remember me
                  </label>
                </div>

                <div className="text-sm">
                  <a href="#" className="font-medium text-primary dark:text-blue-400 hover:text-primary-dark dark:hover:text-blue-300">
                    Forgot your password?
                  </a>
                </div>
              </div>

              <div>
                <button
                  type="submit"
                  disabled={isLoading}
                  className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary hover:bg-primary-dark focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary dark:focus:ring-blue-500 disabled:opacity-50 transition-colors duration-200"
                >
                  {isLoading ? 'Signing in...' : 'Sign in'}
                </button>
              </div>
            </form>

            <div className="mt-6">
              <div className="relative">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-gray-200 dark:border-gray-700" />
                </div>
                <div className="relative flex justify-center text-sm">
                  <span className="px-2 text-sm bg-white dark:bg-gray-800 text-gray-500 dark:text-gray-400">Parliament Video Clip Manager</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
};

export default Login;
