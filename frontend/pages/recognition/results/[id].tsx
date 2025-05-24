import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import MainLayout from '../../../components/layout/MainLayout';
import { withAuth, useAuth } from '../../../contexts/AuthContext';
import { UserRole } from '../../../contexts/AuthContext';
import { api } from '../../../utils/api';
import CustomRecognitionResults from '../../../components/recognition/CustomRecognitionResults';
import UnifiedRecognitionTimeline from '../../../components/recognition/UnifiedRecognitionTimeline';
import UnifiedRecognitionResults from '../../../components/recognition/UnifiedRecognitionResults';
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
  const [captureData, setCaptureData] = useState<any>(null);
  const [activeTab, setActiveTab] = useState('unified');
  const [currentTime, setCurrentTime] = useState(0);
  const [videoDuration, setVideoDuration] = useState(0);

  // Function to fetch recognition results
  const fetchRecognitionResults = async (): Promise<void> => {
    if (!id) return;
    
    try {
      setIsLoading(true);
      setError(undefined);
      
      // Step 1: Fetch the capture data
      let captureResponse;
      let captureDataObj: any;
      try {
        captureResponse = await api.get(`/capture/${id}`);
        // Log the raw response to debug
        console.log('Raw capture response:', captureResponse);
        
        // Check if we have a response with data
        console.log('Checking captureResponse:', captureResponse);
        
        // The response might be directly the data object
        if (captureResponse && typeof captureResponse === 'object') {
          // If captureResponse is already the data object
          if (captureResponse.id && captureResponse.status) {
            captureDataObj = captureResponse;
          } 
          // If captureResponse has a data property
          else if (captureResponse.data) {
            captureDataObj = captureResponse.data;
          }
          // If we couldn't find data
          else {
            throw new Error('No capture data found in response');
          }
        } else {
          throw new Error('Invalid capture response format');
        }
        
        // Set the capture data state
        setCaptureData(captureDataObj);
        console.log('Capture data successfully fetched:', captureDataObj);
      } catch (captureErr) {
        console.error('Error fetching capture data:', captureErr);
        setError('Failed to fetch capture data. Please try again.');
        setIsLoading(false);
        return;
      }
      
      // Step 2: Fetch recognition status
      let statusResponse;
      let resultsObj: any;
      try {
        statusResponse = await api.get(`/recognition/detailed-status/${id}`);
        // Log the raw response to debug
        console.log('Raw status response:', statusResponse);
        
        // Check if we have a response with data
        console.log('Checking statusResponse:', statusResponse);
        
        // The response might be directly the data object
        if (statusResponse && typeof statusResponse === 'object') {
          // Log all keys in the response to debug
          console.log('Status response keys:', Object.keys(statusResponse));
          
          // If statusResponse is already the data object with success field (common format)
          if (statusResponse.success) {
            resultsObj = statusResponse;
          }
          // If statusResponse has results, speakers or unidentified_faces
          else if (statusResponse.results || statusResponse.speakers || statusResponse.unidentified_faces) {
            resultsObj = statusResponse;
          } 
          // If statusResponse has a data property
          else if (statusResponse.data) {
            resultsObj = statusResponse.data;
          }
          // If we couldn't find data but have a results property
          else if (statusResponse.results) {
            resultsObj = { results: statusResponse.results };
          }
          // Accept any object as a last resort
          else {
            console.log('Using statusResponse as is, no specific fields found');
            resultsObj = statusResponse;
          }
        } else {
          throw new Error('Invalid recognition status response format');
        }
        
        console.log('Recognition status successfully fetched:', resultsObj);
      } catch (statusErr) {
        console.error('Error fetching recognition status:', statusErr);
        setError('Failed to fetch recognition status. Please try again.');
        setIsLoading(false);
        return;
      }
      
      // Log the extracted data for debugging
      console.log('Using captureDataObj:', captureDataObj);
      console.log('Using resultsObj:', resultsObj);
      
      // Step 3: Check if captureDataObj has recognition_status
      if (!captureDataObj) {
        console.error('Capture data is undefined after fetching');
        setError('Failed to fetch capture data. Please try again.');
        setIsLoading(false);
        return;
      }
      
      if (captureDataObj.recognition_status === undefined) {
        console.error('Capture data is missing recognition_status field');
        console.log('Available fields in captureDataObj:', Object.keys(captureDataObj));
        setError('Failed to fetch complete capture data. Please try again.');
        setIsLoading(false);
        return;
      }
      
      console.log('Checking recognition status:', captureDataObj.recognition_status);
      
      // Check recognition status
      if (captureDataObj.recognition_status !== 'completed') {
        setError(`Recognition is ${captureDataObj.recognition_status}. Please wait for it to complete.`);
        setIsLoading(false);
        return;
      }
      
      // Step 4: Check if we have recognition results
      if (!captureDataObj.recognition_results) {
        setError('No recognition results available for this capture.');
        setIsLoading(false);
        return;
      }
      
      // Additional validation for resultsObj
      if (!resultsObj) {
        console.error('Recognition results are undefined after fetching');
        setError('Failed to fetch recognition results. Please try again.');
        setIsLoading(false);
        return;
      }
      
      // Log the structure of both objects to help debug
      console.log('captureDataObj structure:', Object.keys(captureDataObj));
      console.log('resultsObj structure:', Object.keys(resultsObj));
      
      console.log('Processing recognition results:', resultsObj);
      
      // Step 5: Parse the recognition results
      let recognitionResults;
      
      // Log the recognition_results field to debug
      console.log('Recognition results field type:', typeof captureDataObj.recognition_results);
      if (captureDataObj.recognition_results) {
        console.log('Recognition results field exists');
      } else {
        console.log('Recognition results field is missing or null');
        // Try to use the resultsObj directly if recognition_results is missing
        recognitionResults = resultsObj;
        console.log('Using resultsObj as recognitionResults');
      }
      
      // Try to parse if it's a string
      if (typeof captureDataObj.recognition_results === 'string') {
        try {
          recognitionResults = JSON.parse(captureDataObj.recognition_results);
          console.log('Successfully parsed recognition results from string');
        } catch (e) {
          console.error('Error parsing recognition results:', e);
          // Don't fail immediately, try to use resultsObj
          if (resultsObj) {
            console.log('Using resultsObj as fallback after parsing error');
            recognitionResults = resultsObj;
          } else {
            setError('Error parsing recognition results.');
            setIsLoading(false);
            return;
          }
        }
      } else if (captureDataObj.recognition_results) {
        recognitionResults = captureDataObj.recognition_results;
        console.log('Recognition results already in object format');
      }
      
      // Step 6: Extract data from recognition results
      let speakers = [];
      let unidentifiedFaces = [];
      let unidentifiedDir = '';
      let facesDetected = 0;
      let transcript = '';
      
      // Log recognition results structure for debugging
      console.log('Recognition results structure:', JSON.stringify(recognitionResults || {}).substring(0, 200) + '...');
      
      console.log('Checking for unidentified faces in resultsObj:', resultsObj);
      console.log('ResultsObj keys:', Object.keys(resultsObj || {}));
      
      // Check multiple possible locations for unidentified faces
      if (resultsObj?.unidentified_faces) {
        // Format 1: Unidentified faces directly in the results
        console.log('Found unidentified_faces directly in resultsObj');
        unidentifiedFaces = resultsObj.unidentified_faces;
        unidentifiedDir = resultsObj.unidentified_dir || '';
        console.log(`Found ${unidentifiedFaces.length} unidentified faces directly in results`);
        
        // Process each unidentified face
        unidentifiedFaces = unidentifiedFaces.map((face: any) => {
          // Extract just the basename from the full path
          const filename = face.filename ? face.filename.split('/').pop() : '';
          console.log(`Processing face ${face.id} with filename ${filename}`);
          
          return {
            id: face.id,
            filename: filename,
            start_time: face.appearances?.[0]?.timestamp || 0,
            end_time: face.appearances?.[0]?.timestamp || 0,
            duration: 30, // Default duration
            timestamp: face.appearances?.[0]?.timestamp || 0
          };
        });
      } else if (recognitionResults?.speaker_identification?.results?.unidentified_faces && 
          Array.isArray(recognitionResults.speaker_identification.results.unidentified_faces)) {
        
        const rawUnidentifiedFaces = recognitionResults.speaker_identification.results.unidentified_faces;
        console.log(`Found ${rawUnidentifiedFaces.length} unidentified faces in speaker_identification.results`);
        
        // Process each unidentified face
        unidentifiedFaces = rawUnidentifiedFaces.map((face: any) => {
          // Extract just the basename from the full path
          const filename = face.filename ? face.filename.split('/').pop() : '';
          console.log(`Processing face ${face.id} with filename ${filename}`);
          
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
          console.log(`Setting unidentified directory to ${unidentifiedDir}`);
        }
      } else if (resultsObj?.results?.unidentified_faces && 
          Array.isArray(resultsObj.results.unidentified_faces)) {
        
        const rawUnidentifiedFaces = resultsObj.results.unidentified_faces;
        console.log(`Found ${rawUnidentifiedFaces.length} unidentified faces in resultsObj.results`);
        
        // Process each unidentified face
        unidentifiedFaces = rawUnidentifiedFaces.map((face: any) => {
          // Extract just the basename from the full path
          const filename = face.filename ? face.filename.split('/').pop() : '';
          console.log(`Processing face ${face.id} with filename ${filename}`);
          
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
        if (resultsObj.results.unidentified_dir) {
          unidentifiedDir = resultsObj.results.unidentified_dir;
          console.log(`Setting unidentified directory to ${unidentifiedDir}`);
        }
      } else if (resultsObj?.unidentified) {
        // Another possible format where unidentified is directly in resultsObj
        console.log('Found unidentified field in resultsObj');
        
        // If it's an array, use it directly
        if (Array.isArray(resultsObj.unidentified)) {
          const rawUnidentifiedFaces = resultsObj.unidentified;
          console.log(`Found ${rawUnidentifiedFaces.length} unidentified faces in resultsObj.unidentified`);
          
          // Process each unidentified face
          unidentifiedFaces = rawUnidentifiedFaces.map((face: any) => {
            // Extract just the basename from the full path
            const filename = face.filename ? face.filename.split('/').pop() : '';
            console.log(`Processing face ${face.id || 'unknown'} with filename ${filename}`);
            
            return {
              id: face.id || `unidentified_${Math.random().toString(36).substr(2, 9)}`,
              filename: filename,
              start_time: face.appearances?.[0]?.timestamp || face.timestamp || 0,
              end_time: face.appearances?.[0]?.timestamp || face.timestamp || 0,
              duration: 30, // Default duration
              timestamp: face.appearances?.[0]?.timestamp || face.timestamp || 0
            };
          });
        }

        // Set facesDetected to at least the number of unidentified faces
        facesDetected = Math.max(facesDetected, unidentifiedFaces.length);
        console.log(`Set facesDetected to ${facesDetected}`);
      } else {
        console.log('No unidentified faces found in recognition results structure');
        console.log('Recognition results keys:', Object.keys(recognitionResults || {}));
        if (recognitionResults?.speaker_identification) {
          console.log('Speaker identification keys:', Object.keys(recognitionResults.speaker_identification));
          if (recognitionResults.speaker_identification.results) {
            console.log('Results keys:', Object.keys(recognitionResults.speaker_identification.results));
          }
        }
      }

      // Step 8: Check for faces detected count
      if (resultsObj.processing_info?.faces_detected !== undefined) {
        facesDetected = resultsObj.processing_info.faces_detected;
      } else if (resultsObj.results?.processing_info?.faces_detected !== undefined) {
        facesDetected = resultsObj.results.processing_info.faces_detected;
      } else if (recognitionResults?.processing_info?.faces_detected !== undefined) {
        facesDetected = recognitionResults.processing_info.faces_detected;
      }

      // Step 8: Extract speakers from results
      if (resultsObj) {
        // Handle different formats of recognition results
        if (resultsObj.speakers && Array.isArray(resultsObj.speakers)) {
          // Format 1: Array of speakers with time segments
          speakers = resultsObj.speakers.map((speaker: any) => {
            return {
              name: speaker.name,
              confidence: speaker.confidence || 0.5,
              start_time: speaker.start_time || 0,
              end_time: speaker.end_time || 0,
              duration: speaker.duration || 0
            };
          });
        } else if (resultsObj.results && resultsObj.results.speakers) {
          // Format 2: Nested results object with speakers
          speakers = Object.entries(resultsObj.results.speakers).map(([name, data]: [string, any]) => {
            return {
              name,
              confidence: data.confidence || 0.5,
              start_time: data.start_time || 0,
              end_time: data.end_time || 0,
              duration: data.duration || 0
            };
          });
        } else if (resultsObj.results_summary && resultsObj.results_summary.speakers) {
          // Format 3: Results summary with speakers
          speakers = resultsObj.results_summary.speakers.map((speaker: any) => {
            return {
              name: speaker.name,
              confidence: speaker.confidence || 0.5,
              start_time: speaker.start_time || 0,
              end_time: speaker.end_time || 0,
              duration: speaker.duration || 0
            };
          });
        }
      }

      // Step 9: Extract transcription text if available
      if (resultsObj.transcript) {
        // Format 1: Transcript directly in the resultsObj
        transcript = resultsObj.transcript;
        console.log('Found transcript directly in resultsObj');
      } else if (resultsObj.transcription?.transcript) {
        // Format 2: Transcript in a nested transcription object
        transcript = resultsObj.transcription.transcript;
        console.log('Found transcript in nested transcription object');
      } else if (resultsObj.results?.transcription?.transcript) {
        // Format 3: Transcript in a deeply nested object
        transcript = resultsObj.results.transcription.transcript;
        console.log('Found transcript in deeply nested object');
      } else if (recognitionResults?.transcription?.transcript) {
        // Format 4: Transcript in the recognition results
        transcript = recognitionResults.transcription.transcript;
        console.log('Found transcript in recognition results');
      }

      // Step 10: Create the final speaker results object
      console.log(`Creating final speakerResults with ${unidentifiedFaces.length} unidentified faces`);
      if (unidentifiedFaces.length > 0) {
        console.log(`Found ${unidentifiedFaces.length} unidentified faces`);
        console.log(`First unidentified face: ${JSON.stringify(unidentifiedFaces[0])}`);
        
        // Ensure all unidentified faces have valid filenames
        unidentifiedFaces = unidentifiedFaces.map((face: any, index: number) => {
          if (!face.filename || face.filename === '') {
            console.log(`Face ${face.id} has no filename, generating one`);
            return {
              ...face,
              filename: `unidentified_face_${face.id || index}.jpg`
            };
          }
          return face;
        });
      } else {
        console.log('No unidentified faces found in the results');
        
        // Check if we can extract unidentified faces from other parts of the response
        if (resultsObj?.data?.unidentified_faces || recognitionResults?.data?.unidentified_faces) {
          const dataFaces = (resultsObj?.data?.unidentified_faces || recognitionResults?.data?.unidentified_faces);
          if (Array.isArray(dataFaces) && dataFaces.length > 0) {
            console.log(`Found ${dataFaces.length} unidentified faces in data field`);
            unidentifiedFaces = dataFaces.map((face: any, index: number) => ({
              id: face.id || `unidentified_${index}`,
              filename: face.filename || `unidentified_face_${index}.jpg`,
              start_time: face.start_time || 0,
              end_time: face.end_time || 0,
              duration: face.duration || 30,
              timestamp: face.timestamp || 0
            }));
          }
        }
      }
      
      const finalSpeakerResults = {
        speakers,
        unidentified_faces: unidentifiedFaces,
        unidentified_dir: unidentifiedDir || '/api/v1/files/unidentified', // Default path if not specified
        transcript: transcript,
        processing_info: {
          faces_detected: facesDetected || unidentifiedFaces.length || 0
        }
      };
      
      console.log('Final speaker results:', finalSpeakerResults);
      console.log('Unidentified faces count:', unidentifiedFaces.length);
      
      setSpeakerResults(finalSpeakerResults);
      setTranscriptionText(transcript);
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
      
      // Try to get video duration from the capture data
      if (captureData?.duration) {
        setVideoDuration(captureData.duration);
      } else {
        // Fetch video metadata to get duration
        const fetchVideoDuration = async () => {
          try {
            const response = await api.get(`/capture/${id}/metadata`);
            const data = response.data || response;
            if (data.duration) {
              setVideoDuration(data.duration);
            }
          } catch (err) {
            console.error('Error fetching video metadata:', err);
          }
        };
        
        fetchVideoDuration();
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, retryCount]);
  
  // Function to handle retry
  const handleRetry = (): void => {
    setRetryCount(prev => prev + 1);
    toast.info("Retrying to fetch recognition results...");
  };
  
  // Function to navigate to face profiles page
  const navigateToFaceProfiles = (): void => {
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
            {captureData?.title || `Capture ID: ${id}`}
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
            <div>
              {/* Tabs */}
              <div className="mb-4 border-b border-gray-700">
                <ul className="flex flex-wrap -mb-px">
                  <li className="mr-2">
                    <button
                      className={`inline-block p-4 ${
                        activeTab === 'unified'
                          ? 'text-blue-500 border-b-2 border-blue-500'
                          : 'text-gray-400 hover:text-gray-300'
                      }`}
                      onClick={() => setActiveTab('unified')}
                    >
                      Unified View
                    </button>
                  </li>
                  <li className="mr-2">
                    <button
                      className={`inline-block p-4 ${
                        activeTab === 'faces'
                          ? 'text-blue-500 border-b-2 border-blue-500'
                          : 'text-gray-400 hover:text-gray-300'
                      }`}
                      onClick={() => setActiveTab('faces')}
                    >
                      Faces
                    </button>
                  </li>
                  <li className="mr-2">
                    <button
                      className={`inline-block p-4 ${
                        activeTab === 'timeline'
                          ? 'text-blue-500 border-b-2 border-blue-500'
                          : 'text-gray-400 hover:text-gray-300'
                      }`}
                      onClick={() => setActiveTab('timeline')}
                    >
                      Timeline
                    </button>
                  </li>
                </ul>
              </div>
              
              {/* Tab content */}
              <div className="p-4">
                {activeTab === 'unified' && (
                  <UnifiedRecognitionResults videoId={String(id)} />
                )}
                
                {activeTab === 'faces' && (
                  <CustomRecognitionResults
                    videoId={Number(id)}
                    speakerResults={speakerResults}
                    transcriptionText={transcriptionText}
                    isLoading={isLoading}
                    error={undefined}
                  />
                )}
                
                {activeTab === 'timeline' && (
                  <UnifiedRecognitionTimeline
                    videoId={String(id)}
                    currentTime={currentTime}
                    onSeek={(time) => {
                      setCurrentTime(time);
                      // Navigate to the video player at the specified time
                      router.push(`/parliament-tv/captures/${id}?t=${Math.floor(time)}`);
                    }}
                    videoDuration={videoDuration || 600} // Default to 10 minutes if duration unknown
                  />
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </MainLayout>
  );
};

export default withAuth(RecognitionResultsPage, [UserRole.ADMIN, UserRole.MP, UserRole.STAFF]);
