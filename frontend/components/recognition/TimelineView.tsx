import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import { formatTime } from '../../utils/formatTime';

// Format duration in seconds to HH:MM:SS
const formatDuration = (seconds: number): string => {
  if (!seconds) return '00:00:00';
  
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);
  
  return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
};

interface TimelineItem {
  type: 'face' | 'speaker';
  id: string;
  name: string;
  start: number;
  end?: number;
  confidence: number;
  text?: string;
  image_path?: string;
  correlations?: any[];
}

interface TimelineViewProps {
  videoId: string;
  transcriptionData: any;
  integratedTimeline?: any;
}

const TimelineView: React.FC<TimelineViewProps> = ({ videoId, transcriptionData, integratedTimeline }) => {
  const router = useRouter();
  const [combinedTimeline, setCombinedTimeline] = useState<TimelineItem[]>([]);
  const [selectedItem, setSelectedItem] = useState<string | null>(null);
  
  // Combine face detections and speaker segments into a single timeline
  useEffect(() => {
    if (!transcriptionData || !transcriptionData.segments) return;
    
    const timelineItems: TimelineItem[] = [];
    
    // Add speaker segments
    if (transcriptionData.segments && transcriptionData.segments.length > 0) {
      transcriptionData.segments.forEach((segment: any) => {
        timelineItems.push({
          type: 'speaker',
          id: `speaker-${segment.id || Math.random().toString(36).substr(2, 9)}`,
          name: segment.speaker || 'Unknown Speaker',
          start: segment.start,
          end: segment.end,
          confidence: segment.confidence || 0,
          text: segment.text
        });
      });
    }
    
    // Add face detections if available
    if (integratedTimeline?.timeline && integratedTimeline.timeline.length > 0) {
      integratedTimeline.timeline.forEach((item: any) => {
        if (item.type === 'face') {
          timelineItems.push({
            type: 'face',
            id: item.id,
            name: item.name || 'Unknown Face',
            start: item.start,
            end: item.end,
            confidence: item.confidence || 0,
            image_path: item.image_path
          });
        }
      });
    }
    
    // Add correlation information
    if (integratedTimeline?.correlations && integratedTimeline.correlations.length > 0) {
      // Map correlations to timeline items
      timelineItems.forEach(item => {
        const itemCorrelations = integratedTimeline.correlations.filter((corr: any) => {
          if (item.type === 'face') {
            return corr.face_id === item.id;
          } else if (item.type === 'speaker') {
            return corr.speaker_id === item.id;
          }
          return false;
        });
        
        if (itemCorrelations.length > 0) {
          item.correlations = itemCorrelations;
        }
      });
    }
    
    // Sort by start time
    timelineItems.sort((a, b) => a.start - b.start);
    
    setCombinedTimeline(timelineItems);
  }, [transcriptionData, integratedTimeline]);
  
  if (combinedTimeline.length === 0) {
    return (
      <div className="p-6 text-center">
        <p className="text-gray-400">No timeline data available.</p>
      </div>
    );
  }

  const jumpToTimestamp = (timestamp: number) => {
    router.push(`/parliament-tv/captures/${videoId}?t=${Math.floor(timestamp)}`);
  };

  return (
    <div className="mt-4">
      <h3 className="text-lg font-medium mb-4 text-white">Unified Timeline</h3>
      <div className="space-y-2 max-h-96 overflow-y-auto pr-2">
        {combinedTimeline.map((item, index) => {
          const hasCorrelations = item.correlations && item.correlations.length > 0;
          const itemClass = `p-3 border rounded-md ${hasCorrelations ? 'border-green-600 bg-green-900/20' : 'border-gray-700 bg-gray-800'}`;
          
          return (
            <div 
              key={`timeline-${item.id}-${index}`}
              className={itemClass}
              onClick={() => setSelectedItem(selectedItem === item.id ? null : item.id)}
            >
              <div className="flex justify-between mb-1">
                <div className="flex items-center">
                  <span className={`px-2 py-0.5 rounded text-xs mr-2 ${item.type === 'face' ? 'bg-purple-900 text-purple-200' : 'bg-blue-900 text-blue-200'}`}>
                    {item.type === 'face' ? 'Face' : 'Speaker'}
                  </span>
                  <span className="text-white font-medium">{item.name}</span>
                </div>
                <span className="text-gray-400 text-sm">
                  {formatTime(item.start)}{item.end ? ` - ${formatTime(item.end)}` : ''}
                </span>
              </div>
              
              {item.type === 'speaker' && item.text && (
                <p className="text-white text-sm mt-1">{item.text}</p>
              )}
              
              {item.type === 'face' && item.image_path && (
                <div className="mt-2">
                  <img 
                    src={item.image_path} 
                    alt={item.name} 
                    className="h-20 object-cover rounded"
                    onError={(e) => {
                      (e.target as HTMLImageElement).src = '/placeholder-face.png';
                    }}
                  />
                </div>
              )}
              
              {hasCorrelations && selectedItem === item.id && (
                <div className="mt-2 p-2 bg-gray-900 rounded border border-green-700 border-opacity-50">
                  <h4 className="text-sm font-medium text-green-400 mb-1">Correlations</h4>
                  {item.correlations && item.correlations.map((corr: any, i: number) => (
                    <div key={i} className="text-xs text-gray-300 flex justify-between">
                      <span>
                        {item.type === 'face' ? `Voice: ${corr.speaker_name || 'Unknown'}` : `Face: ${corr.face_name || 'Unknown'}`}
                      </span>
                      <span className="text-green-400">{Math.round(corr.confidence * 100)}% match</span>
                    </div>
                  ))}
                </div>
              )}
              
              <div className="mt-2 flex justify-end">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    jumpToTimestamp(item.start);
                  }}
                  className="px-2 py-1 bg-blue-600 hover:bg-blue-700 text-white text-xs rounded transition-colors"
                >
                  Jump to {formatTime(item.start)}
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default TimelineView;
