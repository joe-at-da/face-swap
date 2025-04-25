import React, { createContext, useState, useContext, useEffect } from 'react';
import { useRouter } from 'next/router';
import { api } from '../utils/api';

// Define user roles based on the backend enum
export enum UserRole {
  ADMIN = 'admin',
  MP = 'mp',
  STAFF = 'staff',
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
      const storedToken = localStorage.getItem('token');
      
      if (storedToken) {
        try {
          // Set token in state and API
          setToken(storedToken);
          api.setAuthToken(storedToken);
          
          // Fetch user data
          const userData = await api.get('/auth/me');
          setUser(userData);
        } catch (error) {
          console.error('Failed to authenticate:', error);
          localStorage.removeItem('token');
          setToken(null);
          api.setAuthToken(null);
        }
      }
      
      setIsLoading(false);
    };

    initAuth();
  }, []);

  // Login function
  const login = async (email: string, password: string) => {
    setIsLoading(true);
    
    try {
      // Create form data for OAuth2 login
      const formData = new URLSearchParams();
      formData.append('username', email); // OAuth2 expects 'username' even though we're using email
      formData.append('password', password);
      
      // When running in Docker, use the service name 'app' instead of localhost
      const isDocker = process.env.DOCKER_ENV === 'true';
      const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || (isDocker ? 'http://app:8000' : 'http://localhost:8000');
      
      // Make the request with form data instead of JSON
      const response = await fetch(`${apiBaseUrl}/api/v1/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: formData,
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Login failed: ${response.status}`);
      }
      
      const data = await response.json();
      const { access_token } = data;
      
      // Store token
      localStorage.setItem('token', access_token);
      setToken(access_token);
      
      // Fetch user data with the token
      api.setAuthToken(access_token);
      const userData = await api.get('/users/me');
      setUser(userData);
      
      // Redirect to dashboard
      router.push('/dashboard');
    } catch (error) {
      console.error('Login failed:', error);
      throw error;
    } finally {
      setIsLoading(false);
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
    const { isAuthenticated, isLoading, hasRole } = useAuth();
    const router = useRouter();

    useEffect(() => {
      if (!isLoading && !isAuthenticated) {
        router.push('/login');
      } else if (!isLoading && isAuthenticated && requiredRoles && !hasRole(requiredRoles)) {
        router.push('/unauthorized');
      }
    }, [isLoading, isAuthenticated, router]);

    if (isLoading) {
      return <div className="flex items-center justify-center min-h-screen">Loading...</div>;
    }

    if (!isAuthenticated) {
      return null;
    }

    if (requiredRoles && !hasRole(requiredRoles)) {
      return null;
    }

    return <Component {...props} />;
  };

  return AuthGuard;
};
