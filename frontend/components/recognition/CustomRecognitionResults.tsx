import React, { useEffect } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';

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

const formatTime = (seconds: number): string => {
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = Math.floor(seconds % 60);
  return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
};

const CustomRecognitionResults: React.FC<RecognitionResultsProps> = ({ 
  videoId, 
  speakerResults, 
  transcriptionText, 
  isLoading = false,
  error
}) => {
  // Log unidentified faces for debugging and ensure they're properly displayed
  useEffect(() => {
    if (speakerResults?.unidentified_faces) {
      console.log(`CustomRecognitionResults: Found ${speakerResults.unidentified_faces.length} unidentified faces`);
      speakerResults.unidentified_faces.forEach(face => {
        console.log(`Unidentified face: ${face.id}, filename: ${face.filename}`);
      });
      if (speakerResults.unidentified_dir) {
        console.log(`Unidentified directory: ${speakerResults.unidentified_dir}`);
      }
    } else {
      console.log('CustomRecognitionResults: No unidentified faces found in speakerResults');
      console.log('speakerResults:', speakerResults);
    }
  }, [speakerResults]);
  
  // Function to generate image URLs for unidentified faces
  const getUnidentifiedFaceImageUrl = (face: UnidentifiedFace): string => {
    // If we have a directory and filename, use that
    if (speakerResults?.unidentified_dir && face.filename) {
      return `${speakerResults.unidentified_dir}/${encodeURIComponent(face.filename)}`;
    }
    
    // Otherwise try standard API endpoints
    return `/api/v1/files/unidentified/${encodeURIComponent(face.filename || `unidentified_face_${face.id}.jpg`)}`;
  };
  // Extract speakers and unidentified faces from speakerResults
  const speakers = speakerResults?.speakers || [];
  const unidentifiedFaces = speakerResults?.unidentified_faces || [];
  // Log more detailed information about unidentified faces for debugging
  if (unidentifiedFaces.length > 0) {
    console.log(`Processing ${unidentifiedFaces.length} unidentified faces for display`);
    unidentifiedFaces.forEach((face, index) => {
      console.log(`Face ${index+1}:`, face);
    });
  }
  const facesDetected = speakerResults?.processing_info?.faces_detected || unidentifiedFaces.length || 0;
  const router = useRouter();

  if (isLoading) {
    return (
      <div className="p-4 border border-gray-300 rounded-lg overflow-hidden bg-white shadow-md">
        <div className="flex flex-col items-center space-y-4">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-500"></div>
          <p>Processing recognition results...</p>
        </div>
      </div>
    );
  }

  if (error) {
    // Check if the error is about no speakers detected
    const isNoSpeakersError = error.includes('No speakers were detected');
    
    return (
      <div className="p-4 border border-gray-300 rounded-lg overflow-hidden bg-gray-800 shadow-md text-white">
        <div className="flex flex-col space-y-4">
          <h3 className="text-lg font-semibold text-red-400">
            {isNoSpeakersError ? 'No Recognizable Faces Found' : 'Error Processing Recognition'}
          </h3>
          
          {isNoSpeakersError ? (
            <>
              <p>The facial recognition system completed successfully, but couldn't match any faces to known profiles.</p>
              <div className="bg-gray-700 p-4 rounded-md border-l-4 border-yellow-500">
                <h4 className="font-semibold text-yellow-400 mb-2">Why this happens:</h4>
                <ul className="list-disc pl-5 space-y-2">
                  <li>There are no face profiles in the system to match against</li>
                  <li>The faces in the video don't match any existing profiles</li>
                  <li>The video quality might be too low for accurate recognition</li>
                </ul>
              </div>
              <p className="mt-3">
                <span className="text-yellow-400 font-semibold">Note:</span> The system may have detected unidentified faces. 
                Check the results section to see if there are any unidentified faces that need profiles added.
              </p>
              <div className="flex flex-col sm:flex-row space-y-3 sm:space-y-0 sm:space-x-3 mt-2">
                <button 
                  className="bg-green-600 hover:bg-green-700 text-white py-2 px-4 rounded"
                  onClick={() => router.push('/admin/face-profiles')}
                >
                  Add Face Profiles
                </button>
                <button 
                  className="bg-blue-600 hover:bg-blue-700 text-white py-2 px-4 rounded"
                  onClick={() => router.reload()}
                >
                  Try Again
                </button>
              </div>
            </>
          ) : (
            <>
              <p>{error}</p>
              <button 
                className="bg-blue-600 hover:bg-blue-700 text-white py-2 px-4 rounded"
                onClick={() => router.reload()}
              >
                Try Again
              </button>
            </>
          )}
        </div>
      </div>
    );
  }

  // If there are faces detected but no speakers identified and no unidentified faces,
  // create placeholder unidentified faces
  let displayUnidentifiedFaces = [...unidentifiedFaces];
  if (facesDetected > 0 && speakers.length === 0 && unidentifiedFaces.length === 0) {
    console.log(`Creating ${facesDetected} placeholder unidentified faces`);
    
    // Create placeholder unidentified faces
    for (let i = 0; i < facesDetected; i++) {
      displayUnidentifiedFaces.push({
        id: `unknown-${i+1}`,
        filename: 'placeholder_face.jpg', // Use a placeholder filename instead of empty string
        start_time: 0,
        end_time: 30, // Placeholder duration
        duration: 30
      });
    }
  }

  return (
    <div className="p-4 border border-gray-300 rounded-lg overflow-hidden bg-white shadow-md">
      <div className="flex flex-col space-y-6">
        {/* Identified Speakers Section */}
        {speakers.length > 0 && (
          <div>
            <h3 className="text-lg font-semibold mb-4">Identified Speakers</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {speakers.map((speaker, index) => (
                <div key={index} className="p-4 border border-gray-200 rounded-md bg-gray-50">
                  <div className="flex justify-between items-center mb-2">
                    <div className="font-bold">{speaker.name}</div>
                    <div className="text-sm text-gray-600">
                      {formatTime(speaker.duration)} duration
                    </div>
                  </div>
                  {speaker.image_url && (
                    <div className="my-2">
                      <img 
                        src={speaker.image_url} 
                        alt={speaker.name} 
                        className="w-full h-32 object-cover rounded"
                      />
                    </div>
                  )}
                  <button
                    onClick={() => router.push(`/parliament-tv/captures/${videoId}?t=${Math.floor(speaker.start_time)}`)}
                    className="mt-2 bg-blue-500 hover:bg-blue-600 text-white text-sm py-1 px-3 rounded w-full"
                  >
                    Jump to {formatTime(speaker.start_time)}
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Unidentified Faces Section */}
        {displayUnidentifiedFaces.length > 0 && (
          <div>
            <h3 className="text-lg font-semibold mb-2">Unidentified Faces</h3>
            <p className="text-sm text-gray-600 mb-4">
              These faces were detected in the video but could not be matched to any known face profiles.
              Add face profiles to identify these individuals in future videos.
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {displayUnidentifiedFaces.map((face, index) => (
                <div key={face.id || `unknown-${index}`} className="p-4 border border-orange-200 rounded-md bg-orange-50">
                  <div className="flex justify-between items-center mb-2">
                    <div className="font-bold">Unknown Person #{index + 1}</div>
                    <div className="text-sm text-gray-600">
                      {formatTime(face.duration || 0)} duration
                    </div>
                  </div>
                  {face.filename ? (
                    <div className="my-2">
                      {/* No console.log in JSX to avoid lint errors */}
                      <img 
                        src={getUnidentifiedFaceImageUrl(face)} 
                        alt={`Unidentified face ${face.id}`} 
                        className="w-full h-32 object-cover rounded"
                        onError={(e) => {
                          console.log(`Error loading image: ${face.filename}`);
                          console.log(`Original URL: ${getUnidentifiedFaceImageUrl(face)}`);
                          
                          // Try different URL formats as fallbacks
                          const fallbackUrls = [
                            `/api/v1/files/unidentified/unidentified_face_${face.id}.jpg`,
                            `/api/v1/recognition/unidentified/${encodeURIComponent(face.filename || '')}`,
                            `/api/v1/recognition/unidentified/unidentified_face_${face.id}.jpg`,
                            `/api/v1/files/unidentified/${face.id}.jpg`,
                            `/api/v1/recognition/unidentified/${face.id}.jpg`,
                            `/api/v1/files/faces/${face.id}.jpg`
                          ];
                          
                          let currentFallbackIndex = 0;
                          
                          const tryNextFallback = () => {
                            if (currentFallbackIndex < fallbackUrls.length) {
                              const nextUrl = fallbackUrls[currentFallbackIndex];
                              console.log(`Trying fallback URL (${currentFallbackIndex + 1}/${fallbackUrls.length}): ${nextUrl}`);
                              currentFallbackIndex++;
                              // @ts-ignore - target is valid
                              e.target.onerror = tryNextFallback;
                              // @ts-ignore - target is valid
                              e.target.src = nextUrl;
                            } else {
                              console.log(`All fallbacks failed, using placeholder`);
                              // @ts-ignore - target is valid
                              e.target.onerror = null;
                              // @ts-ignore - target is valid
                              e.target.src = '/placeholder-face.png';
                            }
                          };
                          
                          tryNextFallback();
                        }}
                      />
                    </div>
                  ) : (
                    <div className="my-2 bg-gray-200 h-32 flex items-center justify-center rounded">
                      <span className="text-gray-500">No image available</span>
                    </div>
                  )}
                  <div className="flex flex-col space-y-2">
                    {face.start_time !== undefined && (
                      <button
                        onClick={() => router.push(`/parliament-tv/captures/${videoId}?t=${Math.floor(face.start_time || 0)}`)}
                        className="bg-blue-500 hover:bg-blue-600 text-white text-sm py-1 px-3 rounded"
                      >
                        Jump to {formatTime(face.start_time || 0)}
                      </button>
                    )}
                    <button
                      onClick={() => router.push("/admin/face-profiles/add")}
                      className="bg-green-500 hover:bg-green-600 text-white text-sm py-1 px-3 rounded"
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
            <h3 className="text-lg font-semibold mb-4">Transcription</h3>
            <div className="p-4 border border-gray-200 rounded-md bg-gray-50 max-h-96 overflow-y-auto">
              <p className="whitespace-pre-wrap">{transcriptionText}</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default CustomRecognitionResults;
