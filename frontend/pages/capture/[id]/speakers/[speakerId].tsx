import React, { useState, useRef, useEffect } from 'react';
import { useRouter } from 'next/router';
import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import MainLayout from '../../../../components/layout/MainLayout';
import { withAuth } from '../../../../contexts/AuthContext';
import { api } from '../../../../utils/api';

interface Speaker {
  name: string;
  frames: number;
  average_confidence: number;
  metadata?: {
    id: string;
    name: string;
    party: string;
    constituency: string;
  };
}

interface TimelineEntry {
  speaker: string;
  start_time: number;
  end_time: number;
  duration: number;
}

const SpeakerDetailsPage: React.FC = () => {
  const router = useRouter();
  const { id, speakerId } = router.query;
  const videoRef = useRef<HTMLVideoElement>(null);
  const [currentTime, setCurrentTime] = useState(0);
  
  // Fetch speaker identification details
  const {
    data: identification,
    isLoading,
    error
  } = useQuery({
    queryKey: ['speakerIdentification', speakerId],
    queryFn: async () => {
      if (!speakerId) return null;
      return await api.get(`/speakers/${speakerId}`);
    },
    enabled: !!speakerId
  });

  // Format time in seconds to MM:SS
  const formatTime = (seconds: number): string => {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.floor(seconds % 60);
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
  };

  // Jump to a specific time in the video
  const jumpToTime = (time: number) => {
    if (videoRef.current) {
      videoRef.current.currentTime = time;
      videoRef.current.play();
    }
  };

  // Update current time when video is playing
  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;
    
    const updateTime = () => {
      setCurrentTime(video.currentTime);
    };
    
    video.addEventListener('timeupdate', updateTime);
    return () => {
      video.removeEventListener('timeupdate', updateTime);
    };
  }, []);

  // Get color for confidence level
  const getConfidenceColor = (confidence: number): string => {
    if (confidence >= 0.8) return 'text-green-600';
    if (confidence >= 0.6) return 'text-yellow-600';
    return 'text-red-600';
  };

  if (isLoading) {
    return (
      <MainLayout>
        <div className="container mx-auto px-4 py-8">
          <div className="flex justify-center items-center h-64">
            <div className="spinner"></div>
          </div>
        </div>
      </MainLayout>
    );
  }

  if (error || !identification) {
    return (
      <MainLayout>
        <div className="container mx-auto px-4 py-8">
          <div className="bg-red-100 border-l-4 border-red-500 text-red-700 p-4 mb-4">
            <p>Error loading speaker identification data. Please try again.</p>
          </div>
          <button
            onClick={() => router.back()}
            className="bg-gray-200 hover:bg-gray-300 text-gray-800 font-semibold py-2 px-4 rounded"
          >
            Go Back
          </button>
        </div>
      </MainLayout>
    );
  }

  const results = identification.results || {};
  const speakers = results.speakers || {};
  const timeline = results.timeline || [];
  const primarySpeaker = results.primary_speaker || 'Unknown';

  return (
    <MainLayout>
      <div className="container mx-auto px-4 py-8">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-2xl font-bold">Speaker Identification Results</h1>
          <Link href={`/capture/${id}/speakers`}>
            <span className="bg-gray-200 hover:bg-gray-300 text-gray-800 font-semibold py-2 px-4 rounded cursor-pointer">
              Back to Speaker List
            </span>
          </Link>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2">
            <div className="bg-white shadow-md rounded-lg p-6 mb-6">
              <h2 className="text-xl font-semibold mb-4">Video with Speaker Identification</h2>
              {identification.output_file ? (
                <div className="aspect-w-16 aspect-h-9 bg-black mb-4">
                  <video
                    ref={videoRef}
                    src={identification.output_file}
                    controls
                    className="w-full h-full object-contain"
                  />
                </div>
              ) : (
                <div className="bg-gray-100 p-4 rounded text-center">
                  <p>No processed video available</p>
                </div>
              )}
              
              <div className="mt-4">
                <h3 className="text-lg font-medium mb-2">Current Position: {formatTime(currentTime)}</h3>
                <p className="text-sm text-gray-600 mb-2">
                  Click on a timeline entry below to jump to that position in the video.
                </p>
              </div>
            </div>

            <div className="bg-white shadow-md rounded-lg p-6 mb-6">
              <h2 className="text-xl font-semibold mb-4">Speaker Timeline</h2>
              {timeline.length > 0 ? (
                <div className="space-y-2 max-h-96 overflow-y-auto">
                  {timeline.map((entry: TimelineEntry, index: number) => (
                    <div
                      key={index}
                      onClick={() => jumpToTime(entry.start_time)}
                      className="p-3 border rounded hover:bg-gray-50 cursor-pointer transition-colors"
                    >
                      <div className="flex justify-between items-center">
                        <div className="font-medium">{entry.speaker}</div>
                        <div className="text-sm text-gray-500">
                          {formatTime(entry.start_time)} - {formatTime(entry.end_time)} ({formatTime(entry.duration)})
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-gray-500">No timeline data available.</p>
              )}
            </div>
          </div>

          <div className="lg:col-span-1">
            <div className="bg-white shadow-md rounded-lg p-6 mb-6">
              <h2 className="text-xl font-semibold mb-4">Identification Details</h2>
              <div className="space-y-3">
                <div>
                  <span className="font-medium">ID:</span> {identification.id}
                </div>
                <div>
                  <span className="font-medium">Status:</span>{' '}
                  <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                    identification.status === 'completed'
                      ? 'bg-green-100 text-green-800'
                      : identification.status === 'processing'
                      ? 'bg-yellow-100 text-yellow-800'
                      : identification.status === 'pending'
                      ? 'bg-blue-100 text-blue-800'
                      : 'bg-red-100 text-red-800'
                  }`}>
                    {identification.status.charAt(0).toUpperCase() + identification.status.slice(1)}
                  </span>
                </div>
                <div>
                  <span className="font-medium">Created:</span>{' '}
                  {new Date(identification.created_at).toLocaleString()}
                </div>
                <div>
                  <span className="font-medium">Threshold:</span> {identification.threshold}
                </div>
                <div>
                  <span className="font-medium">Primary Speaker:</span> {primarySpeaker}
                </div>
                <div>
                  <span className="font-medium">Total Frames:</span> {results.frame_count || 0}
                </div>
                <div>
                  <span className="font-medium">Processed Frames:</span> {results.processed_frames || 0}
                </div>
              </div>
            </div>

            <div className="bg-white shadow-md rounded-lg p-6">
              <h2 className="text-xl font-semibold mb-4">Detected Speakers</h2>
              {Object.keys(speakers).length > 0 ? (
                <div className="space-y-4">
                  {Object.entries(speakers as Record<string, Speaker>).map(([name, info]) => (
                    <div key={name} className="border rounded p-4">
                      <div className="flex justify-between items-center mb-2">
                        <h3 className="font-medium text-lg">{name}</h3>
                        <span className={`${getConfidenceColor(info.average_confidence)}`}>
                          {(info.average_confidence * 100).toFixed(1)}% confidence
                        </span>
                      </div>
                      <div className="text-sm">
                        <p><span className="font-medium">Frames:</span> {info.frames}</p>
                        {info.metadata && (
                          <>
                            {info.metadata.party && (
                              <p><span className="font-medium">Party:</span> {info.metadata.party}</p>
                            )}
                            {info.metadata.constituency && (
                              <p><span className="font-medium">Constituency:</span> {info.metadata.constituency}</p>
                            )}
                          </>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-gray-500">No speaker data available.</p>
              )}
            </div>
          </div>
        </div>
      </div>
    </MainLayout>
  );
};

export default withAuth(SpeakerDetailsPage);
