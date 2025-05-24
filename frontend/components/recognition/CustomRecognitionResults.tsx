import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import { formatTime } from '../../utils/formatTime';

interface Speaker {
  name: string;
  confidence: number;
  start_time: number;
  end_time: number;
  duration: number;
  image_url?: string;
}

interface UnidentifiedFace {
  id: string;
  filename: string;
  start_time: number;
  end_time: number;
  duration: number;
  timestamp?: number;
}

interface RecognitionResultsProps {
  videoId: number;
  speakerResults?: {
    speakers: Speaker[];
    unidentified_faces?: UnidentifiedFace[];
    unidentified_dir?: string;
    processing_info?: {
      faces_detected?: number;
      [key: string]: any;
    };
    [key: string]: any;
  };
  transcriptionText?: string;
  isLoading?: boolean;
  error?: string;
}

const CustomRecognitionResults: React.FC<RecognitionResultsProps> = ({ 
  videoId, 
  speakerResults, 
  transcriptionText, 
  isLoading = false,
  error
}) => {
  const router = useRouter();
  const [displayUnidentifiedFaces, setDisplayUnidentifiedFaces] = useState<UnidentifiedFace[]>([]);
  const [selectedImage, setSelectedImage] = useState<string | null>(null);
  const [showImageModal, setShowImageModal] = useState(false);
  const [speakers, setSpeakers] = useState<Speaker[]>([]);
  const [facesDetected, setFacesDetected] = useState<number | undefined>(undefined);
  
  // Get the API base URL from environment or use default
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
  
  // Function to generate image URLs for unidentified faces
  const getUnidentifiedFaceImageUrl = (face: UnidentifiedFace): string => {
    // Extract the capture ID from the URL
    const captureIdMatch = window.location.pathname.match(/\/recognition\/results\/(\d+)/);
    const captureId = captureIdMatch ? captureIdMatch[1] : '';
    console.log(`Extracted capture ID from URL: ${captureId}`);
    
    // Get the backend URL directly
    const backendUrl = 'http://localhost:8000/api/v1';
    
    // If we have a capture ID, use the direct backend URL
    if (captureId && face.filename) {
      // Use the direct backend URL
      const url = `${backendUrl}/recognition/unidentified/${captureId}/${encodeURIComponent(face.filename)}`;
      console.log(`Generated direct backend URL: ${url}`);
      return url;
    }
    
    // Fallback: try to use the unidentified_dir if available
    if (speakerResults?.unidentified_dir && face.filename) {
      // If it's a server-side path, convert it to an API endpoint
      if (speakerResults.unidentified_dir.startsWith('/app/') || 
          speakerResults.unidentified_dir.startsWith('/data/')) {
        // Extract the capture ID from the path if possible
        const match = speakerResults.unidentified_dir.match(/capture_(\d+)/);
        const dirCaptureId = match ? match[1] : '';
        
        if (dirCaptureId) {
          // Use direct backend URL
          const url = `${backendUrl}/recognition/unidentified/${dirCaptureId}/${encodeURIComponent(face.filename)}`;
          console.log(`Generated direct backend URL from directory: ${url}`);
          return url;
        }
      }
    }
    
    // Last resort: try the generic endpoint
    const url = `${backendUrl}/files/unidentified/${encodeURIComponent(face.filename || `unidentified_face_${face.id}.jpg`)}`;
    console.log(`Generated fallback direct backend URL: ${url}`);
    return url;
  };

  // Helper function to group similar faces based on timestamp proximity
  const groupSimilarFaces = (faces: UnidentifiedFace[]): UnidentifiedFace[] => {
    if (!faces || faces.length === 0) return [];
    
    // Sort faces by timestamp or start_time
    const sortedFaces = [...faces].sort((a, b) => {
      const timeA = a.timestamp || a.start_time || 0;
      const timeB = b.timestamp || b.start_time || 0;
      return timeA - timeB;
    });
    
    // Group faces that appear within 1.5 seconds of each other
    const groupedFaces: UnidentifiedFace[] = [];
    let currentGroup: UnidentifiedFace[] = [sortedFaces[0]];
    
    for (let i = 1; i < sortedFaces.length; i++) {
      const prevFace = sortedFaces[i-1];
      const currentFace = sortedFaces[i];
      
      const prevTime = prevFace.timestamp || prevFace.start_time || 0;
      const currentTime = currentFace.timestamp || currentFace.start_time || 0;
      
      // If faces are close in time (within 1.5 seconds), consider them the same person
      if (Math.abs(currentTime - prevTime) < 1.5) {
        currentGroup.push(currentFace);
      } else {
        // Select the best face from the group (the one with the clearest image)
        // For now, we'll just use the first one as we don't have image quality metrics
        groupedFaces.push(currentGroup[0]);
        currentGroup = [currentFace];
      }
    }
    
    // Add the last group
    if (currentGroup.length > 0) {
      groupedFaces.push(currentGroup[0]);
    }
    
    console.log(`Grouped ${faces.length} faces into ${groupedFaces.length} unique faces`);
    return groupedFaces;
  };

  // Extract data from speakerResults when it changes
  useEffect(() => {
    if (speakerResults) {
      // Extract speakers
      setSpeakers(speakerResults.speakers || []);
      
      // Extract unidentified faces and group similar ones
      if (speakerResults.unidentified_faces && speakerResults.unidentified_faces.length > 0) {
        console.log(`Found ${speakerResults.unidentified_faces.length} unidentified faces`);
        // Group similar faces to avoid duplicates
        const groupedFaces = groupSimilarFaces(speakerResults.unidentified_faces);
        setDisplayUnidentifiedFaces(groupedFaces);
      } else {
        console.log('No unidentified faces found');
        setDisplayUnidentifiedFaces([]);
      }
      
      // Extract faces detected count
      setFacesDetected(
        speakerResults.processing_info?.faces_detected || 
        speakerResults.faces_detected
      );
    } else {
      setSpeakers([]);
      setDisplayUnidentifiedFaces([]);
      setFacesDetected(undefined);
    }
  }, [speakerResults]);

  if (isLoading) {
    return (
      <div className="p-4">
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-16 w-16 border-t-2 border-b-2 border-blue-500"></div>
        </div>
        <p className="text-center mt-4">Processing recognition results...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4">
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
          <p className="font-bold">Error</p>
          <p>{error}</p>
        </div>
        <div className="mt-4">
          <Link href={`/parliament-tv/captures/${videoId}`}>
            <button className="bg-blue-500 hover:bg-blue-600 text-white py-2 px-4 rounded">
              Back to Video
            </button>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="p-4">
      <div className="space-y-8">
        {/* Speakers Section */}
        {speakers.length > 0 && (
          <div>
            <h3 className="text-lg font-semibold mb-2">Recognized Speakers</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {speakers.map((speaker, index) => (
                <div key={`${speaker.name}-${index}`} className="p-4 border border-green-200 rounded-md bg-green-50">
                  <div className="flex justify-between items-center mb-2">
                    <div className="font-bold">{speaker.name}</div>
                    <div className="text-sm text-gray-600">
                      {formatTime(speaker.duration || 0)} duration
                    </div>
                  </div>
                  
                  {speaker.image_url && (
                    <div className="my-2">
                      <img
                        src={speaker.image_url}
                        alt={speaker.name}
                        className="w-full h-32 object-cover rounded"
                        onError={(e) => {
                          // @ts-ignore
                          e.target.onerror = null;
                          // @ts-ignore
                          e.target.src = 'data:image/svg+xml;charset=UTF-8,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%22128%22%20height%3D%22128%22%20viewBox%3D%220%200%20128%20128%22%3E%3Crect%20width%3D%22128%22%20height%3D%22128%22%20fill%3D%22%23CCCCCC%22%2F%3E%3Ctext%20x%3D%2250%25%22%20y%3D%2250%25%22%20font-size%3D%2214%22%20text-anchor%3D%22middle%22%20alignment-baseline%3D%22middle%22%20font-family%3D%22Arial%2C%20sans-serif%22%20fill%3D%22%23333333%22%3ENo%20Image%3C%2Ftext%3E%3C%2Fsvg%3E';
                        }}
                      />
                    </div>
                  )}
                  
                  <div className="flex flex-col space-y-2">
                    {speaker.start_time !== undefined && (
                      <button
                        onClick={() => router.push(`/parliament-tv/captures/${videoId}?t=${Math.floor(speaker.start_time || 0)}`)}
                        className="bg-blue-500 hover:bg-blue-600 text-white text-sm py-1 px-3 rounded"
                      >
                        Jump to {formatTime(speaker.start_time || 0)}
                      </button>
                    )}
                    <div className="text-sm">
                      Confidence: {Math.round(speaker.confidence * 100)}%
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Unidentified Faces Section */}
        {displayUnidentifiedFaces.length > 0 && (
          <div>
            <h3 className="text-lg font-semibold mb-2 dark:text-white">Unidentified Faces</h3>
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
              These faces were detected in the video but could not be matched to any known face profiles.
              Add face profiles to identify these individuals in future videos.
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {displayUnidentifiedFaces.map((face, index) => (
                <div key={face.id || `unknown-${index}`} className="p-4 border border-orange-300 rounded-md bg-orange-50 dark:bg-gray-800 dark:border-orange-700 shadow-md">
                  <div className="flex justify-between items-center mb-2">
                    <div className="font-bold text-gray-900 dark:text-gray-100">Unknown Person #{index + 1}</div>
                    <div className="text-sm text-gray-600 dark:text-gray-400">
                      {formatTime(face.duration || 0)} duration
                    </div>
                  </div>
                  
                  {face.filename ? (
                    <div className="my-2 rounded overflow-hidden ring-1 ring-gray-200 dark:ring-gray-700">
                      <img
                        src={getUnidentifiedFaceImageUrl(face)}
                        alt={`Unidentified face ${index + 1}`}
                        className="w-full h-40 object-contain rounded cursor-pointer"
                        onClick={() => {
                          setSelectedImage(getUnidentifiedFaceImageUrl(face));
                          setShowImageModal(true);
                        }}
                        onError={(e) => {
                          console.error(`Error loading image: ${face.filename}`);
                          
                          // Get the original URL that failed
                          const originalUrl = getUnidentifiedFaceImageUrl(face);
                          console.error(`Original URL failed: ${originalUrl}`);
                          
                          // Extract the capture ID from the URL
                          const captureIdMatch = window.location.pathname.match(/\/recognition\/results\/(\d+)/);
                          const captureId = captureIdMatch ? captureIdMatch[1] : '';
                          const paddedCaptureId = captureId.padStart(4, '0');
                          
                          // Try different URL formats as fallbacks
                          const fallbackUrls = [
                            // Try with direct backend URL (no /api/v1 prefix)
                            `http://localhost:8000/recognition/unidentified/${captureId}/${face.filename}`,
                            
                            // Try with padded capture ID
                            `http://localhost:8000/api/v1/recognition/unidentified/${paddedCaptureId}/${face.filename}`,
                            
                            // Try with unpadded capture ID
                            `http://localhost:8000/api/v1/recognition/unidentified/${captureId}/${face.filename}`,
                            
                            // Try the files endpoint
                            `http://localhost:8000/api/v1/files/unidentified/${face.filename}`,
                            
                            // Fallback to a data URI for a placeholder
                            'data:image/svg+xml;charset=UTF-8,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%22128%22%20height%3D%22128%22%20viewBox%3D%220%200%20128%20128%22%3E%3Crect%20width%3D%22128%22%20height%3D%22128%22%20fill%3D%22%23CCCCCC%22%2F%3E%3Ctext%20x%3D%2250%25%22%20y%3D%2250%25%22%20font-size%3D%2214%22%20text-anchor%3D%22middle%22%20alignment-baseline%3D%22middle%22%20font-family%3D%22Arial%2C%20sans-serif%22%20fill%3D%22%23333333%22%3ENo%20Image%3C%2Ftext%3E%3C%2Fsvg%3E'
                          ];
                          
                          let currentFallbackIndex = 0;
                          
                          // Function to try the next fallback URL
                          const tryNextFallback = () => {
                            if (currentFallbackIndex < fallbackUrls.length) {
                              const nextUrl = fallbackUrls[currentFallbackIndex];
                              console.log(`Trying fallback URL (${currentFallbackIndex + 1}/${fallbackUrls.length}): ${nextUrl}`);
                              
                              // @ts-ignore
                              e.target.onerror = () => {
                                currentFallbackIndex++;
                                tryNextFallback();
                              };
                              
                              // @ts-ignore
                              e.target.src = nextUrl;
                              currentFallbackIndex++;
                            } else {
                              // We've tried all fallbacks, use the placeholder
                              console.error('All fallback URLs failed, using placeholder');
                              // @ts-ignore
                              e.target.onerror = null;
                              // @ts-ignore
                              e.target.src = 'data:image/svg+xml;charset=UTF-8,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%22128%22%20height%3D%22128%22%20viewBox%3D%220%200%20128%20128%22%3E%3Crect%20width%3D%22128%22%20height%3D%22128%22%20fill%3D%22%23CCCCCC%22%2F%3E%3Ctext%20x%3D%2250%25%22%20y%3D%2250%25%22%20font-size%3D%2214%22%20text-anchor%3D%22middle%22%20alignment-baseline%3D%22middle%22%20font-family%3D%22Arial%2C%20sans-serif%22%20fill%3D%22%23333333%22%3ENo%20Image%3C%2Ftext%3E%3C%2Fsvg%3E';
                            }
                          };
                          
                          // Start trying fallbacks
                          tryNextFallback();
                        }}
                      />
                    </div>
                  ) : (
                    <div className="my-2 bg-gray-200 dark:bg-gray-700 h-40 flex items-center justify-center rounded">
                      <span className="text-gray-500 dark:text-gray-400">No image available</span>
                    </div>
                  )}
                  
                  <div className="flex flex-col space-y-2">
                    {face.start_time !== undefined && (
                      <button
                        onClick={() => router.push(`/parliament-tv/captures/${videoId}?t=${Math.floor(face.start_time || 0)}`)}
                        className="bg-blue-500 hover:bg-blue-600 dark:bg-blue-600 dark:hover:bg-blue-700 text-white text-sm py-1 px-3 rounded transition-colors"
                      >
                        Jump to {formatTime(face.start_time || 0)}
                      </button>
                    )}
                    <button
                      onClick={() => router.push("/admin/face-profiles/add")}
                      className="bg-green-500 hover:bg-green-600 dark:bg-green-600 dark:hover:bg-green-700 text-white text-sm py-1 px-3 rounded transition-colors"
                    >
                      Add Face Profile
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* No Results Section */}
        {speakers.length === 0 && displayUnidentifiedFaces.length === 0 && (
          <div className="text-center py-6">
            <p className="text-lg">No faces were detected in this video</p>
            <p className="mt-2 text-gray-600">
              This could be because there are no faces in the video, or because the faces were not detected properly.
              You can try running the recognition process again or check the video quality.
            </p>
            <div className="flex space-x-4 mt-6 justify-center">
              <Link href={`/recognition/process/${videoId}`}>
                <button className="bg-blue-500 hover:bg-blue-600 text-white py-2 px-4 rounded">
                  Process Recognition Again
                </button>
              </Link>
              <Link href={`/parliament-tv/captures/${videoId}`}>
                <button className="border border-gray-300 hover:bg-gray-100 py-2 px-4 rounded">
                  View Video
                </button>
              </Link>
            </div>
          </div>
        )}

        {/* Transcription Section */}
        {transcriptionText && (
          <div>
            <h3 className="text-xl font-semibold mb-4 dark:text-white">Transcription</h3>
            <div className="p-4 border border-gray-200 dark:border-gray-700 rounded-md bg-gray-50 dark:bg-gray-800 max-h-96 overflow-y-auto">
              <p className="whitespace-pre-wrap text-gray-900 dark:text-gray-200">{transcriptionText}</p>
            </div>
          </div>
        )}
      </div>
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

export default CustomRecognitionResults;
