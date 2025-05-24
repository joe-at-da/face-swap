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

const RecognitionResultsPage = () => {
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
      const response = await api.get(`/capture/${id}`);
      return response?.data;
    },
    enabled: !!id,
  });

  // Function to fetch recognition results
  const fetchRecognitionResults = async () => {
    if (!id) return;
    
    try {
      setIsLoading(true);
      setError(undefined);
      
      // Fetch the detailed recognition status for this video
      const response = await api.get(`/recognition/detailed-status/${id}`);
      const results = response.data;
      
      // Fetch the capture data to get additional metadata
      const captureResponse = await api.get(`/capture/${id}`);
      const captureData = captureResponse?.data;
      console.log('Capture data:', captureData);
      if (captureData) {
        console.log('Capture data keys:', Object.keys(captureData));
        console.log('Recognition status:', captureData.recognition_status);
        console.log('Has recognition_results:', !!captureData.recognition_results);
      } else {
        console.error('No capture data returned from API');
        setError('Failed to fetch capture data. Please try again.');
        setIsLoading(false);
        return;
      }
      
      // If the recognition is not completed, show an appropriate message
      if (captureData.recognition_status !== 'completed') {
        setError(`Recognition is ${captureData.recognition_status}. Please wait for it to complete.`);
        setIsLoading(false);
        return;
      }
      
      // Check if we have recognition results
      if (!captureData.recognition_results) {
        setError('No recognition results available for this capture.');
        setIsLoading(false);
        return;
      }
      
      // Parse the recognition results
      let recognitionResults;
      if (typeof captureData.recognition_results === 'string') {
        try {
          recognitionResults = JSON.parse(captureData.recognition_results);
        } catch (e) {
          console.error('Error parsing recognition results:', e);
          setError('Error parsing recognition results.');
          setIsLoading(false);
          return;
        }
      } else {
        recognitionResults = captureData.recognition_results;
      }
      
      console.log('Recognition results found:', JSON.stringify(recognitionResults));
      
      // Extract speakers and unidentified faces from the results
      let speakers: Speaker[] = [];
      let unidentifiedFaces: UnidentifiedFace[] = [];
      let unidentifiedDir: string | undefined = undefined;
      let facesDetected = 0;
      let transcript = '';
      
      // CRITICAL: Direct access to unidentified faces from the raw data
      // This is a more reliable way to access the unidentified faces
      if (recognitionResults?.speaker_identification?.results?.unidentified_faces && 
          Array.isArray(recognitionResults.speaker_identification.results.unidentified_faces)) {
        const rawUnidentifiedFaces = recognitionResults.speaker_identification.results.unidentified_faces;
        console.log(`Direct access: Found ${rawUnidentifiedFaces.length} unidentified faces in raw data`);
        
        // Process each unidentified face
        unidentifiedFaces = rawUnidentifiedFaces.map((face: any) => {
          // Extract just the basename from the full path
          const filename = face.filename ? face.filename.split('/').pop() : '';
          console.log(`Direct access: Processing face ${face.id} with filename ${filename}`);
          
          return {
            id: face.id,
            filename: filename,
            start_time: face.appearances?.[0]?.timestamp || 0,
            end_time: face.appearances?.[0]?.timestamp || 0,
            duration: 30, // Default duration
            timestamp: face.appearances?.[0]?.timestamp || 0
          };
        });
        
        // Set the unidentified directory if available
        if (recognitionResults.speaker_identification.unidentified_dir) {
          unidentifiedDir = recognitionResults.speaker_identification.unidentified_dir;
          console.log(`Direct access: Setting unidentified directory to ${unidentifiedDir}`);
        }
        
        // Set facesDetected to at least the number of unidentified faces
        facesDetected = Math.max(facesDetected, unidentifiedFaces.length);
        console.log(`Direct access: Set facesDetected to ${facesDetected}`);
      }
      
      if (results) {
        // Handle different formats of recognition results
        if (results.speakers && Array.isArray(results.speakers)) {
          // Format 1: Array of speakers with time segments
          speakers = results.speakers.map((speaker: any) => {
            return {
              name: speaker.name,
              confidence: speaker.confidence || 0.5,
              start_time: speaker.start_time || 0,
              end_time: speaker.end_time || 0,
              duration: speaker.duration || 0
            };
          });
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
        
        // Extract transcription text if available
        if (results.transcription && results.transcription.transcript) {
          transcript = results.transcription.transcript;
        } else if (results.results_summary && results.results_summary.transcript_text) {
          transcript = results.results_summary.transcript_text;
        }
        
        // Log the unidentified faces before creating the final object
        console.log(`Creating final speakerResults with ${unidentifiedFaces.length} unidentified faces`);
        if (unidentifiedFaces.length > 0) {
          console.log(`First unidentified face: ${JSON.stringify(unidentifiedFaces[0])}`);
        }
        
        const finalSpeakerResults = {
          speakers,
          unidentified_faces: unidentifiedFaces,
          unidentified_dir: unidentifiedDir,
          transcript: transcript
        };
        
        setSpeakerResults(finalSpeakerResults);
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
