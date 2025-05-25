import React, { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/router';
import { formatTime } from '../../utils/formatTime';
import { api } from '../../utils/api';
import { Tooltip } from '@chakra-ui/react';

interface TimelineItem {
  type: 'face' | 'speaker';
  id: string;
  person_id?: string;
  name: string;
  start: number;
  end: number;
  confidence: number;
  image_path?: string;
  text?: string;
}

interface Correlation {
  face_id: string;
  speaker_id: string;
  face_name: string;
  speaker_name: string;
  start: number;
  end: number;
  confidence: number;
  confidence_level?: 'very_low' | 'low' | 'medium' | 'high' | 'very_high';
  same_person: boolean;
  match_type?: 'explicit_id' | 'name_similarity';
  name_similarity?: number;
  factors?: {
    boosters: Record<string, number>;
    penalties: Record<string, number>;
    face_confidence: number;
    speaker_confidence: number;
    base_combined: number;
  };
}

interface TimelineData {
  success: boolean;
  video_id: string;
  timeline: TimelineItem[];
  correlations: Correlation[];
}

interface UnifiedTimelineProps {
  videoId: string;
  currentTime: number;
  onSeek: (time: number) => void;
  videoDuration: number;
}

const UnifiedRecognitionTimeline: React.FC<UnifiedTimelineProps> = ({ 
  videoId, 
  currentTime, 
  onSeek,
  videoDuration
}) => {
  const [timelineData, setTimelineData] = useState<TimelineData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | undefined>();
  const [scale, setScale] = useState(100); // pixels per second
  const [hoveredItem, setHoveredItem] = useState<TimelineItem | null>(null);
  const timelineRef = useRef<HTMLDivElement>(null);
  const router = useRouter();
  
  // Fetch timeline data
  useEffect(() => {
    const fetchTimelineData = async () => {
      if (!videoId) return;
      
      try {
        setIsLoading(true);
        const response = await api.get(`/recognition/timeline/${videoId}`);
        
        // Handle different response formats
        const data = response.data || response;
        
        if (!data.success) {
          throw new Error(data.error || 'Failed to fetch timeline data');
        }
        
        setTimelineData(data);
        console.log('Timeline data loaded:', data);
      } catch (err) {
        console.error('Error loading timeline data:', err);
        setError('Error loading recognition data. Please try again.');
      } finally {
        setIsLoading(false);
      }
    };
    
    fetchTimelineData();
  }, [videoId]);
  
  // Group items by person
  const personGroups = React.useMemo(() => {
    if (!timelineData?.timeline) return {};
    
    return timelineData.timeline.reduce((groups: any, item) => {
      const personId = item.person_id || item.id;
      if (!groups[personId]) {
        groups[personId] = {
          personId,
          name: item.name,
          items: []
        };
      }
      groups[personId].items.push(item);
      return groups;
    }, {});
  }, [timelineData]);
  
  // Process correlations
  const correlationsByFaceId = React.useMemo(() => {
    if (!timelineData?.correlations) return {};
    
    return timelineData.correlations.reduce((acc: Record<string, Correlation[]>, correlation) => {
      if (!acc[correlation.face_id]) {
        acc[correlation.face_id] = [];
      }
      acc[correlation.face_id].push(correlation);
      return acc;
    }, {});
  }, [timelineData]);
  
  // Calculate timeline width
  const timelineWidth = videoDuration * scale;
  
  // Handle timeline click
  const handleTimelineClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!timelineRef.current) return;
    
    const rect = timelineRef.current.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const clickedTime = (clickX / rect.width) * videoDuration;
    
    onSeek(clickedTime);
  };
  
  // Convert time to position
  const timeToPosition = (time: number) => {
    return `${(time / videoDuration) * 100}%`;
  };
  
  // Handle zoom in/out
  const handleZoomIn = () => {
    setScale(prev => Math.min(prev * 1.5, 500));
  };
  
  const handleZoomOut = () => {
    setScale(prev => Math.max(prev / 1.5, 20));
  };
  
  if (isLoading) {
    return (
      <div className="bg-white dark:bg-gray-900 rounded-lg shadow-md p-6 mb-6">
        <h3 className="text-lg font-semibold mb-4 dark:text-white">Recognition Timeline</h3>
        <div className="flex justify-center items-center h-32">
          <p className="text-gray-500 dark:text-gray-400">Loading recognition data...</p>
        </div>
      </div>
    );
  }
  
  if (error) {
    return (
      <div className="bg-white dark:bg-gray-900 rounded-lg shadow-md p-6 mb-6">
        <h3 className="text-lg font-semibold mb-4 dark:text-white">Recognition Timeline</h3>
        <div className="flex justify-center items-center h-32">
          <p className="text-red-500">{error}</p>
        </div>
      </div>
    );
  }
  
  if (!timelineData || timelineData.timeline.length === 0) {
    return (
      <div className="bg-white dark:bg-gray-900 rounded-lg shadow-md p-6 mb-6">
        <h3 className="text-lg font-semibold mb-4 dark:text-white">Recognition Timeline</h3>
        <div className="flex justify-center items-center h-32">
          <p className="text-gray-500 dark:text-gray-400">No recognition data available for this video.</p>
        </div>
      </div>
    );
  }
  
  return (
    <div className="bg-white dark:bg-gray-900 rounded-lg shadow-md p-6 mb-6">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold dark:text-white">Recognition Timeline</h3>
        <div className="flex space-x-2">
          <button 
            onClick={handleZoomOut}
            className="bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-200 px-2 py-1 rounded"
          >
            Zoom Out
          </button>
          <button 
            onClick={handleZoomIn}
            className="bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-200 px-2 py-1 rounded"
          >
            Zoom In
          </button>
        </div>
      </div>
      
      <div className="relative overflow-x-auto" style={{ height: Object.keys(personGroups).length * 60 + 40 }}>
        {/* Timeline header */}
        <div className="sticky top-0 bg-white dark:bg-gray-900 z-10 border-b border-gray-200 dark:border-gray-700 pb-2">
          <div className="flex">
            <div className="w-32 flex-shrink-0 pr-2 font-medium dark:text-white">Person</div>
            <div 
              ref={timelineRef}
              className="relative flex-grow" 
              style={{ minWidth: '100%', width: timelineWidth }}
              onClick={handleTimelineClick}
            >
              {/* Time markers */}
              {Array.from({ length: Math.ceil(videoDuration / 60) + 1 }).map((_, i) => (
                <div 
                  key={i} 
                  className="absolute top-0 bottom-0 border-l border-gray-300 dark:border-gray-700"
                  style={{ left: timeToPosition(i * 60) }}
                >
                  <div className="text-xs text-gray-500 dark:text-gray-400 ml-1">
                    {formatTime(i * 60)}
                  </div>
                </div>
              ))}
              
              {/* Current time indicator */}
              <div 
                className="absolute top-0 bottom-0 w-0.5 bg-red-500 z-20"
                style={{ left: timeToPosition(currentTime) }}
              />
            </div>
          </div>
        </div>
        
        {/* Timeline rows */}
        <div className="mt-2">
          {Object.values(personGroups).map((group: any) => (
            <div key={group.personId} className="flex mb-2">
              <div className="w-32 flex-shrink-0 pr-2 text-sm font-medium dark:text-white truncate">
                {group.name}
              </div>
              <div 
                className="relative flex-grow" 
                style={{ height: 40, minWidth: '100%', width: timelineWidth }}
              >
                {/* Face items */}
                {group.items.filter((item: TimelineItem) => item.type === 'face').map((item: TimelineItem, index: number) => {
                  const correlations = correlationsByFaceId[item.id] || [];
                  const hasCorrelation = correlations.length > 0;
                  const highConfidenceCorrelation = correlations.find(c => 
                    c.confidence_level === 'high' || c.confidence_level === 'very_high'
                  );
                  
                  // Determine border color based on correlation confidence
                  let borderColor = '';
                  if (hasCorrelation) {
                    if (highConfidenceCorrelation) {
                      borderColor = 'border-yellow-400 dark:border-yellow-500';
                    } else {
                      borderColor = 'border-purple-400 dark:border-purple-500';
                    }
                  }
                  
                  return (
                    <div
                      key={`face-${item.id}-${index}`}
                      className={`absolute h-4 bg-blue-400 dark:bg-blue-600 rounded-sm cursor-pointer z-10 top-0 ${hasCorrelation ? 'border-2 ' + borderColor : ''}`}
                      style={{ 
                        left: timeToPosition(item.start),
                        width: `calc(${timeToPosition(item.end - item.start)})`,
                        opacity: 0.7 + (item.confidence * 0.3)
                      }}
                      onClick={() => onSeek(item.start)}
                      onMouseEnter={() => setHoveredItem(item)}
                      onMouseLeave={() => setHoveredItem(null)}
                    >
                      {hasCorrelation && (
                        <div className="absolute -top-1 -right-1 w-2 h-2 rounded-full bg-yellow-500" 
                             title="Has correlation with speaker"/>
                      )}
                    </div>
                  );
                })}
                
                {/* Speaker items */}
                {group.items.filter((item: TimelineItem) => item.type === 'speaker').map((item: TimelineItem, index: number) => {
                  // Find correlations where this speaker is mentioned
                  const relatedCorrelations = timelineData?.correlations?.filter(c => c.speaker_id === item.id) || [];
                  const hasCorrelation = relatedCorrelations.length > 0;
                  const highConfidenceCorrelation = relatedCorrelations.find(c => 
                    c.confidence_level === 'high' || c.confidence_level === 'very_high'
                  );
                  
                  // Determine border color based on correlation confidence
                  let borderColor = '';
                  if (hasCorrelation) {
                    if (highConfidenceCorrelation) {
                      borderColor = 'border-yellow-400 dark:border-yellow-500';
                    } else {
                      borderColor = 'border-purple-400 dark:border-purple-500';
                    }
                  }
                  
                  return (
                    <div
                      key={`speaker-${item.id}-${index}`}
                      className={`absolute h-4 bg-green-400 dark:bg-green-600 rounded-sm cursor-pointer z-10 bottom-0 ${hasCorrelation ? 'border-2 ' + borderColor : ''}`}
                      style={{ 
                        left: timeToPosition(item.start),
                        width: `calc(${timeToPosition(item.end - item.start)})`,
                        opacity: 0.7 + (item.confidence * 0.3)
                      }}
                      onClick={() => onSeek(item.start)}
                      onMouseEnter={() => setHoveredItem(item)}
                      onMouseLeave={() => setHoveredItem(null)}
                    >
                      {hasCorrelation && (
                        <div className="absolute -bottom-1 -right-1 w-2 h-2 rounded-full bg-yellow-500" 
                             title="Has correlation with face"/>
                      )}
                    </div>
                  );
                })}
                
                {/* Correlation lines */}
                {timelineData?.correlations?.map((correlation, index) => {
                  // Find the face and speaker items
                  const faceItem = timelineData.timeline.find(item => 
                    item.type === 'face' && item.id === correlation.face_id
                  );
                  const speakerItem = timelineData.timeline.find(item => 
                    item.type === 'speaker' && item.id === correlation.speaker_id
                  );
                  
                  if (!faceItem || !speakerItem) return null;
                  
                  // Determine line color based on confidence level
                  let lineColor = '';
                  let lineOpacity = 0.5;
                  
                  switch(correlation.confidence_level) {
                    case 'very_high':
                      lineColor = 'rgba(234, 179, 8, 0.8)'; // yellow-500
                      lineOpacity = 0.9;
                      break;
                    case 'high':
                      lineColor = 'rgba(234, 179, 8, 0.6)'; // yellow-500
                      lineOpacity = 0.8;
                      break;
                    case 'medium':
                      lineColor = 'rgba(168, 85, 247, 0.6)'; // purple-500
                      lineOpacity = 0.7;
                      break;
                    case 'low':
                      lineColor = 'rgba(168, 85, 247, 0.4)'; // purple-500
                      lineOpacity = 0.6;
                      break;
                    default:
                      lineColor = 'rgba(168, 85, 247, 0.3)'; // purple-500
                      lineOpacity = 0.5;
                  }
                  
                  // Only show if correlation is reasonably confident
                  if (correlation.confidence < 0.4) return null;
                  
                  // Calculate positions
                  const faceStart = faceItem.start;
                  const speakerStart = speakerItem.start;
                  const facePos = timeToPosition(faceStart);
                  const speakerPos = timeToPosition(speakerStart);
                  
                  // Draw a line or connector between the two items
                  return (
                    <div 
                      key={`correlation-${index}`}
                      className="absolute h-full w-0.5 z-5"
                      style={{ 
                        left: timeToPosition(correlation.start),
                        backgroundColor: lineColor,
                        opacity: lineOpacity
                      }}
                      onMouseEnter={() => {
                        // Create a virtual item for the tooltip
                        setHoveredItem({
                          type: 'face', // Doesn't matter
                          id: `correlation-${index}`,
                          name: `Correlation: ${correlation.face_name} (face) & ${correlation.speaker_name} (voice)`,
                          start: correlation.start,
                          end: correlation.end,
                          confidence: correlation.confidence,
                          text: `Confidence: ${(correlation.confidence * 100).toFixed(1)}% - ${correlation.confidence_level || 'unknown'}
${correlation.match_type === 'explicit_id' ? 'Matched by ID' : 'Matched by name similarity'}
${correlation.name_similarity ? `Name similarity: ${(correlation.name_similarity * 100).toFixed(1)}%` : ''}`
                        });
                      }}
                      onMouseLeave={() => setHoveredItem(null)}
                    />
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      </div>
      
      {/* Tooltip */}
      {hoveredItem && (
        <div className="fixed bg-white dark:bg-gray-800 shadow-lg rounded p-2 z-50 max-w-xs">
          <div className="font-medium dark:text-white">{hoveredItem.name}</div>
          <div className="text-sm text-gray-500 dark:text-gray-400">
            {formatTime(hoveredItem.start)} - {formatTime(hoveredItem.end)}
          </div>
          {hoveredItem.type === 'speaker' && hoveredItem.text && (
            <div className="text-sm mt-1 dark:text-gray-300">"{hoveredItem.text}"</div>
          )}
          {hoveredItem.type === 'face' && hoveredItem.image_path && (
            <div className="mt-1">
              <img 
                src={hoveredItem.image_path} 
                alt={hoveredItem.name} 
                className="w-24 h-24 object-contain"
              />
            </div>
          )}
        </div>
      )}
      
      <div className="flex items-center mt-2 flex-wrap">
        <div className="flex items-center mr-4 mb-1">
          <div className="w-4 h-4 bg-blue-400 dark:bg-blue-600 rounded-sm mr-1"></div>
          <span className="text-sm text-gray-600 dark:text-gray-400">Face Detection</span>
        </div>
        <div className="flex items-center mr-4 mb-1">
          <div className="w-4 h-4 bg-green-400 dark:bg-green-600 rounded-sm mr-1"></div>
          <span className="text-sm text-gray-600 dark:text-gray-400">Voice Detection</span>
        </div>
        <div className="flex items-center mr-4 mb-1">
          <div className="w-4 h-4 bg-yellow-500 opacity-80 rounded-sm mr-1"></div>
          <span className="text-sm text-gray-600 dark:text-gray-400">High Confidence Correlation</span>
        </div>
        <div className="flex items-center mr-4 mb-1">
          <div className="w-4 h-4 bg-purple-500 opacity-60 rounded-sm mr-1"></div>
          <span className="text-sm text-gray-600 dark:text-gray-400">Medium/Low Confidence Correlation</span>
        </div>
        <div className="flex items-center mb-1">
          <div className="w-2 h-2 bg-yellow-500 rounded-full mr-1"></div>
          <span className="text-sm text-gray-600 dark:text-gray-400">Correlated Event</span>
        </div>
      </div>
    </div>
  );
};

export default UnifiedRecognitionTimeline;
