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

  // Fetch capture details
  const { data: capture, isLoading: isLoadingCapture } = useQuery({
    queryKey: ['capture', id],
    queryFn: async () => {
      if (!id) return null;
      return await api.get(`/capture/${id}`);
    },
    enabled: !!id,
  });

  // Fetch recognition results
  useEffect(() => {
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
        
        if (captureData.recognition_results) {
          // Parse the results if they're a string
          const results = typeof captureData.recognition_results === 'string' 
            ? JSON.parse(captureData.recognition_results) 
            : captureData.recognition_results;
          
          console.log('Recognition results:', results);
          
          // Extract speaker identification results
          let speakers: Speaker[] = [];
          
          // Try different possible formats for speaker data
          if (results.speaker_identification && results.speaker_identification.results && 
              results.speaker_identification.results.speakers) {
            // Format 1: Structured speaker identification results
            speakers = results.speaker_identification.results.speakers.map((speaker: any) => ({
              name: speaker.name || 'Unknown',
              confidence: speaker.confidence || 0,
              start_time: speaker.start_time || 0,
              end_time: speaker.end_time || 0,
              duration: (speaker.end_time || 0) - (speaker.start_time || 0)
            }));
          } else if (results.speakers) {
            // Format 2: Direct speakers array
            speakers = results.speakers.map((speaker: any) => ({
              name: speaker.name || 'Unknown',
              confidence: speaker.confidence || 0,
              start_time: speaker.start_time || 0,
              end_time: speaker.end_time || 0,
              duration: (speaker.end_time || 0) - (speaker.start_time || 0)
            }));
          }
          
          // Extract transcription text
          let transcript: string | undefined = undefined;
          if (results.transcription && results.transcription.transcript) {
            transcript = results.transcription.transcript;
          } else if (results.results_summary && results.results_summary.transcript_text) {
            transcript = results.results_summary.transcript_text;
          }
          
          setSpeakerResults({ speakers });
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
    
    fetchRecognitionResults();
  }, [id]);

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
          <CustomRecognitionResults
            videoId={Number(id)}
            speakerResults={speakerResults}
            transcriptionText={transcriptionText}
            isLoading={isLoading}
            error={error || undefined}
          />
        </div>
      </div>
    </MainLayout>
  );
};

export default withAuth(RecognitionResultsPage, [UserRole.ADMIN, UserRole.MP, UserRole.STAFF]);
