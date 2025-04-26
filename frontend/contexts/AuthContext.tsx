import React, { createContext, useState, useContext, useEffect } from 'react';
import { useRouter } from 'next/router';
import { api } from '../utils/api';

// Define user roles based on the backend enum
export enum UserRole {
  ADMIN = 'ADMIN',
  MP = 'MP',
  STAFF = 'STAFF',
}

// Define user type
export interface User {
  id: number;
  email: string;
  name: string;
  role: UserRole;
}

// Define auth context type
interface AuthContextType {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  hasRole: (roles: UserRole[]) => boolean;
}

// Create auth context
const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Auth provider props
interface AuthProviderProps {
  children: React.ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  // Check if user is authenticated on mount
  useEffect(() => {
    const initAuth = async () => {
      console.log('Initializing authentication state...');
      const storedToken = localStorage.getItem('token');
      
      if (storedToken) {
        try {
          console.log('Found stored token, attempting to validate...');
          // Set token in state and API
          setToken(storedToken);
          api.setAuthToken(storedToken);
          
          // Fetch user data
          const userData = await api.get('/auth/me');
          setUser(userData);
          console.log('User authenticated successfully:', userData.email);
          
          // If we're on the login page and already authenticated, redirect to dashboard
          if (router.pathname === '/login') {
            console.log('Already authenticated, redirecting to dashboard');
            router.push('/dashboard');
          }
        } catch (error) {
          console.error('Failed to authenticate with stored token:', error);
          // Clear authentication data
          localStorage.removeItem('token');
          setToken(null);
          setUser(null);
          api.setAuthToken(null);
          
          // If we're not on the login page, redirect to login
          if (router.pathname !== '/login') {
            console.log('Authentication failed, redirecting to login');
            router.push('/login');
          }
        }
      } else {
        console.log('No stored token found');
        // If we're not on the login page and there's no token, redirect to login
        if (router.pathname !== '/login') {
          console.log('No authentication, redirecting to login');
          router.push('/login');
        }
      }
      
      setIsLoading(false);
    };

    initAuth();
  }, [router]);

  // Login function
  const login = async (email: string, password: string) => {
    setIsLoading(true);
    // Set a flag to indicate we're in the login process
    sessionStorage.setItem('loggingIn', 'true');
    
    try {
      console.log('Attempting login for:', email);
      
      // Create form data for OAuth2 login - this is the format expected by FastAPI's OAuth2PasswordRequestForm
      const formData = new URLSearchParams();
      formData.append('username', email); // OAuth2 expects 'username' even though we're using email
      formData.append('password', password);
      
      // Determine the correct API URL based on environment
      // When running in Docker, we need to use the service name
      let apiUrl = 'http://localhost:8000/api/v1/auth/login';
      if (typeof window !== 'undefined') {
        // Always use localhost when running in browser
        apiUrl = 'http://localhost:8000/api/v1/auth/login';
      }
      
      console.log('Using API URL:', apiUrl);
      
      // Make the login request
      const response = await fetch(apiUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'Accept': 'application/json',
        },
        body: formData,
        // Don't use 'include' for credentials as it requires specific CORS setup
        credentials: 'same-origin',
      });
      
      console.log('Login response status:', response.status);
      
      // Handle non-OK responses
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
        
        console.error('Login error details:', errorDetail);
        throw new Error(errorDetail);
      }
      
      // Parse the successful response
      const data = await response.json();
      console.log('Login successful, received token');
      const { access_token } = data;
      
      // Store token
      console.log('Storing access token in localStorage and state');
      localStorage.setItem('token', access_token);
      setToken(access_token);
      
      // Ensure token is set in API client
      api.setAuthToken(access_token);
      
      // Set a flag to indicate successful authentication
      sessionStorage.setItem('authSuccess', 'true');
      try {
        console.log('Fetching user data...');
        const userData = await api.get('/auth/me');
        setUser(userData);
        console.log('User authenticated successfully:', userData.email);
      } catch (error) {
        console.warn('Could not fetch user data:', error);
        // Set a minimal user object with the email
        setUser({
          id: 0, // Placeholder ID
          email,
          name: email.split('@')[0], // Use part of email as name
          role: UserRole.ADMIN // Use the enum value for admin role
        });
      }
      
      // Set flags to prevent redirect loops
      sessionStorage.setItem('justLoggedIn', 'true');
      sessionStorage.setItem('manualRedirect', 'true');
      
      // Small delay to ensure state is updated before redirect
      setTimeout(() => {
        console.log('Redirecting to dashboard after successful login');
        router.push('/dashboard');
      }, 100);
    } catch (error: any) {
      console.error('Login failed:', error.message || error);
      // Clear any partial authentication data
      localStorage.removeItem('token');
      setToken(null);
      setUser(null);
      api.setAuthToken(null);
      throw error;
    } finally {
      setIsLoading(false);
      // Clear the login flag
      sessionStorage.removeItem('loggingIn');
    }
  };

  // Logout function
  const logout = () => {
    localStorage.removeItem('token');
    setToken(null);
    setUser(null);
    api.setAuthToken(null);
    router.push('/login');
  };

  // Check if user has one of the specified roles
  const hasRole = (roles: UserRole[]) => {
    if (!user) return false;
    return roles.includes(user.role);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isLoading,
        isAuthenticated: !!user,
        login,
        logout,
        hasRole,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

// Custom hook to use auth context
export const useAuth = () => {
  const context = useContext(AuthContext);
  
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  
  return context;
};

// Auth guard HOC
export const withAuth = (Component: React.ComponentType, requiredRoles?: UserRole[]) => {
  const AuthGuard = (props: any) => {
    const { isAuthenticated, isLoading, hasRole, user, token } = useAuth();
    const router = useRouter();
    const [authChecked, setAuthChecked] = useState(false);

    useEffect(() => {
      console.log('withAuth effect running', { 
        isLoading, 
        isAuthenticated, 
        path: router.pathname,
        token: token ? 'Present' : 'None',
        user: user ? 'Logged in' : 'Not logged in'
      });

      // Skip redirect if we're in the process of logging in or we've just logged in
      const isLoggingIn = sessionStorage.getItem('loggingIn') === 'true';
      const justLoggedIn = sessionStorage.getItem('justLoggedIn') === 'true';
      
      if (justLoggedIn) {
        console.log('User just logged in, preventing redirect');
        sessionStorage.removeItem('justLoggedIn');
        setAuthChecked(true);
        return;
      }

      if (!isLoading) {
        if (!isAuthenticated && !isLoggingIn) {
          console.log('Not authenticated, redirecting to login');
          router.push('/login');
        } else if (isAuthenticated && requiredRoles && !hasRole(requiredRoles)) {
          console.log('Unauthorized role, redirecting');
          router.push('/unauthorized');
        } else if (isAuthenticated) {
          console.log('Authenticated, staying on current page');
          setAuthChecked(true);
        }
      }
    }, [isLoading, isAuthenticated, router, token, user]);

    if (isLoading) {
      return <div className="flex items-center justify-center min-h-screen">Loading...</div>;
    }

    if (!authChecked && !isAuthenticated) {
      return <div className="flex items-center justify-center min-h-screen">Checking authentication...</div>;
    }

    if (requiredRoles && !hasRole(requiredRoles)) {
      return null;
    }

    // We're authenticated and authorized, render the component
    return <Component {...props} />;
  };

  return AuthGuard;
};
