import React, { useEffect, useState } from 'react';
import { formatTime } from '../../utils/formatTime';
import { useAuth } from '../../contexts/AuthContext';

// API base URL
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

interface EnhancedViewProps {
  captureId: number;
  audioInfo: any;
  transcriptionData: any;
  integratedTimeline: any;
}

const EnhancedView: React.FC<EnhancedViewProps> = ({ 
  captureId, 
  audioInfo, 
  transcriptionData, 
  integratedTimeline 
}) => {
  const { token } = useAuth();
  const [videoUrl, setVideoUrl] = useState('');
  const [posterUrl, setPosterUrl] = useState('');
  
  useEffect(() => {
    if (audioInfo?.file_path) {
      // Extract filename from the path - format should be capture_XXXX.mp4
      const captureNumber = captureId.toString().padStart(4, '0');
      const filename = `capture_${captureNumber}.mp4`;
      
      // Create authenticated video URL with exact format
      setVideoUrl(`${API_BASE_URL}/videos/stream-with-token/${filename}?token=${token}`);
      
      // Set poster URL to use the new thumbnail endpoint
      setPosterUrl(`${API_BASE_URL}/thumbnail/capture/${captureId}?token=${token}`);
    }
  }, [audioInfo, captureId, token]);
  // Format duration in seconds to HH:MM:SS
  const formatDuration = (seconds: number): string => {
    if (!seconds) return '00:00:00';
    
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    
    return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  if (!transcriptionData || !transcriptionData.segments || transcriptionData.segments.length === 0) {
    return (
      <div className="p-4 border border-gray-700 rounded-lg bg-gray-800/50 text-center">
        {/* Video Player */}
        <div className="mb-6 bg-black rounded-lg overflow-hidden">
          {audioInfo?.file_path && (
            <video 
              controls 
              className="w-full max-h-[400px]" 
              src={videoUrl}
              poster={posterUrl}
            >
              {videoUrl && <source src={videoUrl} type="video/mp4" />}
              Your browser does not support the video tag.
            </video>
          )}
        </div>
        <div className="text-gray-400 p-3 border border-gray-700 rounded-md text-sm">
          No transcription data available for this video.
        </div>
      </div>
    );
  }

  // Get correlation data if available
  const correlations = integratedTimeline?.correlations || [];
  const hasCorrelations = correlations.length > 0;
  
  return (
    <div>
      {/* Video Player */}
      <div className="mb-6 bg-black rounded-lg overflow-hidden">
        {audioInfo?.file_path && (
          <video 
            controls 
            className="w-full max-h-[400px]" 
            src={videoUrl}
            poster={posterUrl}
          >
            {videoUrl && <source src={videoUrl} type="video/mp4" />}
            Your browser does not support the video tag.
          </video>
        )}
      </div>

      <h3 className="text-lg font-medium mb-2 text-white">Transcription Timeline</h3>
      
      {/* Show correlation stats if available */}
      {hasCorrelations && (
        <div className="mb-4 p-3 bg-blue-900 bg-opacity-30 border border-blue-700 rounded-md">
          <h4 className="text-sm font-medium mb-1 text-white">Correlation Statistics</h4>
          <p className="text-xs text-gray-300">
            Found {correlations.length} correlations between face and voice recognition
          </p>
        </div>
      )}
      
      <div className="max-h-80 overflow-y-auto pr-2">
        {transcriptionData.segments.map((segment: any, index: number) => {
          // Find speaker color based on speaker name
          const speakerColor = segment.speaker ? 
            `hsl(${(segment.speaker.charCodeAt(0) * 10) % 360}, 70%, 50%)` : 
            '#6B7280';
          
          // Find any correlations that match this segment's time range
          const matchingCorrelations = hasCorrelations ? correlations.filter((corr: any) => {
            return (segment.start <= corr.end && segment.end >= corr.start);
          }) : [];
          
          // Use a different style if there are matching correlations
          const hasMatches = matchingCorrelations.length > 0;
          const borderColor = hasMatches ? '#10B981' : speakerColor; // Green for matches
          const bgColor = hasMatches ? 'rgba(16, 185, 129, 0.1)' : 'rgba(31, 41, 55, 0.8)';
          
          return (
            <div 
              key={`segment-${segment.id || index}`}
              className="mb-3 p-3 rounded-md border-l-4"
              style={{ borderLeftColor: borderColor, backgroundColor: bgColor }}
            >
              <div className="flex justify-between items-start mb-1">
                <div className="flex items-center">
                  {segment.speaker && (
                    <span 
                      className="px-2 py-1 rounded-md text-xs font-medium mr-2"
                      style={{ backgroundColor: `${speakerColor}30` }}
                    >
                      {segment.speaker}
                    </span>
                  )}
                  <span className="text-gray-400 text-xs">
                    {formatDuration(segment.start)} - {formatDuration(segment.end)}
                  </span>
                </div>
                {segment.confidence && (
                  <span className="text-gray-500 text-xs">
                    {(segment.confidence * 100).toFixed(1)}% confidence
                  </span>
                )}
              </div>
              <p className="text-sm text-white">{segment.text}</p>
              
              {/* Show correlation details if any */}
              {hasMatches && (
                <div className="mt-2 p-2 bg-gray-900 bg-opacity-50 rounded-sm border border-green-800 border-opacity-50">
                  <p className="text-xs font-medium text-green-400">
                    {matchingCorrelations.length} face-voice correlation{matchingCorrelations.length > 1 ? 's' : ''}
                  </p>
                  {matchingCorrelations.map((corr: any, i: number) => (
                    <p key={i} className="text-xs text-gray-400 mt-1">
                      Confidence: {(corr.confidence * 100).toFixed(1)}% 
                      ({formatTime(corr.start)} - {formatTime(corr.end)})
                    </p>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default EnhancedView;
