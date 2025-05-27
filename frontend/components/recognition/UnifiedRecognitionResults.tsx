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
        
        // Extract the actual ID from the generated ID format if needed
        let captureId = videoId;
        if (typeof videoId === 'string') {
          // If it's a generated ID like 'file-123456' or 'video-file-123456'
          if (videoId.startsWith('video-file-')) {
            captureId = videoId.substring(11); // Remove 'video-file-' prefix
          } else if (videoId.startsWith('file-')) {
            captureId = videoId.substring(5); // Remove 'file-' prefix
          }
          
          console.log('Using capture ID for recognition:', captureId);
        }
        
        // Try to fetch the recognition data
        const response = await api.get(`/recognition/timeline/${captureId}`).catch(async (err) => {
          console.log('Error with first recognition attempt:', err);
          
          // If the first attempt fails, try with the original ID
          if (captureId !== videoId) {
            console.log('Trying with original video ID:', videoId);
            return await api.get(`/recognition/timeline/${videoId}`);
          }
          throw err;
        });
        
        // Handle different response formats
        const data = response.data || response;
        console.log('Raw timeline response:', data);
        
        // Validate the response and create a properly structured timeline data object
        // regardless of what the API returns
        
        // First, log the raw response for debugging
        console.log('Raw API response:', data);
        
        // Initialize a valid timeline data structure with defaults
        const validTimelineData: TimelineData = {
          success: true, // Default to success and let validation potentially change it
          video_id: videoId,
          timeline: [],
          correlations: []
        };
        
        // If we have a valid response object
        if (data && typeof data === 'object') {
          // Extract timeline data if available
          if (Array.isArray(data.timeline)) {
            validTimelineData.timeline = data.timeline;
          } else if (data.timeline && typeof data.timeline === 'object') {
            // Handle case where timeline might be an object instead of array
            console.warn('Timeline is an object, not an array. Converting:', data.timeline);
            validTimelineData.timeline = Object.values(data.timeline);
          }
          
          // Extract correlations if available
          if (Array.isArray(data.correlations)) {
            validTimelineData.correlations = data.correlations;
          } else if (data.correlations && typeof data.correlations === 'object') {
            // Handle case where correlations might be an object instead of array
            console.warn('Correlations is an object, not an array. Converting:', data.correlations);
            validTimelineData.correlations = Object.values(data.correlations);
          }
          
          // If we have an explicit error message, mark as not successful
          if (data.error) {
            validTimelineData.success = false;
            console.error('API returned error:', data.error);
          }
        } else if (!data) {
          console.error('Empty response from timeline API');
          validTimelineData.success = false;
        }
        
        // If we have no timeline data at all, this is probably an error
        if (validTimelineData.timeline.length === 0 && validTimelineData.correlations.length === 0) {
          console.warn('No timeline or correlation data found in response');
          // We'll still continue with empty arrays rather than throwing an error
        }
        
        // Process timeline items to ensure all required fields are present
        validTimelineData.timeline = validTimelineData.timeline.map(item => {
          // First, copy the original item properties
          const originalProperties = { ...item };
          
          // Create a new object with defaults for any missing required fields
          const processedItem: TimelineItem = {
            ...originalProperties,
            // Only set defaults if properties are missing
            type: originalProperties.type || ('unknown' as 'face' | 'speaker'),
            id: originalProperties.id || `generated-${Math.random().toString(36).substring(2, 9)}`,
            name: originalProperties.name || 'Unknown',
            start: 0, // Will be overwritten below
            end: 0,   // Will be overwritten below
            confidence: 0 // Will be overwritten below
          };
          
          // Ensure type is valid
          if (processedItem.type !== 'face' && processedItem.type !== 'speaker') {
            console.warn(`Invalid type '${processedItem.type}' for timeline item, defaulting to 'unknown'`);
            processedItem.type = 'unknown' as 'face' | 'speaker';
          }
          
          // Ensure numeric fields are actually numbers
          processedItem.start = typeof originalProperties.start === 'number' ? originalProperties.start : 
                               (typeof originalProperties.start === 'string' ? parseFloat(originalProperties.start) : 0);
          
          processedItem.end = typeof originalProperties.end === 'number' ? originalProperties.end : 
                             (typeof originalProperties.end === 'string' ? parseFloat(originalProperties.end) : 0);
          
          processedItem.confidence = typeof originalProperties.confidence === 'number' ? originalProperties.confidence : 
                                    (typeof originalProperties.confidence === 'string' ? parseFloat(originalProperties.confidence) : 0);
          
          return processedItem;
        });
        
        // Process correlations to ensure all required fields are present
        validTimelineData.correlations = validTimelineData.correlations.map(item => {
          // First, copy the original item properties
          const originalProperties = { ...item };
          
          // Create a new object with defaults for any missing required fields
          return {
            ...originalProperties,
            // Only set defaults if properties are missing
            face_id: originalProperties.face_id || '',
            speaker_id: originalProperties.speaker_id || '',
            face_name: originalProperties.face_name || 'Unknown',
            speaker_name: originalProperties.speaker_name || 'Unknown',
            start: typeof originalProperties.start === 'number' ? originalProperties.start : 0,
            end: typeof originalProperties.end === 'number' ? originalProperties.end : 0,
            confidence: typeof originalProperties.confidence === 'number' ? originalProperties.confidence : 0,
            same_person: originalProperties.same_person !== undefined ? !!originalProperties.same_person : false
          };
        });
        
        setTimelineData(validTimelineData);
        console.log('Timeline data processed and loaded:', validTimelineData);
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
      <div>
        <h2 className="text-lg font-medium mb-4 text-white">Unified Recognition Results</h2>
        <div className="flex justify-center items-center h-32">
          <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-blue-500"></div>
          <span className="ml-3 text-gray-300">Loading recognition data...</span>
        </div>
      </div>
    );
  }
  
  if (error) {
    return (
      <div>
        <h2 className="text-lg font-medium mb-4 text-white">Unified Recognition Results</h2>
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
        {/* No data */}
        {(!timelineData || !timelineData.correlations || timelineData.correlations.length === 0) && (
          <div className="p-6 border border-gray-700 rounded-md bg-gray-800/50 text-center">
            <p className="text-gray-400">No recognition data available for this video.</p>
          </div>
        )}
      </div>
    );
  }
  
  return (
    <div>
      <h2 className="text-lg font-medium mb-4 text-white">Unified Recognition Results</h2>
      
      {/* Correlations */}
      {timelineData && timelineData.correlations && timelineData.correlations.length > 0 && (
        <div className="mb-8">
          <h3 className="text-lg font-medium mb-4 text-white">Face-Voice Correlations</h3>
          
          <div className="bg-blue-900/30 border border-blue-700 rounded-md p-4 mb-6">
            <p className="text-blue-300">
              Found {timelineData.correlations.length} correlations between faces and voices in this video.
            </p>
          </div>
          
          <div className="space-y-4">
            {timelineData.correlations.map((correlation, index) => (
              <div key={`correlation-${index}`} className="border border-gray-700 rounded-lg p-4 bg-gray-800/50">
                <div className="flex flex-col md:flex-row md:items-center justify-between mb-4">
                  <div className="mb-2 md:mb-0">
                    <div className="flex items-center">
                      <span className="bg-purple-900/50 text-purple-300 text-xs font-medium px-2 py-1 rounded mr-2">Face</span>
                      <span className="text-white font-medium">{correlation.face_name || 'Unknown'}</span>
                    </div>
                    <div className="flex items-center mt-2">
                      <span className="bg-blue-900/50 text-blue-300 text-xs font-medium px-2 py-1 rounded mr-2">Voice</span>
                      <span className="text-white font-medium">{correlation.speaker_name || 'Unknown'}</span>
                    </div>
                  </div>
                  
                  <div className="flex items-center">
                    <span className="text-xs font-medium text-gray-400 mr-2">Time: {formatTime(correlation.start)} - {formatTime(correlation.end)}</span>
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${correlation.confidence >= 0.7 ? 'bg-green-900/50 text-green-300' : 'bg-yellow-900/50 text-yellow-300'}`}>
                      {Math.round(correlation.confidence * 100)}% confidence
                    </span>
                  </div>
                </div>
                
                <div className="flex justify-end">
                  <button
                    onClick={() => router.push(`/parliament-tv/captures/${videoId}?t=${Math.floor(correlation.start)}`)}
                    className="bg-blue-600 hover:bg-blue-700 text-white py-1 px-3 rounded text-sm transition-colors"
                  >
                    Jump to {formatTime(correlation.start)}
                  </button>
                </div>
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
                                  if (item.image_path) {
                                    setSelectedImage(item.image_path);
                                    setShowImageModal(true);
                                  }
                                }}
                                onError={(e) => {
                                  console.error(`Error loading image for ${item.name} from path: ${item.image_path}`);
                                  // Instead of using a placeholder, hide the image and show a message
                                  (e.target as HTMLImageElement).style.display = 'none';
                                  const parent = (e.target as HTMLImageElement).parentElement;
                                  if (parent) {
                                    const errorMsg = document.createElement('div');
                                    errorMsg.className = 'bg-gray-800 text-white p-4 text-center rounded';
                                    errorMsg.innerText = 'Image unavailable';
                                    parent.insertBefore(errorMsg, (e.target as HTMLImageElement));
                                  }
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
                  console.error(`Error loading full image from path: ${selectedImage}`);
                  // Instead of using a placeholder, show an error message
                  const parent = (e.target as HTMLImageElement).parentElement;
                  if (parent) {
                    (e.target as HTMLImageElement).style.display = 'none';
                    const errorMsg = document.createElement('div');
                    errorMsg.className = 'bg-gray-800 text-white p-4 text-center rounded';
                    errorMsg.innerText = 'Image could not be loaded';
                    parent.appendChild(errorMsg);
                  }
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
