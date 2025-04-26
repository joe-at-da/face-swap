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
      console.log('%c[AuthContext] Initializing authentication state...', 'color: blue; font-weight: bold');
      console.log('[AuthContext] Current pathname:', router.pathname);
      
      // Check if we're in the process of logging in or just logged in
      const isLoggingIn = sessionStorage.getItem('loggingIn') === 'true';
      const justLoggedIn = sessionStorage.getItem('justLoggedIn') === 'true';
      const isRedirecting = sessionStorage.getItem('redirecting') === 'true';
      
      console.log('[AuthContext] Auth flags:', { 
        isLoggingIn, 
        justLoggedIn, 
        isRedirecting,
        pathname: router.pathname
      });
      
      if (justLoggedIn) {
        console.log('%c[AuthContext] User just logged in, preventing redirect', 'color: green');
        sessionStorage.removeItem('justLoggedIn');
        setIsLoading(false);
        return;
      }
      
      // Check for token in both localStorage and sessionStorage
      const localStorageToken = localStorage.getItem('token');
      const sessionStorageToken = sessionStorage.getItem('token');
      const storedToken = localStorageToken || sessionStorageToken;
      
      console.log('[AuthContext] Token status:', { 
        hasLocalStorageToken: !!localStorageToken, 
        hasSessionStorageToken: !!sessionStorageToken,
        tokenLength: storedToken ? storedToken.length : 0
      });
      
      if (storedToken) {
        try {
          console.log('%c[AuthContext] Found stored token, attempting to validate...', 'color: blue');
          // Set token in state and API
          setToken(storedToken);
          api.setAuthToken(storedToken);
          
          // Fetch user data
          console.log('[AuthContext] Fetching user data with token...');
          console.log('[AuthContext] Token first 20 chars:', storedToken.substring(0, 20) + '...');
          
          try {
            const userData = await api.get('/auth/me');
            console.log('%c[AuthContext] User data fetched successfully:', 'color: green', userData);
            setUser(userData);
            console.log('%c[AuthContext] User authenticated successfully:', 'color: green', userData.email);
            
            // IMPORTANT: Store authentication status in sessionStorage
            // This is critical to prevent redirect loops
            sessionStorage.setItem('isAuthenticated', 'true');
            
            // If we're on the login page and already authenticated, redirect to dashboard
            if (router.pathname === '/login') {
              console.log('%c[AuthContext] Already authenticated, redirecting to dashboard', 'color: purple');
              // Set flag to prevent redirect loops
              sessionStorage.setItem('redirecting', 'true');
              router.push('/dashboard');
            }
          } catch (apiError) {
            console.error('%c[AuthContext] API error when fetching user data:', 'color: red', apiError);
            throw apiError; // Re-throw to be caught by the outer catch block
          }
        } catch (error) {
          console.error('%c[AuthContext] Failed to authenticate with stored token:', 'color: red', error);
          // Clear authentication data
          localStorage.removeItem('token');
          sessionStorage.removeItem('token');
          sessionStorage.removeItem('isAuthenticated');
          setToken(null);
          setUser(null);
          api.setAuthToken(null);
          
          // If we're not on the login page and not in the process of logging in, redirect to login
          if (router.pathname !== '/login' && !isLoggingIn) {
            console.log('%c[AuthContext] Authentication failed, redirecting to login', 'color: orange');
            // Set flag to prevent redirect loops
            sessionStorage.setItem('redirecting', 'true');
            router.push('/login');
          }
        }
      } else {
        console.log('%c[AuthContext] No stored token found', 'color: orange');
        // If we're not on the login page and not in the process of logging in, redirect to login
        if (router.pathname !== '/login' && !isLoggingIn) {
          console.log('%c[AuthContext] No authentication, redirecting to login', 'color: orange');
          // Set flag to prevent redirect loops
          sessionStorage.setItem('redirecting', 'true');
          router.push('/login');
        }
      }
      
      setIsLoading(false);
    };

    // Only run initAuth if we're not currently redirecting
    const isRedirecting = sessionStorage.getItem('redirecting') === 'true';
    console.log('[AuthContext] Before initAuth check, isRedirecting:', isRedirecting);
    
    if (!isRedirecting) {
      console.log('[AuthContext] Running initAuth...');
      initAuth();
    } else {
      // Clear the redirecting flag after it's been used
      console.log('[AuthContext] Skipping initAuth due to redirecting flag');
      sessionStorage.removeItem('redirecting');
      setIsLoading(false);
    }
  }, [router]);

  // Login function
  const login = async (email: string, password: string) => {
    setIsLoading(true);
    // Set a flag to indicate we're in the login process
    sessionStorage.setItem('loggingIn', 'true');
    
    try {
      console.log('%c[AuthContext] Attempting login for:', 'color: blue; font-weight: bold', email);
      
      // Create form data for OAuth2 login - this is the format expected by FastAPI's OAuth2PasswordRequestForm
      const formData = new URLSearchParams();
      formData.append('username', email); // OAuth2 expects 'username' even though we're using email
      formData.append('password', password);
      
      // Always use localhost when running in browser
      const apiUrl = 'http://localhost:8000/api/v1/auth/login';
      
      console.log('[AuthContext] Using API URL:', apiUrl);
      
      // Make the login request
      const response = await fetch(apiUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'Accept': 'application/json',
        },
        body: formData,
        // Use same-origin for credentials
        credentials: 'same-origin',
      });
      
      console.log('[AuthContext] Login response status:', response.status);
      
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
        
        console.error('[AuthContext] Login error details:', errorDetail);
        throw new Error(errorDetail);
      }
      
      // Parse the successful response
      const data = await response.json();
      console.log('%c[AuthContext] Login successful, received token', 'color: green');
      const { access_token } = data;
      
      // Store token in both localStorage and sessionStorage for redundancy
      console.log('[AuthContext] Storing access token in localStorage, sessionStorage and state');
      localStorage.setItem('token', access_token);
      sessionStorage.setItem('token', access_token);
      setToken(access_token);
      
      // Ensure token is set in API client
      api.setAuthToken(access_token);
      
      // Set flags to indicate successful authentication
      // This is critical to prevent redirect loops
      sessionStorage.setItem('authSuccess', 'true');
      sessionStorage.setItem('isAuthenticated', 'true');
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
      
      // Clear the login flag
      sessionStorage.removeItem('loggingIn');
      
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
    console.log('%c[AuthContext] Logging out user', 'color: orange');
    
    // Clear all tokens and authentication state
    localStorage.removeItem('token');
    sessionStorage.removeItem('token');
    sessionStorage.removeItem('isAuthenticated');
    sessionStorage.removeItem('authSuccess');
    sessionStorage.removeItem('justLoggedIn');
    sessionStorage.removeItem('loggingIn');
    sessionStorage.removeItem('redirecting');
    
    // Update state
    setToken(null);
    setUser(null);
    api.setAuthToken(null);
    
    // Redirect to login
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
