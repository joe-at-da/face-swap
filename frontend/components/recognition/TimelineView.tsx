import React from 'react';

// Format duration in seconds to HH:MM:SS
const formatDuration = (seconds: number): string => {
  if (!seconds) return '00:00:00';
  
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);
  
  return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
};

interface TimelineViewProps {
  transcriptionData: any;
}

const TimelineView: React.FC<TimelineViewProps> = ({ transcriptionData }) => {
  if (!transcriptionData || !transcriptionData.segments || transcriptionData.segments.length === 0) {
    return (
      <div className="p-6 text-center">
        <p className="text-gray-400">No timeline data available.</p>
      </div>
    );
  }

  return (
    <div className="mt-4">
      <h3 className="text-lg font-medium mb-4 text-white">Timeline</h3>
      <div className="space-y-2 max-h-96 overflow-y-auto pr-2">
        {transcriptionData.segments.map((segment: any, index: number) => (
          <div 
            key={`segment-${index}`}
            className="p-3 border border-gray-700 rounded-md bg-gray-800"
          >
            <div className="flex justify-between mb-1">
              <span className="text-gray-400 text-sm">{formatDuration(segment.start)} - {formatDuration(segment.end)}</span>
              {segment.speaker && (
                <span className="text-blue-400 text-sm">{segment.speaker}</span>
              )}
            </div>
            <p className="text-white">{segment.text}</p>
          </div>
        ))}
      </div>
    </div>
  );
};

export default TimelineView;
