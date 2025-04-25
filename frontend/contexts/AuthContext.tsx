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
      const response = await api.post('/auth/login', { email, password });
      const { access_token, user: userData } = response;
      
      // Store token and user data
      localStorage.setItem('token', access_token);
      setToken(access_token);
      setUser(userData);
      api.setAuthToken(access_token);
      
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
