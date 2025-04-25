import React, { useState } from 'react';
import { useRouter } from 'next/router';
import { useMutation } from '@tanstack/react-query';
import Link from 'next/link';
import MainLayout from '../../components/layout/MainLayout';
import { withAuth } from '../../contexts/AuthContext';
import { UserRole } from '../../contexts/AuthContext';
import { api } from '../../utils/api';

interface CaptureFormData {
  title: string;
  description: string;
  source_url: string;
  scheduled_start?: string;
  scheduled_end?: string;
}

const NewCapturePage: React.FC = () => {
  const router = useRouter();
  const [formData, setFormData] = useState<CaptureFormData>({
    title: '',
    description: '',
    source_url: 'https://www.parliamentlive.tv/Event/Index/',
  });
  
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [scheduleCapture, setScheduleCapture] = useState(false);
  
  // Start capture mutation
  const startCaptureMutation = useMutation({
    mutationFn: async (data: CaptureFormData) => {
      return await api.post('/capture', data);
    },
    onSuccess: (data) => {
      router.push(`/capture/${data.id}`);
    },
    onError: (error: any) => {
      setErrors({
        form: error.message || 'Failed to start capture session',
      });
    },
  });

  // Handle form input changes
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    
    // Clear error for this field
    if (errors[name]) {
      setErrors((prev) => {
        const newErrors = { ...prev };
        delete newErrors[name];
        return newErrors;
      });
    }
  };

  // Toggle scheduling option
  const handleScheduleToggle = (e: React.ChangeEvent<HTMLInputElement>) => {
    setScheduleCapture(e.target.checked);
    
    // Clear scheduled times if scheduling is disabled
    if (!e.target.checked) {
      setFormData((prev) => ({
        ...prev,
        scheduled_start: undefined,
        scheduled_end: undefined,
      }));
    }
  };

  // Validate form before submission
  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {};
    
    if (!formData.title.trim()) {
      newErrors.title = 'Title is required';
    }
    
    if (!formData.source_url.trim()) {
      newErrors.source_url = 'Source URL is required';
    } else if (!formData.source_url.includes('parliamentlive.tv')) {
      newErrors.source_url = 'Source URL must be from parliamentlive.tv';
    }
    
    if (scheduleCapture) {
      if (!formData.scheduled_start) {
        newErrors.scheduled_start = 'Scheduled start time is required';
      }
      
      if (formData.scheduled_start && formData.scheduled_end) {
        const startDate = new Date(formData.scheduled_start);
        const endDate = new Date(formData.scheduled_end);
        
        if (startDate >= endDate) {
          newErrors.scheduled_end = 'End time must be after start time';
        }
      }
      
      // Ensure scheduled start is in the future
      if (formData.scheduled_start) {
        const startDate = new Date(formData.scheduled_start);
        const now = new Date();
        
        if (startDate <= now) {
          newErrors.scheduled_start = 'Scheduled start time must be in the future';
        }
      }
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // Handle form submission
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) return;
    
    const submitData = { ...formData };
    
    // Only include scheduled times if scheduling is enabled
    if (!scheduleCapture) {
      delete submitData.scheduled_start;
      delete submitData.scheduled_end;
    }
    
    startCaptureMutation.mutate(submitData);
  };

  // Get current date-time in ISO format for datetime-local input
  const getCurrentDateTime = (): string => {
    const now = new Date();
    now.setMinutes(now.getMinutes() + 5); // Add 5 minutes to current time
    return now.toISOString().slice(0, 16); // Format as YYYY-MM-DDTHH:MM
  };

  // Get default end time (current time + 2 hours)
  const getDefaultEndTime = (): string => {
    const now = new Date();
    now.setHours(now.getHours() + 2); // Add 2 hours to current time
    return now.toISOString().slice(0, 16); // Format as YYYY-MM-DDTHH:MM
  };

  return (
    <MainLayout title="Start New Capture | Parliament Video Clip Manager">
      <div className="page-container">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-3xl font-bold text-gray-900">Start New Capture</h1>
          <Link href="/capture">
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
            <h2 className="text-lg font-medium text-gray-800">Capture Details</h2>
          </div>
          
          <form onSubmit={handleSubmit} className="p-6">
            <div className="space-y-6">
              <div className="grid grid-cols-1 gap-6">
                {/* Title */}
                <div>
                  <label htmlFor="title" className="block text-sm font-medium text-gray-700">
                    Title *
                  </label>
                  <input
                    type="text"
                    id="title"
                    name="title"
                    value={formData.title}
                    onChange={handleInputChange}
                    className={`mt-1 form-input ${errors.title ? 'border-red-300 focus:ring-red-500 focus:border-red-500' : ''}`}
                    placeholder="Enter capture session title"
                  />
                  {errors.title && (
                    <p className="mt-1 text-sm text-red-600">{errors.title}</p>
                  )}
                </div>
                
                {/* Description */}
                <div>
                  <label htmlFor="description" className="block text-sm font-medium text-gray-700">
                    Description
                  </label>
                  <textarea
                    id="description"
                    name="description"
                    rows={3}
                    value={formData.description}
                    onChange={handleInputChange}
                    className="mt-1 form-input"
                    placeholder="Enter capture session description"
                  />
                </div>
                
                {/* Source URL */}
                <div>
                  <label htmlFor="source_url" className="block text-sm font-medium text-gray-700">
                    Parliament TV Source URL *
                  </label>
                  <input
                    type="url"
                    id="source_url"
                    name="source_url"
                    value={formData.source_url}
                    onChange={handleInputChange}
                    className={`mt-1 form-input ${errors.source_url ? 'border-red-300 focus:ring-red-500 focus:border-red-500' : ''}`}
                    placeholder="https://www.parliamentlive.tv/Event/Index/..."
                  />
                  {errors.source_url ? (
                    <p className="mt-1 text-sm text-red-600">{errors.source_url}</p>
                  ) : (
                    <p className="mt-1 text-sm text-gray-500">
                      Enter the URL of the Parliament TV stream you want to capture
                    </p>
                  )}
                </div>
                
                {/* Schedule toggle */}
                <div className="pt-4">
                  <div className="flex items-start">
                    <div className="flex items-center h-5">
                      <input
                        id="schedule"
                        name="schedule"
                        type="checkbox"
                        checked={scheduleCapture}
                        onChange={handleScheduleToggle}
                        className="h-4 w-4 text-primary focus:ring-primary border-gray-300 rounded"
                      />
                    </div>
                    <div className="ml-3 text-sm">
                      <label htmlFor="schedule" className="font-medium text-gray-700">
                        Schedule for later
                      </label>
                      <p className="text-gray-500">
                        Set a specific start and end time for the capture session
                      </p>
                    </div>
                  </div>
                </div>
                
                {/* Scheduled times */}
                {scheduleCapture && (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-2">
                    <div>
                      <label htmlFor="scheduled_start" className="block text-sm font-medium text-gray-700">
                        Scheduled Start Time *
                      </label>
                      <input
                        type="datetime-local"
                        id="scheduled_start"
                        name="scheduled_start"
                        value={formData.scheduled_start || ''}
                        onChange={handleInputChange}
                        min={getCurrentDateTime()}
                        className={`mt-1 form-input ${errors.scheduled_start ? 'border-red-300 focus:ring-red-500 focus:border-red-500' : ''}`}
                      />
                      {errors.scheduled_start && (
                        <p className="mt-1 text-sm text-red-600">{errors.scheduled_start}</p>
                      )}
                    </div>
                    
                    <div>
                      <label htmlFor="scheduled_end" className="block text-sm font-medium text-gray-700">
                        Scheduled End Time
                      </label>
                      <input
                        type="datetime-local"
                        id="scheduled_end"
                        name="scheduled_end"
                        value={formData.scheduled_end || ''}
                        onChange={handleInputChange}
                        min={formData.scheduled_start || getDefaultEndTime()}
                        className={`mt-1 form-input ${errors.scheduled_end ? 'border-red-300 focus:ring-red-500 focus:border-red-500' : ''}`}
                      />
                      {errors.scheduled_end ? (
                        <p className="mt-1 text-sm text-red-600">{errors.scheduled_end}</p>
                      ) : (
                        <p className="mt-1 text-sm text-gray-500">
                          Optional. If not set, capture will continue until manually stopped.
                        </p>
                      )}
                    </div>
                  </div>
                )}
              </div>
              
              {/* Important notes */}
              <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4">
                <div className="flex">
                  <div className="flex-shrink-0">
                    <svg className="h-5 w-5 text-yellow-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                    </svg>
                  </div>
                  <div className="ml-3">
                    <h3 className="text-sm font-medium text-yellow-800">Important Notes</h3>
                    <div className="mt-2 text-sm text-yellow-700">
                      <ul className="list-disc pl-5 space-y-1">
                        <li>Ensure the Parliament TV stream is active before starting capture</li>
                        <li>Capture sessions require sufficient storage space</li>
                        <li>Active captures will continue until manually stopped or scheduled end time</li>
                        <li>You can create multiple clips from a single capture session</li>
                      </ul>
                    </div>
                  </div>
                </div>
              </div>
              
              {/* Submit button */}
              <div className="pt-4">
                <button
                  type="submit"
                  disabled={startCaptureMutation.isPending}
                  className="w-full btn-primary rounded-md px-4 py-2 text-center cursor-pointer inline-block disabled:opacity-50"
                >
                  {startCaptureMutation.isPending ? 'Starting Capture...' : scheduleCapture ? 'Schedule Capture' : 'Start Capture Now'}
                </button>
              </div>
            </div>
          </form>
        </div>
      </div>
    </MainLayout>
  );
};

export default withAuth(NewCapturePage, [UserRole.ADMIN, UserRole.MP, UserRole.STAFF]);
