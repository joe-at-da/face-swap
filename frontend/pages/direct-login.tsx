import React, { useState } from 'react';
import Head from 'next/head';

const DirectLogin: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [token, setToken] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      // Create form data for OAuth2 login
      const formData = new URLSearchParams();
      formData.append('username', email);
      formData.append('password', password);
      
      console.log('Attempting direct login');
      
      // Make the login request directly
      const response = await fetch('http://localhost:8000/api/v1/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'Accept': 'application/json',
        },
        body: formData,
      });
      
      console.log('Login response status:', response.status);
      
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(errorText || `Login failed: ${response.status}`);
      }
      
      const data = await response.json();
      console.log('Login successful, received token');
      
      // Store token in state to display
      setToken(data.access_token);
      setIsSuccess(true);
      
      // Store token in localStorage
      localStorage.setItem('token', data.access_token);
      
      // Store token in sessionStorage as well for redundancy
      sessionStorage.setItem('token', data.access_token);
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
        <title>Direct Login | Parliament Video Clip Manager</title>
        <style>{`
          body {
            background-color: #1f2937;
            color: white;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
          }
          .container {
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            justify-content: center;
            padding: 3rem 1.5rem;
          }
          .card {
            background-color: #111827;
            border-radius: 0.5rem;
            padding: 2rem;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            max-width: 28rem;
            margin: 0 auto;
            width: 100%;
          }
          .title {
            font-size: 1.875rem;
            font-weight: 800;
            text-align: center;
            margin-bottom: 1.5rem;
          }
          .subtitle {
            font-size: 0.875rem;
            text-align: center;
            color: #9ca3af;
            margin-bottom: 2rem;
          }
          .form-group {
            margin-bottom: 1.5rem;
          }
          .label {
            display: block;
            font-size: 0.875rem;
            font-weight: 500;
            margin-bottom: 0.5rem;
            color: #d1d5db;
          }
          .input {
            width: 100%;
            padding: 0.5rem 0.75rem;
            border-radius: 0.375rem;
            border: 1px solid #4b5563;
            background-color: #374151;
            color: white;
            font-size: 0.875rem;
          }
          .button {
            width: 100%;
            padding: 0.5rem 1rem;
            background-color: #2563eb;
            color: white;
            border: none;
            border-radius: 0.375rem;
            font-weight: 500;
            cursor: pointer;
            font-size: 0.875rem;
          }
          .button:hover {
            background-color: #1d4ed8;
          }
          .button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
          }
          .error {
            background-color: rgba(220, 38, 38, 0.1);
            border: 1px solid #ef4444;
            color: #f87171;
            padding: 0.75rem 1rem;
            border-radius: 0.375rem;
            margin-bottom: 1.5rem;
          }
          .success {
            background-color: rgba(5, 150, 105, 0.1);
            border: 1px solid #10b981;
            color: #34d399;
            padding: 0.75rem 1rem;
            border-radius: 0.375rem;
            margin-bottom: 1.5rem;
          }
          .token-display {
            background-color: #374151;
            border-radius: 0.375rem;
            padding: 1rem;
            font-family: monospace;
            font-size: 0.75rem;
            word-break: break-all;
            margin-top: 1rem;
          }
        `}</style>
      </Head>

      <div className="container">
        <div className="card">
          <h1 className="title">Parliament Video Clip Manager</h1>
          <p className="subtitle">Direct Login Page (No Auth Provider)</p>
          
          {error && (
            <div className="error">{error}</div>
          )}
          
          {isSuccess && (
            <div className="success">
              <p>Login successful! Token received:</p>
              <div className="token-display">{token}</div>
              <p style={{ marginTop: '1rem', fontSize: '0.875rem' }}>
                Token has been stored in localStorage and sessionStorage.
              </p>
            </div>
          )}

          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label className="label" htmlFor="email">
                Email address
              </label>
              <input
                id="email"
                className="input"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>

            <div className="form-group">
              <label className="label" htmlFor="password">
                Password
              </label>
              <input
                id="password"
                className="input"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>

            <button
              type="submit"
              className="button"
              disabled={isLoading}
            >
              {isLoading ? 'Signing in...' : 'Sign in'}
            </button>
          </form>
        </div>
      </div>
    </>
  );
};

// Define the correct type for Next.js pages with noAuth prop
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

export default DirectLogin;
