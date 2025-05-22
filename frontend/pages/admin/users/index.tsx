import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Link from 'next/link';
import DarkLayout from '../../../components/layout/DarkLayout';
import { withAuth } from '../../../contexts/AuthContext';
import { UserRole } from '../../../contexts/AuthContext';
import { api } from '../../../utils/api';

interface User {
  id: number;
  name: string;
  email: string;
  role: UserRole;
  is_active: boolean;
  last_login: string | null;
  created_at: string;
}

interface FilterState {
  role: string;
  status: string;
  search: string;
}

const UserManagement: React.FC = () => {
  const queryClient = useQueryClient();
  
  // Filter state
  const [filters, setFilters] = useState<FilterState>({
    role: '',
    status: '',
    search: '',
  });
  
  // Fetch users
  const { data: users, isLoading, isError } = useQuery({
    queryKey: ['users', filters],
    queryFn: async () => {
      const params: Record<string, any> = {};
      
      if (filters.role) {
        params.role = filters.role;
      }
      
      if (filters.status) {
        params.is_active = filters.status === 'active';
      }
      
      if (filters.search) {
        params.search = filters.search;
      }
      
      return await api.get('/admin/users', params);
    },
  });
  
  // Toggle user active status mutation
  const toggleUserStatusMutation = useMutation({
    mutationFn: async ({ userId, isActive }: { userId: number; isActive: boolean }) => {
      return await api.patch(`/admin/users/${userId}`, { is_active: isActive });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
    },
  });
  
  // Handle filter changes
  const handleFilterChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFilters((prev) => ({ ...prev, [name]: value }));
  };
  
  // Handle search input
  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFilters((prev) => ({ ...prev, search: e.target.value }));
  };
  
  // Handle toggle user status
  const handleToggleUserStatus = (user: User) => {
    if (confirm(`Are you sure you want to ${user.is_active ? 'deactivate' : 'activate'} this user?`)) {
      toggleUserStatusMutation.mutate({
        userId: user.id,
        isActive: !user.is_active,
      });
    }
  };
  
  // Format date to readable format
  const formatDate = (dateString: string | null): string => {
    if (!dateString) return 'Never';
    
    const date = new Date(dateString);
    return date.toLocaleDateString('en-GB', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };
  
  // Get role badge color
  const getRoleBadgeClass = (role: UserRole): string => {
    switch (role) {
      case UserRole.ADMIN:
        return 'bg-red-500 text-white';
      case UserRole.MP:
        return 'bg-blue-500 text-white';
      case UserRole.STAFF:
        return 'bg-green-500 text-white';
      default:
        return 'bg-gray-500 text-white';
    }
  };
  
  return (
    <DarkLayout>
      <div className="page-container">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-3xl font-bold text-white">User Management</h1>
          <Link href="/admin/users/new">
            <span className="btn-primary rounded-md px-4 py-2 text-center cursor-pointer inline-block">
              Add New User
            </span>
          </Link>
        </div>
        
        {/* Filters */}
        <div className="bg-gray-800 rounded-lg shadow p-6 mb-6">
          <div className="flex flex-col md:flex-row md:items-end space-y-4 md:space-y-0 md:space-x-4">
            <div>
              <label htmlFor="role" className="block text-sm font-medium text-gray-300 mb-1">
                Role
              </label>
              <select
                id="role"
                name="role"
                value={filters.role}
                onChange={handleFilterChange}
                className="form-input w-full md:w-40"
              >
                <option value="">All Roles</option>
                <option value={UserRole.ADMIN}>Admin</option>
                <option value={UserRole.MP}>MP</option>
                <option value={UserRole.STAFF}>Staff</option>
                <option value={UserRole.VIEWER}>Viewer</option>
              </select>
            </div>
            
            <div>
              <label htmlFor="status" className="block text-sm font-medium text-gray-300 mb-1">
                Status
              </label>
              <select
                id="status"
                name="status"
                value={filters.status}
                onChange={handleFilterChange}
                className="form-input w-full md:w-40"
              >
                <option value="">All Statuses</option>
                <option value="active">Active</option>
                <option value="inactive">Inactive</option>
              </select>
            </div>
            
            <div className="flex-grow">
              <label htmlFor="search" className="block text-sm font-medium text-gray-300 mb-1">
                Search
              </label>
              <input
                type="text"
                id="search"
                name="search"
                value={filters.search}
                onChange={handleSearchChange}
                placeholder="Search by name or email"
                className="form-input w-full"
              />
            </div>
          </div>
        </div>
        
        {/* Users table */}
        <div className="bg-gray-800 rounded-lg shadow overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-medium text-gray-300">Users</h2>
          </div>
          
          <div className="overflow-x-auto">
            {isLoading ? (
              <div className="text-center py-8 text-gray-300">Loading users...</div>
            ) : isError ? (
              <div className="bg-gray-900 border-l-4 border-red-600 p-4 mb-6">
                <div className="flex">
                  <div className="flex-shrink-0">
                    <svg className="h-5 w-5 text-red-500" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                    </svg>
                  </div>
                  <div className="ml-3">
                    <h3 className="text-sm font-medium text-red-400">Error</h3>
                    <div className="mt-2 text-sm text-red-300">
                      <p>Failed to load users. Please try again.</p>
                    </div>
                  </div>
                </div>
              </div>
            ) : !users || users.length === 0 ? (
              <div className="p-6 text-center text-gray-500">
                No users found. Add a new user to get started.
              </div>
            ) : (
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-900">
                  <tr>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                      User
                    </th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Role
                    </th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Status
                    </th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Last Login
                    </th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Created
                    </th>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-gray-800 divide-y divide-gray-700">
                  {users.map((user: User) => (
                    <tr key={user.id} className="hover:bg-gray-700">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center">
                          <div className="flex-shrink-0 h-10 w-10 rounded-full bg-gray-600 flex items-center justify-center">
                            <span className="text-gray-300 font-medium text-lg">
                              {user.name ? user.name.charAt(0).toUpperCase() : '?'}
                            </span>
                          </div>
                          <div className="ml-4">
                            <div className="text-sm font-medium text-white">{user.name}</div>
                            <div className="text-sm text-gray-300">{user.email}</div>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${getRoleBadgeClass(user.role)}`}>
                          {user.role}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                          user.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                        }`}>
                          {user.is_active ? 'Active' : 'Inactive'}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {formatDate(user.last_login)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {formatDate(user.created_at)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                        <Link href={`/admin/users/${user.id}`}>
                          <span className="text-primary hover:text-primary-dark mr-3 cursor-pointer">
                            View
                          </span>
                        </Link>
                        <Link href={`/admin/users/${user.id}/edit`}>
                          <span className="text-primary hover:text-primary-dark mr-3 cursor-pointer">
                            Edit
                          </span>
                        </Link>
                        <button
                          type="button"
                          onClick={() => handleToggleUserStatus(user)}
                          disabled={toggleUserStatusMutation.isPending}
                          className={`${
                            user.is_active ? 'text-red-600 hover:text-red-900' : 'text-green-600 hover:text-green-900'
                          }`}
                        >
                          {toggleUserStatusMutation.isPending && toggleUserStatusMutation.variables?.userId === user.id
                            ? 'Processing...'
                            : user.is_active
                            ? 'Deactivate'
                            : 'Activate'}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </div>
    </DarkLayout>
  );
};

export default withAuth(UserManagement, [UserRole.ADMIN]);
