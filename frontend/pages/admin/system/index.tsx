import React from 'react';
import MainLayout from '../../../components/layout/MainLayout';
import { useAuth } from '../../../contexts/AuthContext';
import { UserRole } from '../../../contexts/AuthContext';
import { useRouter } from 'next/router';

const SystemAdminPage: React.FC = () => {
  const { user } = useAuth();
  const router = useRouter();

  // Redirect if not admin
  React.useEffect(() => {
    if (user && user.role !== UserRole.ADMIN) {
      router.push('/dashboard');
    }
  }, [user, router]);

  if (!user || user.role !== UserRole.ADMIN) {
    return null;
  }

  return (
    <MainLayout title="System Administration | Parliament Video Clip Manager">
      <div className="container mx-auto px-4 py-8">
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">System Administration</h1>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* System Status Card */}
          <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">System Status</h2>
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <span className="text-gray-600 dark:text-gray-400">API Server</span>
                <span className="px-2 py-1 text-xs font-semibold rounded-full bg-green-100 text-green-800 dark:bg-green-800 dark:text-green-100">
                  Online
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-600 dark:text-gray-400">Database</span>
                <span className="px-2 py-1 text-xs font-semibold rounded-full bg-green-100 text-green-800 dark:bg-green-800 dark:text-green-100">
                  Connected
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-600 dark:text-gray-400">Redis Cache</span>
                <span className="px-2 py-1 text-xs font-semibold rounded-full bg-green-100 text-green-800 dark:bg-green-800 dark:text-green-100">
                  Connected
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-600 dark:text-gray-400">Celery Workers</span>
                <span className="px-2 py-1 text-xs font-semibold rounded-full bg-green-100 text-green-800 dark:bg-green-800 dark:text-green-100">
                  Running
                </span>
              </div>
            </div>
          </div>

          {/* System Metrics Card */}
          <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">System Metrics</h2>
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <span className="text-gray-600 dark:text-gray-400">CPU Usage</span>
                <span className="text-gray-900 dark:text-white font-medium">12%</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-600 dark:text-gray-400">Memory Usage</span>
                <span className="text-gray-900 dark:text-white font-medium">1.2 GB / 8 GB</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-600 dark:text-gray-400">Disk Usage</span>
                <span className="text-gray-900 dark:text-white font-medium">24 GB / 100 GB</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-600 dark:text-gray-400">Network Traffic</span>
                <span className="text-gray-900 dark:text-white font-medium">2.4 MB/s</span>
              </div>
            </div>
          </div>

          {/* System Logs Card */}
          <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6 md:col-span-2">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white">System Logs</h2>
              <div>
                <select className="bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-white text-sm rounded-lg focus:ring-primary focus:border-primary block p-2">
                  <option>All Logs</option>
                  <option>Error Logs</option>
                  <option>Info Logs</option>
                  <option>Debug Logs</option>
                </select>
              </div>
            </div>
            <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-3 font-mono text-sm h-64 overflow-y-auto">
              <div className="text-gray-500 dark:text-gray-400">
                <p>[2025-04-26 13:45:12] INFO: System startup complete</p>
                <p>[2025-04-26 13:45:15] INFO: Connected to database</p>
                <p>[2025-04-26 13:45:16] INFO: Redis connection established</p>
                <p>[2025-04-26 13:45:18] INFO: Celery workers started</p>
                <p>[2025-04-26 13:46:02] INFO: User admin@parliament.uk logged in</p>
                <p>[2025-04-26 13:47:30] INFO: Storage check completed</p>
                <p>[2025-04-26 13:50:15] INFO: Scheduled tasks running</p>
                <p>[2025-04-26 14:00:00] INFO: Hourly system check passed</p>
                <p>[2025-04-26 14:15:22] INFO: Authentication service healthy</p>
                <p>[2025-04-26 14:30:05] INFO: Video processing service healthy</p>
              </div>
            </div>
          </div>

          {/* Coming Soon Features */}
          <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6 md:col-span-2">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">Coming Soon</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
                <h3 className="font-medium text-gray-900 dark:text-white mb-2">Advanced Monitoring</h3>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Integration with Prometheus and Grafana for detailed system metrics and dashboards.
                </p>
              </div>
              <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
                <h3 className="font-medium text-gray-900 dark:text-white mb-2">Backup Management</h3>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Configure and manage automated backups for database and media files.
                </p>
              </div>
              <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
                <h3 className="font-medium text-gray-900 dark:text-white mb-2">System Settings</h3>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Configure application-wide settings and parameters.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </MainLayout>
  );
};

export default SystemAdminPage;
