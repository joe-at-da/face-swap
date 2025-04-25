import React, { useState } from 'react';
import { useRouter } from 'next/router';
import { useMutation } from '@tanstack/react-query';
import Link from 'next/link';
import MainLayout from '../../../components/layout/MainLayout';
import { withAuth } from '../../../contexts/AuthContext';
import { UserRole } from '../../../contexts/AuthContext';
import { api } from '../../../utils/api';

interface UserFormData {
  name: string;
  email: string;
  password: string;
  password_confirmation: string;
  role: UserRole;
  is_active: boolean;
}

const NewUserPage: React.FC = () => {
  const router = useRouter();
  
  // Form state
  const [formData, setFormData] = useState<UserFormData>({
    name: '',
    email: '',
    password: '',
    password_confirmation: '',
    role: UserRole.VIEWER,
    is_active: true,
  });
  
  // Error state
  const [errors, setErrors] = useState<Record<string, string>>({});
  
  // Create user mutation
  const createUserMutation = useMutation({
    mutationFn: async (data: UserFormData) => {
      return await api.post('/admin/users', data);
    },
    onSuccess: () => {
      router.push('/admin/users');
    },
    onError: (error: any) => {
      if (error.response?.data?.errors) {
        setErrors(error.response.data.errors);
      } else {
        setErrors({
          form: error.message || 'Failed to create user',
        });
      }
    },
  });
  
  // Handle form input changes
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value, type } = e.target;
    
    if (type === 'checkbox') {
      const target = e.target as HTMLInputElement;
      setFormData((prev) => ({ ...prev, [name]: target.checked }));
    } else {
      setFormData((prev) => ({ ...prev, [name]: value }));
    }
    
    // Clear error for this field
    if (errors[name]) {
      setErrors((prev) => {
        const newErrors = { ...prev };
        delete newErrors[name];
        return newErrors;
      });
    }
  };
  
  // Validate form before submission
  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {};
    
    if (!formData.name.trim()) {
      newErrors.name = 'Name is required';
    }
    
    if (!formData.email.trim()) {
      newErrors.email = 'Email is required';
    } else if (!/\S+@\S+\.\S+/.test(formData.email)) {
      newErrors.email = 'Email is invalid';
    }
    
    if (!formData.password) {
      newErrors.password = 'Password is required';
    } else if (formData.password.length < 8) {
      newErrors.password = 'Password must be at least 8 characters';
    }
    
    if (formData.password !== formData.password_confirmation) {
      newErrors.password_confirmation = 'Passwords do not match';
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };
  
  // Handle form submission
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) return;
    
    createUserMutation.mutate(formData);
  };
  
  // Generate random password
  const generateRandomPassword = () => {
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*()';
    let password = '';
    
    for (let i = 0; i < 12; i++) {
      password += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    
    setFormData((prev) => ({
      ...prev,
      password,
      password_confirmation: password,
    }));
    
    // Clear password errors
    setErrors((prev) => {
      const newErrors = { ...prev };
      delete newErrors.password;
      delete newErrors.password_confirmation;
      return newErrors;
    });
  };
  
  return (
    <MainLayout title="Add New User | Parliament Video Clip Manager">
      <div className="page-container">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-3xl font-bold text-gray-900">Add New User</h1>
          <Link href="/admin/users">
            <span className="text-gray-600 hover:text-gray-900 px-4 py-2 border border-gray-300 rounded-md cursor-pointer inline-block">
              Cancel
            </span>
          </Link>
        </div>
        
        {/* Form error */}
        {errors.form && (
          <div className="bg-red-50 border-l-4 border-red-500 p-4 mb-6">
            <div className="flex">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
              </div>
              <div className="ml-3">
                <p className="text-sm text-red-700">{errors.form}</p>
              </div>
            </div>
          </div>
        )}
        
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-medium text-gray-800">User Information</h2>
          </div>
          
          <form onSubmit={handleSubmit} className="p-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Name */}
              <div>
                <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-1">
                  Name *
                </label>
                <input
                  type="text"
                  id="name"
                  name="name"
                  value={formData.name}
                  onChange={handleInputChange}
                  className={`form-input ${errors.name ? 'border-red-300 focus:ring-red-500 focus:border-red-500' : ''}`}
                  placeholder="Enter user's full name"
                />
                {errors.name && (
                  <p className="mt-1 text-sm text-red-600">{errors.name}</p>
                )}
              </div>
              
              {/* Email */}
              <div>
                <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
                  Email *
                </label>
                <input
                  type="email"
                  id="email"
                  name="email"
                  value={formData.email}
                  onChange={handleInputChange}
                  className={`form-input ${errors.email ? 'border-red-300 focus:ring-red-500 focus:border-red-500' : ''}`}
                  placeholder="Enter user's email address"
                />
                {errors.email && (
                  <p className="mt-1 text-sm text-red-600">{errors.email}</p>
                )}
              </div>
              
              {/* Role */}
              <div>
                <label htmlFor="role" className="block text-sm font-medium text-gray-700 mb-1">
                  Role *
                </label>
                <select
                  id="role"
                  name="role"
                  value={formData.role}
                  onChange={handleInputChange}
                  className="form-input"
                >
                  <option value={UserRole.ADMIN}>Admin</option>
                  <option value={UserRole.MP}>MP</option>
                  <option value={UserRole.STAFF}>Staff</option>
                  <option value={UserRole.VIEWER}>Viewer</option>
                </select>
                <p className="mt-1 text-sm text-gray-500">
                  {formData.role === UserRole.ADMIN
                    ? 'Full access to all features and settings'
                    : formData.role === UserRole.MP
                    ? 'Can create and manage clips, captures, and social media posts'
                    : formData.role === UserRole.STAFF
                    ? 'Can create and manage clips and captures'
                    : 'Can only view clips'}
                </p>
              </div>
              
              {/* Status */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-3">
                  Status
                </label>
                <div className="flex items-center">
                  <input
                    type="checkbox"
                    id="is_active"
                    name="is_active"
                    checked={formData.is_active}
                    onChange={handleInputChange}
                    className="h-4 w-4 text-primary focus:ring-primary border-gray-300 rounded"
                  />
                  <label htmlFor="is_active" className="ml-2 block text-sm text-gray-900">
                    Active
                  </label>
                </div>
                <p className="mt-1 text-sm text-gray-500">
                  Inactive users cannot log in to the system
                </p>
              </div>
              
              {/* Password */}
              <div>
                <div className="flex justify-between items-center mb-1">
                  <label htmlFor="password" className="block text-sm font-medium text-gray-700">
                    Password *
                  </label>
                  <button
                    type="button"
                    onClick={generateRandomPassword}
                    className="text-xs text-primary hover:text-primary-dark"
                  >
                    Generate Random Password
                  </button>
                </div>
                <input
                  type="password"
                  id="password"
                  name="password"
                  value={formData.password}
                  onChange={handleInputChange}
                  className={`form-input ${errors.password ? 'border-red-300 focus:ring-red-500 focus:border-red-500' : ''}`}
                  placeholder="Enter password"
                />
                {errors.password ? (
                  <p className="mt-1 text-sm text-red-600">{errors.password}</p>
                ) : (
                  <p className="mt-1 text-sm text-gray-500">
                    Password must be at least 8 characters
                  </p>
                )}
              </div>
              
              {/* Password Confirmation */}
              <div>
                <label htmlFor="password_confirmation" className="block text-sm font-medium text-gray-700 mb-1">
                  Confirm Password *
                </label>
                <input
                  type="password"
                  id="password_confirmation"
                  name="password_confirmation"
                  value={formData.password_confirmation}
                  onChange={handleInputChange}
                  className={`form-input ${errors.password_confirmation ? 'border-red-300 focus:ring-red-500 focus:border-red-500' : ''}`}
                  placeholder="Confirm password"
                />
                {errors.password_confirmation && (
                  <p className="mt-1 text-sm text-red-600">{errors.password_confirmation}</p>
                )}
              </div>
            </div>
            
            {/* Submit button */}
            <div className="mt-8 flex justify-end">
              <button
                type="submit"
                disabled={createUserMutation.isPending}
                className="btn-primary rounded-md px-4 py-2 text-center cursor-pointer inline-block disabled:opacity-50"
              >
                {createUserMutation.isPending ? 'Creating User...' : 'Create User'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </MainLayout>
  );
};

export default withAuth(NewUserPage, [UserRole.ADMIN]);
