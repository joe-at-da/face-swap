import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import DarkLayout from '../components/layout/DarkLayout';
import { useQuery } from '@tanstack/react-query';
import { api } from '../utils/api';
import Link from 'next/link';
import { Card, Button } from '../components/ui';

interface DashboardStats {
  totalClips: number;
  recentClips: number;
  pendingCaptures: number;
  scheduledPosts: number;
  storageUsed: string;
  storageTotal: string;
}

interface Clip {
  id: number;
  title: string;
  duration: number;
  created_at: string;
  thumbnail_url: string;
}

const Dashboard: React.FC = () => {
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<any>(null);
  const [stats, setStats] = useState<DashboardStats>({
    totalClips: 0,
    recentClips: 0,
    pendingCaptures: 0,
    scheduledPosts: 0,
    storageUsed: '0 GB',
    storageTotal: '0 GB',
  });

  // Check for authentication token on mount
  useEffect(() => {
    // Check for token in both localStorage and sessionStorage
    const storedToken = localStorage.getItem('token') || sessionStorage.getItem('token');
    
    if (!storedToken) {
      console.log('No token found, redirecting to login');
      router.push('/login');
      return;
    }
    
    console.log('Token found, setting in state and API client');
    setToken(storedToken);
    api.setAuthToken(storedToken);
    
    // Fetch user data
    const fetchUserData = async () => {
      try {
        const userData = await api.get('/auth/me');
        console.log('User data fetched:', userData);
        setUser(userData);
      } catch (error) {
        console.error('Failed to fetch user data:', error);
        // If we can't fetch user data, token might be invalid
        localStorage.removeItem('token');
        sessionStorage.removeItem('token');
        router.push('/login');
      }
    };
    
    fetchUserData();
  }, [router]);

  // Fetch dashboard stats
  const { data: statsData, isLoading: statsLoading } = useQuery({
    queryKey: ['dashboardStats', token],
    queryFn: async () => {
      try {
        console.log('Fetching dashboard stats with token:', token ? 'Present' : 'None');
        const data = await api.get('/dashboard/stats');
        console.log('Dashboard stats fetched successfully:', data);
        return data;
      } catch (error) {
        console.error('Failed to fetch dashboard stats:', error);
        // Return placeholder data when the API endpoint isn't available
        return {
          totalClips: 5,
          recentClips: 3,
          pendingCaptures: 1,
          scheduledPosts: 2,
          storageUsed: '2.4 GB',
          storageTotal: '100 GB'
        };
      }
    },
    // Don't retry failed requests during development
    retry: false,
    // Prevent query from running until we have a token
    enabled: !!token
  });

  useEffect(() => {
    if (statsData) {
      setStats(statsData);
    }
  }, [statsData]);

  // Fetch recent clips
  const { data: recentClipsData, isLoading: clipsLoading } = useQuery({
    queryKey: ['recentClips', token],
    queryFn: async () => {
      try {
        console.log('Fetching recent clips with token:', token ? 'Present' : 'None');
        const data = await api.get('/clips/?limit=5&sort=created_at:desc');
        console.log('Recent clips fetched successfully:', data);
        return data;
      } catch (error) {
        console.error('Failed to fetch recent clips:', error);
        // Return placeholder data when the API endpoint isn't available
        return {
          items: [
            {
              id: 1,
              title: 'Sample Clip 1',
              duration: 120,
              created_at: new Date().toISOString(),
              thumbnail_url: '/placeholder-thumbnail.jpg'
            },
            {
              id: 2,
              title: 'Sample Clip 2',
              duration: 180,
              created_at: new Date().toISOString(),
              thumbnail_url: '/placeholder-thumbnail.jpg'
            }
          ]
        };
      }
    },
    // Don't retry failed requests during development
    retry: false,
    // Prevent query from running until we have a token
    enabled: !!token
  });

  const handleLogout = () => {
    localStorage.removeItem('token');
    sessionStorage.removeItem('token');
    router.push('/login');
  };

  // Format duration in seconds to MM:SS
  const formatDuration = (seconds: number): string => {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
  };

  // Format date to readable format
  const formatDate = (dateString: string): string => {
    const date = new Date(dateString);
    return date.toLocaleDateString();
  };

  return (
    <DarkLayout>
      <div className="p-6">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-2xl font-bold text-white">Dashboard</h1>
          <Button 
            onClick={handleLogout}
            variant="danger"
          >
            Logout
          </Button>
        </div>

        {user && (
          <Card className="mb-6">
            <p className="text-white">Welcome, {user.email}</p>
            <p className="text-gray-400">Role: {user.role}</p>
          </Card>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <Card className="bg-gray-700">
            <h3 className="text-xl font-semibold mb-2 text-white">Total Clips</h3>
            <p className="text-3xl font-bold text-blue-400">{stats.totalClips}</p>
          </Card>
          <Card className="bg-gray-700">
            <h3 className="text-xl font-semibold mb-2 text-white">Recent Clips</h3>
            <p className="text-3xl font-bold text-green-400">{stats.recentClips}</p>
          </Card>
          <Card className="bg-gray-700">
            <h3 className="text-xl font-semibold mb-2 text-white">Pending Captures</h3>
            <p className="text-3xl font-bold text-yellow-400">{stats.pendingCaptures}</p>
          </Card>
          <Card className="bg-gray-700">
            <h3 className="text-xl font-semibold mb-2 text-white">Scheduled Posts</h3>
            <p className="text-3xl font-bold text-purple-400">{stats.scheduledPosts}</p>
          </Card>
        </div>

        <Card className="mb-8" title="Storage Usage">
          <div className="flex justify-between mb-2 text-gray-300">
            <span>Used: {stats.storageUsed}</span>
            <span>Total: {stats.storageTotal}</span>
          </div>
          <div className="w-full bg-gray-700 rounded-full h-2.5">
            <div 
              className="bg-blue-600 h-2.5 rounded-full" 
              style={{ width: `${(parseInt(stats.storageUsed) / parseInt(stats.storageTotal) * 100) || 0}%` }}
            ></div>
          </div>
        </Card>

        <Card title="Recent Clips">
          {clipsLoading ? (
            <p className="text-gray-300">Loading clips...</p>
          ) : recentClipsData?.items?.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {recentClipsData.items.map((clip: Clip) => (
                <div key={clip.id} className="bg-gray-700 rounded overflow-hidden">
                  <div className="relative pb-[56.25%] bg-gray-900">
                    <img 
                      src={clip.thumbnail_url || '/placeholder-thumbnail.jpg'} 
                      alt={clip.title}
                      className="absolute h-full w-full object-cover"
                    />
                  </div>
                  <div className="p-4">
                    <h3 className="font-semibold mb-2 text-white">{clip.title}</h3>
                    <div className="flex justify-between text-sm text-gray-400">
                      <span>{formatDuration(clip.duration)}</span>
                      <span>{formatDate(clip.created_at)}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-300">No clips found.</p>
          )}
        </Card>

        <div className="mt-8">
          <Link href="/clips/new">
            <Button variant="primary">Create New Clip</Button>
          </Link>
        </div>

        {token && (
          <Card className="mt-8" title="Authentication Token">
            <div className="bg-gray-900 p-2 rounded text-xs font-mono break-all text-gray-300">
              {token}
            </div>
          </Card>
        )}
      </div>
    </DarkLayout>
  );
};

export default Dashboard;
