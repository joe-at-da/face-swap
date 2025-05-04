import React, { useState } from 'react';
import MainLayout from '../components/layout/MainLayout';
import AudioPlayer from '../components/AudioPlayer';
import { withAuth } from '../contexts/AuthContext';
import { UserRole } from '../contexts/AuthContext';

const AudioTestPage: React.FC = () => {
  const [audioUrl, setAudioUrl] = useState<string>('');
  
  // API base URL for streaming
  const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api';
  
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setAudioUrl(e.target.value);
  };

  return (
    <MainLayout title="Audio Player Test | Parliament Video Clip Manager">
      <div className="container mx-auto p-6">
        <h1 className="text-2xl font-bold mb-4">Audio Player Test</h1>
        
        <div className="bg-white shadow-md rounded-lg p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">Test Audio Player</h2>
          <p className="text-gray-600 mb-4">
            Enter an audio file URL to test the audio player component.
          </p>
          
          <div className="mb-4">
            <label htmlFor="audioUrl" className="block text-sm font-medium text-gray-700 mb-1">
              Audio URL
            </label>
            <input
              type="text"
              id="audioUrl"
              value={audioUrl}
              onChange={handleInputChange}
              placeholder="Enter audio URL"
              className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
            />
          </div>
          
          {audioUrl && (
            <div className="mt-4">
              <h3 className="text-lg font-medium mb-2">Audio Player</h3>
              <AudioPlayer 
                audioUrl={audioUrl}
                title="Test Audio"
              />
            </div>
          )}
        </div>
        
        <div className="bg-white shadow-md rounded-lg p-6">
          <h2 className="text-xl font-semibold mb-4">Sample Audio Files</h2>
          <p className="text-gray-600 mb-4">
            Click on any of the following sample audio files to test:
          </p>
          
          <ul className="space-y-2">
            <li>
              <button
                onClick={() => setAudioUrl(`${API_BASE_URL}/videos/static/audio/sample1.mp3`)}
                className="text-blue-600 hover:text-blue-800"
              >
                Sample 1
              </button>
            </li>
            <li>
              <button
                onClick={() => setAudioUrl(`${API_BASE_URL}/videos/static/audio/sample2.mp3`)}
                className="text-blue-600 hover:text-blue-800"
              >
                Sample 2
              </button>
            </li>
            <li>
              <button
                onClick={() => setAudioUrl('https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3')}
                className="text-blue-600 hover:text-blue-800"
              >
                External Sample (SoundHelix)
              </button>
            </li>
          </ul>
        </div>
      </div>
    </MainLayout>
  );
};

export default withAuth(AudioTestPage, [UserRole.ADMIN, UserRole.MP, UserRole.STAFF]);
