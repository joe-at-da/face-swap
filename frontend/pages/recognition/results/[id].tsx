import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import MainLayout from '../../../components/layout/MainLayout';
import { withAuth, useAuth } from '../../../contexts/AuthContext';
import { UserRole } from '../../../contexts/AuthContext';
import { api } from '../../../utils/api';
import CustomRecognitionResults from '../../../components/recognition/CustomRecognitionResults';
import { toast } from 'react-toastify';

// Types
interface Speaker {
  name: string;
  confidence: number;
  start_time: number;
  end_time: number;
  duration: number;
}

interface UnidentifiedFace {
  id: string;
  filename: string;
  start_time: number;
  end_time: number;
  duration: number;
  timestamp?: number;
}

interface RecognitionResultsPage extends React.FC {
  // Add any additional props or methods here
}

const RecognitionResultsPage: RecognitionResultsPage = () => {
  const router = useRouter();
  const { id } = router.query;
  const { token } = useAuth();
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | undefined>(undefined);
  const [speakerResults, setSpeakerResults] = useState<any>(null);
  const [transcriptionText, setTranscriptionText] = useState<string | undefined>(undefined);
  const [retryCount, setRetryCount] = useState(0);

  // Fetch capture details
  const { data: capture, isLoading: isLoadingCapture } = useQuery({
    queryKey: ['capture', id],
    queryFn: async () => {
      if (!id) return null;
      return await api.get(`/capture/${id}`);
    },
    enabled: !!id,
  });

  // Function to fetch recognition results
  const fetchRecognitionResults = async () => {
      if (!id) return;
      
      setIsLoading(true);
      setError(undefined);
      
      try {
        // First try to get recognition status
        const statusResponse = await api.get(`/recognition/detailed-status/${id}`);
        console.log('Recognition status:', statusResponse);
        
        if (statusResponse.status !== 'completed') {
          setError('Recognition processing has not been completed yet.');
          setIsLoading(false);
          return;
        }
        
        // Get the capture data to access recognition results
        const captureData = await api.get(`/capture/${id}`);
        console.log('Capture data:', captureData);
        
        // Detailed logging of the capture data structure
        console.log('Capture data keys:', Object.keys(captureData));
        console.log('Recognition status:', captureData.recognition_status);
        console.log('Has recognition_results:', Boolean(captureData.recognition_results));
        
        // Check if recognition results are in the status response
        if (!captureData.recognition_results && statusResponse && statusResponse.progress) {
          try {
            // Extract recognition results from the status response if available
            if (statusResponse.progress && statusResponse.progress.recognition_data) {
              captureData.recognition_results = statusResponse.progress.recognition_data;
              console.log('Using recognition data from status response');
            }
          } catch (e) {
            console.error('Error extracting recognition results from status:', e);
          }
        }
        
        // If we still don't have recognition results, try to fetch them directly
        if (!captureData.recognition_results && captureData.recognition_status === 'completed') {
          console.log('Recognition is completed but no results found in API response, trying direct fetch');
          
          try {
            // Try to fetch the recognition results directly from the detailed status endpoint
            const detailedStatus = await api.get(`/recognition/detailed-status/${id}`);
            console.log('Detailed status response:', detailedStatus);
            
            if (detailedStatus && detailedStatus.status && detailedStatus.status.progress) {
              const progressData = detailedStatus.status.progress;
              console.log('Progress data:', progressData);
              
              // Check if we have recognition_data in the progress
              if (progressData.recognition_data) {
                console.log('Found recognition_data in progress');
                captureData.recognition_results = progressData.recognition_data;
              }
            }
          } catch (e) {
            console.error('Error fetching detailed status:', e);
          }
          
          // If we still don't have results, show an error
          if (!captureData.recognition_results) {
            console.log('Still no recognition results after direct fetch attempt');
            setError('Recognition process completed, but results are not available. Please check that the recognition process ran correctly.');
          }
        }
        
        if (captureData.recognition_results) {
          console.log('Recognition results found:', captureData.recognition_results);
          
          const results = captureData.recognition_results;
          let speakers: Speaker[] = [];
          let unidentifiedFaces: UnidentifiedFace[] = [];
          let unidentifiedDir: string | undefined;
          
          // Handle different formats of recognition results
          if (results.speakers && Array.isArray(results.speakers)) {
            // Format 1: Array of speakers with time segments
            speakers = results.speakers.map((speaker: any) => {
              // Calculate total duration across all time segments
              let totalDuration = 0;
              let earliestStart = Infinity;
              let latestEnd = 0;
              
              if (speaker.time_segments && Array.isArray(speaker.time_segments)) {
                speaker.time_segments.forEach((segment: any) => {
                  const segmentDuration = segment.end - segment.start;
                  totalDuration += segmentDuration;
                  earliestStart = Math.min(earliestStart, segment.start);
                  latestEnd = Math.max(latestEnd, segment.end);
                });
              }
              
              return {
                name: speaker.name,
                confidence: speaker.confidence || 0.5,
                start_time: earliestStart !== Infinity ? earliestStart : 0,
                end_time: latestEnd,
                duration: totalDuration
              };
            });
            
            // Handle unidentified faces if available
            if (results.unidentified_faces && Array.isArray(results.unidentified_faces)) {
              unidentifiedFaces = results.unidentified_faces.map((face: any) => {
                // Calculate total duration across all time segments
                let totalDuration = 0;
                let earliestStart = Infinity;
                let latestEnd = 0;
                
                if (face.time_segments && Array.isArray(face.time_segments)) {
                  face.time_segments.forEach((segment: any) => {
                    const segmentDuration = segment.end - segment.start;
                    totalDuration += segmentDuration;
                    earliestStart = Math.min(earliestStart, segment.start);
                    latestEnd = Math.max(latestEnd, segment.end);
                  });
                }
                
                return {
                  id: face.id,
                  filename: face.filename,
                  start_time: earliestStart !== Infinity ? earliestStart : 0,
                  end_time: latestEnd,
                  duration: totalDuration,
                  timestamp: face.timestamp
                };
              });
            }
            
            // Check for nested unidentified faces in speaker_identification.results
            if (results.speaker_identification?.results?.unidentified_faces && 
                Array.isArray(results.speaker_identification.results.unidentified_faces)) {
              const nestedUnidentifiedFaces = results.speaker_identification.results.unidentified_faces.map((face: any) => {
                // Calculate total duration across all time segments
                let totalDuration = 0;
                let earliestStart = Infinity;
                let latestEnd = 0;
                
                if (face.time_segments && Array.isArray(face.time_segments)) {
                  face.time_segments.forEach((segment: any) => {
                    const segmentDuration = segment.end - segment.start;
                    totalDuration += segmentDuration;
                    earliestStart = Math.min(earliestStart, segment.start);
                    latestEnd = Math.max(latestEnd, segment.end);
                  });
                }
                
                return {
                  id: face.id,
                  filename: face.filename,
                  start_time: earliestStart !== Infinity ? earliestStart : 0,
                  end_time: latestEnd,
                  duration: totalDuration || 30, // Default duration if not available
                  timestamp: face.appearances?.[0]?.timestamp || 0
                };
              });
              
              // Add these to the unidentified faces array
              unidentifiedFaces = [...unidentifiedFaces, ...nestedUnidentifiedFaces];
            }
            
            // Store unidentified directory if available
            if (results.unidentified_dir) {
              unidentifiedDir = results.unidentified_dir;
            }
          } else if (results.results && results.results.speakers) {
            // Format 2: Nested results object with speakers
            speakers = Object.entries(results.results.speakers).map(([name, data]: [string, any]) => {
              return {
                name,
                confidence: data.confidence || 0.5,
                start_time: data.start_time || 0,
                end_time: data.end_time || 0,
                duration: data.duration || 0
              };
            });
          } else if (results.results_summary && results.results_summary.speakers) {
            // Format 3: Results summary with speakers
            speakers = results.results_summary.speakers.map((speaker: any) => {
              return {
                name: speaker.name,
                confidence: speaker.confidence || 0.5,
                start_time: speaker.start_time || 0,
                end_time: speaker.end_time || 0,
                duration: speaker.duration || 0
              };
            });
          }
          
          // IMPORTANT: Extract the faces_detected count directly from the recognition_results string
          // This is a direct approach to fix the issue with nested structures
          const recognitionResultsStr = captureData.recognition_results;
          let facesDetected = 0;
          
          try {
            // Look for "faces_detected": number pattern in the string
            const facesDetectedMatch = recognitionResultsStr.match(/"faces_detected":\s*(\d+)/);
            if (facesDetectedMatch && facesDetectedMatch[1]) {
              facesDetected = parseInt(facesDetectedMatch[1], 10);
              console.log(`Found ${facesDetected} faces detected in the recognition results string`);
            }
          } catch (e) {
            console.error('Error extracting faces_detected from string:', e);
          }
          
          // Fallback to the structured approach if the string approach fails
          if (facesDetected === 0) {
            // Check in the main processing_info
            if (results.processing_info && results.processing_info.faces_detected) {
              facesDetected = results.processing_info.faces_detected;
            }
            // Check in the speaker_identification.results.processing_info
            else if (results.speaker_identification?.results?.processing_info?.faces_detected) {
              facesDetected = results.speaker_identification.results.processing_info.faces_detected;
            }
            // Check in any other nested structure
            else if (results.results?.processing_info?.faces_detected) {
              facesDetected = results.results.processing_info.faces_detected;
            }
          }
          
          console.log(`Found ${facesDetected} detected faces, ${speakers.length} identified speakers, and ${unidentifiedFaces.length} unidentified faces`);
          
          // If there are faces detected but no speakers identified and no unidentified faces,
          // create placeholder unidentified faces
          if (facesDetected > 0 && speakers.length === 0 && unidentifiedFaces.length === 0) {
            console.log(`Creating ${facesDetected} placeholder unidentified faces`);
            
            // Create placeholder unidentified faces
            for (let i = 0; i < facesDetected; i++) {
              unidentifiedFaces.push({
                id: `unknown-${i+1}`,
                filename: '',
                start_time: 0,
                end_time: 30, // Placeholder duration
                duration: 30,
                timestamp: 0
              });
            }
          }
          
          // Only show error if no speakers AND no unidentified faces AND no faces detected
          if (speakers.length === 0 && unidentifiedFaces.length === 0 && facesDetected === 0) {
            setError('No speakers were detected in this video.');
          } else {
            // Sort speakers by start time
            speakers.sort((a, b) => a.start_time - b.start_time);
            
            // Sort unidentified faces by start time
            if (unidentifiedFaces.length > 0) {
              unidentifiedFaces.sort((a, b) => a.start_time - b.start_time);
            }
          }
          
          // Extract transcription text if available
          let transcript: string | undefined = undefined;
          if (results.transcription && results.transcription.transcript) {
            transcript = results.transcription.transcript;
          } else if (results.results_summary && results.results_summary.transcript_text) {
            transcript = results.results_summary.transcript_text;
          }
          
          setSpeakerResults({ 
            speakers, 
            unidentified_faces: unidentifiedFaces,
            unidentified_dir: unidentifiedDir
          });
          setTranscriptionText(transcript);
        } else {
          setError('No recognition results available for this capture.');
        }
      } catch (err) {
        console.error('Error fetching recognition results:', err);
        setError('Failed to fetch recognition results. Please try again.');
      } finally {
        setIsLoading(false);
      }
    };
    
  // Trigger the fetch when id changes or when retry is clicked
  useEffect(() => {
    if (id) {
      fetchRecognitionResults();
    }
  }, [id, retryCount]);
  
  // Function to handle retry
  const handleRetry = () => {
    setRetryCount(prev => prev + 1);
    toast.info("Retrying to fetch recognition results...");
  };
  
  // Function to navigate to face profiles page
  const navigateToFaceProfiles = () => {
    router.push('/admin/face-profiles');
  };

  return (
    <MainLayout>
      <div className="container mx-auto px-4 py-8">
        <div className="mb-6">
          <Link href={`/capture/${id}`} className="text-blue-500 hover:text-blue-700">
            &larr; Back to Capture
          </Link>
          <h1 className="text-2xl font-bold mt-2 text-white">Recognition Results</h1>
          <p className="text-gray-400">
            {capture?.title || `Capture ID: ${id}`}
          </p>
        </div>
        
        <div className="bg-gray-800 rounded-lg shadow-lg overflow-hidden">
          {error ? (
            <div className="p-6 text-center">
              <div className="text-red-500 mb-4">{error}</div>
              
              {error.includes("No speakers were detected") ? (
                <div className="mb-6">
                  <p className="text-white mb-4">
                    The facial recognition system completed successfully, but couldn't match any faces to known profiles.
                    This usually happens when there are no face profiles in the system to match against.
                  </p>
                  <p className="text-white mb-4">
                    <span className="text-yellow-400 font-semibold">Note:</span> The system may have detected unidentified faces. 
                    Click "Try Again" to see if there are any unidentified faces that need profiles added.
                  </p>
                  <div className="flex flex-col md:flex-row justify-center gap-4">
                    <button 
                      onClick={navigateToFaceProfiles}
                      className="bg-green-500 hover:bg-green-700 text-white font-bold py-2 px-4 rounded"
                    >
                      Add Face Profiles
                    </button>
                    <button 
                      onClick={handleRetry}
                      className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded"
                    >
                      Try Again
                    </button>
                  </div>
                </div>
              ) : (
                <button 
                  onClick={handleRetry}
                  className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded"
                >
                  Try Again
                </button>
              )}
            </div>
          ) : (
            <CustomRecognitionResults
              videoId={Number(id)}
              speakerResults={speakerResults}
              transcriptionText={transcriptionText}
              isLoading={isLoading}
              error={undefined}
            />
          )}
        </div>
      </div>
    </MainLayout>
  );
};

export default withAuth(RecognitionResultsPage, [UserRole.ADMIN, UserRole.MP, UserRole.STAFF]);
