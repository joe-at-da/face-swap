import React, { useState, useRef, useEffect } from 'react';
import { useRouter } from 'next/router';
import { api } from '../../utils/api';

interface Speaker {
  id: string;
  name: string;
  color: string;
}

interface SpeakerSegment {
  id: string;
  speakerId: string;
  startTime: number;
  endTime: number;
  text: string;
  confidence: number;
}

interface EnhancedVideoPlayerProps {
  captureId: number;
  videoUrl: string;
  onTimeUpdate?: (currentTime: number) => void;
}

const EnhancedVideoPlayer: React.FC<EnhancedVideoPlayerProps> = ({
  captureId,
  videoUrl,
  onTimeUpdate
}) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const timelineRef = useRef<HTMLDivElement>(null);
  const [duration, setDuration] = useState<number>(0);
  const [currentTime, setCurrentTime] = useState<number>(0);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [speakers, setSpeakers] = useState<Speaker[]>([]);
  const [segments, setSegments] = useState<SpeakerSegment[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string>('');
  const [volume, setVolume] = useState<number>(1);
  const [showTranscript, setShowTranscript] = useState<boolean>(true);
  const [activeSpeakerId, setActiveSpeakerId] = useState<string | null>(null);
  
  // Color palette for speakers
  const speakerColors = [
    '#4299E1', // blue-500
    '#48BB78', // green-500
    '#ED8936', // orange-500
    '#9F7AEA', // purple-500
    '#F56565', // red-500
    '#38B2AC', // teal-500
    '#ECC94B', // yellow-500
    '#667EEA', // indigo-500
    '#FC8181', // red-400
    '#4FD1C5', // teal-400
  ];

  useEffect(() => {
    if (captureId) {
      fetchRecognitionData();
    }
  }, [captureId]);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const handleTimeUpdate = () => {
      setCurrentTime(video.currentTime);
      if (onTimeUpdate) {
        onTimeUpdate(video.currentTime);
      }
      
      // Find active speaker segment
      const activeSegment = segments.find(
        seg => video.currentTime >= seg.startTime && video.currentTime <= seg.endTime
      );
      
      if (activeSegment) {
        setActiveSpeakerId(activeSegment.speakerId);
      } else {
        setActiveSpeakerId(null);
      }
    };

    const handleLoadedMetadata = () => {
      setDuration(video.duration);
      setIsLoading(false);
    };

    const handlePlay = () => setIsPlaying(true);
    const handlePause = () => setIsPlaying(false);
    const handleEnded = () => setIsPlaying(false);

    video.addEventListener('timeupdate', handleTimeUpdate);
    video.addEventListener('loadedmetadata', handleLoadedMetadata);
    video.addEventListener('play', handlePlay);
    video.addEventListener('pause', handlePause);
    video.addEventListener('ended', handleEnded);

    return () => {
      video.removeEventListener('timeupdate', handleTimeUpdate);
      video.removeEventListener('loadedmetadata', handleLoadedMetadata);
      video.removeEventListener('play', handlePlay);
      video.removeEventListener('pause', handlePause);
      video.removeEventListener('ended', handleEnded);
    };
  }, [segments, onTimeUpdate]);

  // Helper function to process recognition results data
  const processRecognitionResults = (resultsData: any) => {
    if (!resultsData) {
      console.error('No valid recognition results data to process');
      return;
    }

    try {
      // Process speakers
      const speakersData = resultsData.speakers || [];
      const mappedSpeakers = speakersData.map((speaker: any, index: number) => ({
        id: speaker.id || `speaker-${index}`,
        name: speaker.name || `Speaker ${index + 1}`,
        color: speakerColors[index % speakerColors.length]
      }));
      
      // Process segments
      const segmentsData = resultsData.segments || [];
      const mappedSegments = segmentsData.map((segment: any, index: number) => ({
        id: segment.id || `segment-${index}`,
        speakerId: segment.speaker_id || segment.speakerId || 'unknown',
        startTime: parseFloat(segment.start_time || segment.startTime || 0),
        endTime: parseFloat(segment.end_time || segment.endTime || 0),
        text: segment.text || '',
        confidence: segment.confidence || 1.0
      }));
      
      setSpeakers(mappedSpeakers);
      setSegments(mappedSegments);
    } catch (err) {
      console.error('Error processing recognition results:', err);
    }
  };

  const fetchRecognitionData = async () => {
    // Check if captureId is defined before making API calls
    if (!captureId) {
      console.error('Cannot fetch recognition data: captureId is undefined');
      setError('Missing capture ID');
      setIsLoading(false);
      return;
    }

    try {
      setIsLoading(true);
      
      // First, try to get the detailed status which contains recognition results
      let resultsData = null;
      try {
        const statusResponse = await api.get(`/recognition/detailed-status/${captureId}`);
        const statusData = statusResponse.data || statusResponse;
        
        // Check if the detailed status contains recognition results
        if (statusData && statusData.status && statusData.status.recognition_results) {
          // Handle different formats of recognition results
          if (typeof statusData.status.recognition_results === 'string') {
            try {
              resultsData = JSON.parse(statusData.status.recognition_results);
            } catch (parseErr) {
              console.error('Error parsing recognition results:', parseErr);
              resultsData = { error: 'Failed to parse recognition results' };
            }
          } else {
            resultsData = statusData.status.recognition_results;
          }
        }
      } catch (statusErr) {
        console.log('Detailed status endpoint failed, trying alternative endpoints:', statusErr);
      }
      
      // If no results from detailed status, try the recognition results endpoint
      if (!resultsData) {
        try {
          const resultsResponse = await api.get(`/recognition/results/${captureId}`);
          resultsData = resultsResponse.data || resultsResponse;
        } catch (resultsErr) {
          console.log('Recognition results endpoint failed, trying capture endpoint:', resultsErr);
        }
      }
      
      // If still no results, try to get capture data
      if (!resultsData) {
        try {
          const captureResponse = await api.get(`/capture/${captureId}`);
          const captureData = captureResponse.data || captureResponse;
          
          if (captureData && captureData.recognition_results) {
            // Handle different formats of recognition results
            if (typeof captureData.recognition_results === 'string') {
              try {
                resultsData = JSON.parse(captureData.recognition_results);
              } catch (parseErr) {
                console.error('Error parsing recognition results from capture:', parseErr);
                resultsData = { error: 'Failed to parse recognition results' };
              }
            } else {
              resultsData = captureData.recognition_results;
            }
          }
        } catch (captureErr) {
          console.error('All fallback attempts failed. Error fetching capture data:', captureErr);
        }
      }
      
      // Process the results if we have them
      if (resultsData) {
        // Process speakers
        const speakersData = resultsData.speakers || [];
        const mappedSpeakers = speakersData.map((speaker: any, index: number) => ({
          id: speaker.id || `speaker-${index}`,
          name: speaker.name || `Speaker ${index + 1}`,
          color: speakerColors[index % speakerColors.length]
        }));
        
        // Process segments
        const segmentsData = resultsData.segments || [];
        const mappedSegments = segmentsData.map((segment: any, index: number) => ({
          id: segment.id || `segment-${index}`,
          speakerId: segment.speaker_id || segment.speakerId || 'unknown',
          startTime: parseFloat(segment.start_time || segment.startTime || 0),
          endTime: parseFloat(segment.end_time || segment.endTime || 0),
          text: segment.text || '',
          confidence: segment.confidence || 1.0
        }));
        
        setSpeakers(mappedSpeakers);
        setSegments(mappedSegments);
      } else {
        setError('No recognition data available');
      }
    } catch (err) {
      console.error('Error fetching recognition data:', err);
      setError('Error loading recognition data');
    } finally {
      setIsLoading(false);
    }
  };

  const formatTime = (timeInSeconds: number): string => {
    const hours = Math.floor(timeInSeconds / 3600);
    const minutes = Math.floor((timeInSeconds % 3600) / 60);
    const seconds = Math.floor(timeInSeconds % 60);
    
    return `${hours > 0 ? `${hours}:` : ''}${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
  };

  const handlePlayPause = () => {
    const video = videoRef.current;
    if (!video) return;
    
    if (video.paused) {
      video.play();
    } else {
      video.pause();
    }
  };

  const handleVolumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = parseFloat(e.target.value);
    setVolume(value);
    
    if (videoRef.current) {
      videoRef.current.volume = value;
    }
  };

  const handleTimelineClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!timelineRef.current || !videoRef.current) return;
    
    const rect = timelineRef.current.getBoundingClientRect();
    const clickPosition = (e.clientX - rect.left) / rect.width;
    const newTime = clickPosition * duration;
    
    videoRef.current.currentTime = newTime;
    setCurrentTime(newTime);
  };

  const jumpToSegment = (segment: SpeakerSegment) => {
    if (!videoRef.current) return;
    
    videoRef.current.currentTime = segment.startTime;
    setCurrentTime(segment.startTime);
    
    if (videoRef.current.paused) {
      videoRef.current.play();
    }
  };

  const getSpeakerById = (id: string): Speaker | undefined => {
    return speakers.find(speaker => speaker.id === id);
  };

  return (
    <div className="bg-gray-900 rounded-lg overflow-hidden">
      {/* Video Player */}
      <div className="relative">
        {isLoading && (
          <div className="absolute inset-0 flex items-center justify-center bg-black bg-opacity-50 z-10">
            <div className="spinner"></div>
          </div>
        )}
        
        <video
          ref={videoRef}
          src={videoUrl}
          className="w-full"
          controls={false}
          preload="metadata"
        />
        
        {/* Custom Controls */}
        <div className="absolute bottom-0 left-0 right-0 bg-black bg-opacity-60 p-2">
          {/* Timeline with speaker segments */}
          <div 
            ref={timelineRef}
            className="relative h-8 bg-gray-700 rounded cursor-pointer mb-2"
            onClick={handleTimelineClick}
          >
            {/* Speaker segments */}
            {segments.map(segment => {
              const speaker = getSpeakerById(segment.speakerId);
              const startPercent = (segment.startTime / duration) * 100;
              const widthPercent = ((segment.endTime - segment.startTime) / duration) * 100;
              
              return (
                <div
                  key={segment.id}
                  className="absolute h-full opacity-70 hover:opacity-100 transition-opacity"
                  style={{
                    left: `${startPercent}%`,
                    width: `${widthPercent}%`,
                    backgroundColor: speaker?.color || '#888888',
                    top: 0
                  }}
                  title={`${speaker?.name || 'Unknown'}: ${segment.text}`}
                />
              );
            })}
            
            {/* Current time indicator */}
            <div 
              className="absolute top-0 bottom-0 w-0.5 bg-white z-10"
              style={{ left: `${(currentTime / duration) * 100}%` }}
            />
          </div>
          
          {/* Controls */}
          <div className="flex items-center justify-between">
            <button 
              onClick={handlePlayPause}
              className="text-white p-1 focus:outline-none"
            >
              {isPlaying ? (
                <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 9v6m4-6v6m7-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              ) : (
                <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              )}
            </button>
            
            <div className="text-white text-sm mx-2">
              {formatTime(currentTime)} / {formatTime(duration)}
            </div>
            
            <div className="flex items-center">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15.536a5 5 0 001.414 1.414m2.828-9.9a9 9 0 012.728-2.728" />
              </svg>
              <input
                type="range"
                min="0"
                max="1"
                step="0.01"
                value={volume}
                onChange={handleVolumeChange}
                className="w-20 mx-2"
              />
            </div>
            
            <button 
              onClick={() => setShowTranscript(!showTranscript)}
              className={`text-white p-1 focus:outline-none ${showTranscript ? 'text-blue-400' : ''}`}
              title={showTranscript ? 'Hide transcript' : 'Show transcript'}
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </button>
          </div>
        </div>
      </div>
      
      {/* Transcript Panel */}
      {showTranscript && (
        <div className="max-h-60 overflow-y-auto p-4 bg-gray-800">
          <h3 className="text-white text-lg font-medium mb-3">Transcript</h3>
          
          {segments.length === 0 ? (
            <p className="text-gray-400">No transcript available</p>
          ) : (
            <div className="space-y-4">
              {segments.map(segment => {
                const speaker = getSpeakerById(segment.speakerId);
                const isActive = activeSpeakerId === segment.speakerId;
                
                return (
                  <div 
                    key={segment.id}
                    className={`p-2 rounded ${isActive ? 'bg-gray-700' : ''}`}
                    onClick={() => jumpToSegment(segment)}
                  >
                    <div className="flex items-center mb-1">
                      <div 
                        className="w-3 h-3 rounded-full mr-2" 
                        style={{ backgroundColor: speaker?.color || '#888888' }}
                      />
                      <span className="text-gray-300 text-sm font-medium">
                        {speaker?.name || 'Unknown Speaker'}
                      </span>
                      <span className="text-gray-500 text-xs ml-2">
                        {formatTime(segment.startTime)} - {formatTime(segment.endTime)}
                      </span>
                    </div>
                    <p className="text-white">{segment.text}</p>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
      
      <style jsx>{`
        .spinner {
          border: 4px solid rgba(255, 255, 255, 0.1);
          width: 36px;
          height: 36px;
          border-radius: 50%;
          border-left-color: #3b82f6;
          animation: spin 1s linear infinite;
        }
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
        
        input[type=range] {
          -webkit-appearance: none;
          background: transparent;
        }
        
        input[type=range]::-webkit-slider-thumb {
          -webkit-appearance: none;
          height: 12px;
          width: 12px;
          border-radius: 50%;
          background: #3b82f6;
          cursor: pointer;
          margin-top: -4px;
        }
        
        input[type=range]::-webkit-slider-runnable-track {
          width: 100%;
          height: 4px;
          cursor: pointer;
          background: #4b5563;
          border-radius: 2px;
        }
      `}</style>
    </div>
  );
};

export default EnhancedVideoPlayer;
