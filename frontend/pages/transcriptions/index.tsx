import React, { useState } from 'react';
import MainLayout from '../../components/layout/MainLayout';
import { useAuth } from '../../contexts/AuthContext';

const TranscriptionsPage: React.FC = () => {
  const { user } = useAuth();
  const [transcriptions, setTranscriptions] = useState([]);

  return (
    <MainLayout title="Transcriptions | Parliament Video Clip Manager">
      <div className="container mx-auto px-4 py-8">
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Transcriptions</h1>
        </div>

        <div className="bg-white dark:bg-gray-800 shadow rounded-lg p-6">
          <div className="text-center py-12">
            <svg
              className="mx-auto h-16 w-16 text-gray-400 dark:text-gray-500"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
              ></path>
            </svg>
            <h3 className="mt-4 text-lg font-medium text-gray-900 dark:text-white">
              Transcriptions Coming Soon
            </h3>
            <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
              This feature is currently under development. Transcriptions will allow you to view and edit
              automated transcriptions of your video clips.
            </p>
            <div className="mt-6">
              <a
                href="/clips"
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-primary hover:bg-primary-dark focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary"
              >
                Go to Video Clips
              </a>
            </div>
          </div>
        </div>
      </div>
    </MainLayout>
  );
};

export default TranscriptionsPage;
