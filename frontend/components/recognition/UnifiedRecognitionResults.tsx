import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import { formatTime } from '../../utils/formatTime';
import { api } from '../../utils/api';
import { useAuth } from '../../contexts/AuthContext';

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
  same_person: boolean;
}

interface TimelineData {
  success: boolean;
  video_id: string;
  timeline: TimelineItem[];
  correlations: Correlation[];
}

interface UnifiedResultsProps {
  videoId: string;
}

const UnifiedRecognitionResults: React.FC<UnifiedResultsProps> = ({ videoId }) => {
  const [timelineData, setTimelineData] = useState<TimelineData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | undefined>();
  const [selectedImage, setSelectedImage] = useState<string | null>(null);
  const [showImageModal, setShowImageModal] = useState(false);
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
        console.log('Raw timeline response:', data);
        
        // Handle the case where we only have correlations but no success flag
        if (data && data.correlations && !data.success) {
          // Create a valid timeline data structure with the correlations
          const validData = {
            success: true, // Assume success if we have correlations
            video_id: videoId,
            timeline: [],
            correlations: Array.isArray(data.correlations) ? data.correlations : []
          };
          
          setTimelineData(validData);
          console.log('Timeline data loaded with correlations only:', validData);
          return;
        }
        
        if (!data || !data.success) {
          throw new Error(data?.error || 'Failed to fetch timeline data');
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
  
  // Group timeline items by person
  const personGroups = React.useMemo(() => {
    if (!timelineData?.timeline) return {};
    
    return timelineData.timeline.reduce((groups: any, item) => {
      const personId = item.person_id || item.id;
      if (!groups[personId]) {
        groups[personId] = {
          personId,
          name: item.name,
          faceItems: [],
          speakerItems: []
        };
      }
      
      if (item.type === 'face') {
        groups[personId].faceItems.push(item);
      } else if (item.type === 'speaker') {
        groups[personId].speakerItems.push(item);
      }
      
      return groups;
    }, {});
  }, [timelineData]);
  
  if (isLoading) {
    return (
      <div className="bg-white dark:bg-gray-900 rounded-lg shadow-md p-6 mb-6">
        <h2 className="text-xl font-semibold mb-4 dark:text-white">Unified Recognition Results</h2>
        <div className="flex justify-center items-center h-32">
          <p className="text-gray-500 dark:text-gray-400">Loading recognition data...</p>
        </div>
      </div>
    );
  }
  
  if (error) {
    return (
      <div className="bg-white dark:bg-gray-900 rounded-lg shadow-md p-6 mb-6">
        <h2 className="text-xl font-semibold mb-4 dark:text-white">Unified Recognition Results</h2>
        <div className="flex justify-center items-center h-32">
          <p className="text-red-500">{error}</p>
        </div>
      </div>
    );
  }
  
  // Check if we have any data to display
  const hasTimelineData = timelineData?.timeline && timelineData.timeline.length > 0;
  const hasCorrelationData = timelineData?.correlations && timelineData.correlations.length > 0;
  
  if (!timelineData || (!hasTimelineData && !hasCorrelationData)) {
    return (
      <div className="bg-white dark:bg-gray-900 rounded-lg shadow-md p-6 mb-6">
        <h2 className="text-xl font-semibold mb-4 dark:text-white">Unified Recognition Results</h2>
        <div className="flex justify-center items-center h-32">
          <p className="text-gray-500 dark:text-gray-400">No recognition data available for this video.</p>
        </div>
      </div>
    );
  }
  
  return (
    <div className="bg-white dark:bg-gray-900 rounded-lg shadow-md p-6 mb-6">
      <h2 className="text-xl font-semibold mb-4 dark:text-white">Unified Recognition Results</h2>
      
      {/* Display correlations if available */}
      {hasCorrelationData && (
        <div className="mb-6">
          <h3 className="text-lg font-semibold mb-3 dark:text-white">Face-Voice Correlations</h3>
          <div className="bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-800 rounded-lg p-4 mb-4">
            <p className="text-blue-800 dark:text-blue-300 text-sm">
              Found {timelineData.correlations.length} correlations between faces and voices in this video.
            </p>
          </div>
          
          <div className="space-y-3">
            {timelineData.correlations.map((correlation, index) => (
              <div key={`correlation-${index}`} className="border border-gray-200 dark:border-gray-700 rounded-lg p-4 bg-white dark:bg-gray-800">
                <div className="flex justify-between mb-2">
                  <div>
                    <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                      Face: {correlation.face_name || 'Unknown'}
                    </span>
                    <span className="mx-2 text-gray-400">→</span>
                    <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                      Voice: {correlation.speaker_name || 'Unknown'}
                    </span>
                  </div>
                  <span className="text-xs px-2 py-1 rounded-full bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-300">
                    {Math.round(correlation.confidence * 100)}% confidence
                  </span>
                </div>
                <div className="text-xs text-gray-500 dark:text-gray-400">
                  Time: {formatTime(correlation.start)} - {formatTime(correlation.end)}
                </div>
                <button
                  onClick={() => router.push(`/parliament-tv/captures/${videoId}?t=${Math.floor(correlation.start)}`)}
                  className="mt-2 bg-blue-500 hover:bg-blue-600 dark:bg-blue-600 dark:hover:bg-blue-700 text-white text-xs py-1 px-2 rounded transition-colors"
                >
                  Jump to {formatTime(correlation.start)}
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
      
      {/* Display person groups if available */}
      {hasTimelineData && (
        <div className="space-y-6">
          {Object.values(personGroups).map((group: any) => (
            <div key={group.personId} className="border border-gray-200 dark:border-gray-700 rounded-md p-4">
              <h3 className="text-lg font-medium mb-2 dark:text-white">{group.name}</h3>
              
              <div className="space-y-4">
                {/* Face appearances */}
                {group.faceItems.length > 0 && (
                  <div>
                    <h4 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2">
                      Appearances ({group.faceItems.length})
                    </h4>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      {group.faceItems.map((item: TimelineItem, index: number) => (
                        <div key={`${item.id}-${index}`} className="border border-gray-200 dark:border-gray-700 rounded p-2">
                          {item.image_path && (
                            <div className="mb-2">
                              <img 
                                src={item.image_path} 
                                alt={`${item.name} at ${formatTime(item.start)}`}
                                className="w-full h-32 object-contain rounded cursor-pointer"
                                onClick={() => {
                                  setSelectedImage(item.image_path || null);
                                  setShowImageModal(true);
                                }}
                                onError={(e) => {
                                  console.error(`Error loading image: ${item.image_path}`);
                                  (e.target as HTMLImageElement).src = '/placeholder-face.png';
                                }}
                              />
                            </div>
                          )}
                          <div className="text-sm">
                            <p className="text-gray-700 dark:text-gray-300">
                              Time: {formatTime(item.start)}
                            </p>
                            <p className="text-gray-500 dark:text-gray-400">
                              Confidence: {Math.round(item.confidence * 100)}%
                            </p>
                            <button
                              onClick={() => router.push(`/parliament-tv/captures/${videoId}?t=${Math.floor(item.start)}`)}
                              className="mt-2 bg-blue-500 hover:bg-blue-600 dark:bg-blue-600 dark:hover:bg-blue-700 text-white text-sm py-1 px-3 rounded transition-colors"
                            >
                              Jump to {formatTime(item.start)}
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                
                {/* Speaker segments */}
                {group.speakerItems.length > 0 && (
                  <div>
                    <h4 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2">
                      Speech Segments ({group.speakerItems.length})
                    </h4>
                    <div className="space-y-2">
                      {group.speakerItems.map((item: TimelineItem, index: number) => (
                        <div key={`${item.id}-${index}`} className="border border-gray-200 dark:border-gray-700 rounded p-3">
                          <p className="text-gray-700 dark:text-gray-300 mb-1">
                            {item.text || "No transcription available"}
                          </p>
                          <div className="flex justify-between text-sm">
                            <span className="text-gray-500 dark:text-gray-400">
                              {formatTime(item.start)} - {formatTime(item.end)}
                            </span>
                            <span className="text-gray-500 dark:text-gray-400">
                              {item.confidence > 0 && `Confidence: ${Math.round(item.confidence * 100)}%`}
                            </span>
                          </div>
                          <button
                            onClick={() => router.push(`/parliament-tv/captures/${videoId}?t=${Math.floor(item.start)}`)}
                            className="mt-2 bg-blue-500 hover:bg-blue-600 dark:bg-blue-600 dark:hover:bg-blue-700 text-white text-sm py-1 px-3 rounded transition-colors"
                          >
                            Jump to {formatTime(item.start)}
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
      
      {/* Full Image Modal */}
      {showImageModal && selectedImage && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-75" onClick={() => setShowImageModal(false)}>
          <div className="relative bg-white dark:bg-gray-900 p-2 rounded-lg max-w-4xl max-h-[90vh] w-[90vw] overflow-hidden">
            <button 
              className="absolute top-2 right-2 bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-white rounded-full w-8 h-8 flex items-center justify-center"
              onClick={(e) => {
                e.stopPropagation();
                setShowImageModal(false);
              }}
            >
              ✕
            </button>
            <div className="mt-8 w-full h-[calc(90vh-4rem)] flex items-center justify-center">
              <img 
                src={selectedImage} 
                alt="Full face image" 
                className="max-w-full max-h-full object-contain"
                onError={(e) => {
                  console.error(`Error loading full image`);
                  (e.target as HTMLImageElement).src = '/placeholder-face.png';
                }}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default UnifiedRecognitionResults;
