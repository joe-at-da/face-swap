import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Link from 'next/link';
import MainLayout from '../../../components/layout/MainLayout';
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
        return 'bg-red-100 text-red-800';
      case UserRole.MP:
        return 'bg-blue-100 text-blue-800';
      case UserRole.STAFF:
        return 'bg-green-100 text-green-800';
      case UserRole.VIEWER:
        return 'bg-gray-100 text-gray-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };
  
  return (
    <MainLayout title="User Management | Parliament Video Clip Manager">
      <div className="page-container">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-3xl font-bold text-gray-900">User Management</h1>
          <Link href="/admin/users/new">
            <span className="btn-primary rounded-md px-4 py-2 text-center cursor-pointer inline-block">
              Add New User
            </span>
          </Link>
        </div>
        
        {/* Filters */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <div className="flex flex-col md:flex-row md:items-end space-y-4 md:space-y-0 md:space-x-4">
            <div>
              <label htmlFor="role" className="block text-sm font-medium text-gray-700 mb-1">
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
              <label htmlFor="status" className="block text-sm font-medium text-gray-700 mb-1">
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
              <label htmlFor="search" className="block text-sm font-medium text-gray-700 mb-1">
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
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-medium text-gray-800">Users</h2>
          </div>
          
          <div className="overflow-x-auto">
            {isLoading ? (
              <div className="p-6 text-center text-gray-500">Loading users...</div>
            ) : isError ? (
              <div className="p-6 text-center text-red-500">Error loading users</div>
            ) : !users || users.length === 0 ? (
              <div className="p-6 text-center text-gray-500">
                No users found. Add a new user to get started.
              </div>
            ) : (
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
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
                <tbody className="bg-white divide-y divide-gray-200">
                  {users.map((user: User) => (
                    <tr key={user.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center">
                          <div className="flex-shrink-0 h-10 w-10 rounded-full bg-gray-200 flex items-center justify-center">
                            <span className="text-gray-500 font-medium text-lg">
                              {user.name.charAt(0).toUpperCase()}
                            </span>
                          </div>
                          <div className="ml-4">
                            <div className="text-sm font-medium text-gray-900">{user.name}</div>
                            <div className="text-sm text-gray-500">{user.email}</div>
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
    </MainLayout>
  );
};

export default withAuth(UserManagement, [UserRole.ADMIN]);
