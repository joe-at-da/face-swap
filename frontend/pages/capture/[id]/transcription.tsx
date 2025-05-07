import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Link from 'next/link';
import MainLayout from '../../../components/layout/MainLayout';
import { withAuth, useAuth } from '../../../contexts/AuthContext';
import { UserRole } from '../../../contexts/AuthContext';
import { api } from '../../../utils/api';

// Types
interface Transcription {
  id: number;
  capture_id: number;
  status: string;
  language: string;
  format: string;
  model: string;
  output_file: string | null;
  error_message: string | null;
  speaker_identification_id: number | null;
  created_at: string;
  updated_at: string;
}

interface SpeakerIdentification {
  id: number;
  capture_session_id: number;
  status: string;
  results: any;
  output_file: string | null;
  created_at: string;
}

interface CaptureSession {
  id: number;
  title: string;
  status: string;
  file_path: string;
  created_at: string;
}

const TranscriptionPage: React.FC = () => {
  const router = useRouter();
  const { id } = router.query;
  const queryClient = useQueryClient();
  const { token } = useAuth(); // Get token from auth context
  
  const [language, setLanguage] = useState<string>('en');
  const [format, setFormat] = useState<string>('txt');
  const [model, setModel] = useState<string>('medium');
  const [selectedSpeakerId, setSelectedSpeakerId] = useState<number | null>(null);
  const [transcriptionContent, setTranscriptionContent] = useState<string>('');
  const [activeTab, setActiveTab] = useState<string>('start');

  // Fetch capture details
  const { data: capture, isLoading: isLoadingCapture } = useQuery({
    queryKey: ['capture', id],
    queryFn: async () => {
      if (!id) return null;
      return await api.get(`/capture/${id}`);
    },
    enabled: !!id,
  });

  // Fetch speaker identifications for this capture
  const { data: speakerIdentifications, isLoading: isLoadingSpeakers } = useQuery({
    queryKey: ['speaker-identifications', id],
    queryFn: async () => {
      if (!id) return null;
      return await api.get(`/speaker-identification/capture/${id}`);
    },
    enabled: !!id,
  });

  // Fetch transcriptions for this capture
  const { data: transcriptions, isLoading: isLoadingTranscriptions, refetch: refetchTranscriptions } = useQuery({
    queryKey: ['transcriptions', id],
    queryFn: async () => {
      if (!id) return null;
      return await api.get(`/transcription/parliament-tv/capture/${id}`);
    },
    enabled: !!id,
  });

  // Start transcription mutation
  const startTranscriptionMutation = useMutation({
    mutationFn: async (data: any) => {
      return await api.post('/transcription/parliament-tv', data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transcriptions', id] });
      setActiveTab('list');
    },
  });

  // Delete transcription mutation
  const deleteTranscriptionMutation = useMutation({
    mutationFn: async (transcriptionId: number) => {
      return await api.delete(`/transcription/parliament-tv/${transcriptionId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transcriptions', id] });
    },
  });

  // Fetch transcription content
  const fetchTranscriptionContent = async (filePath: string) => {
    try {
      const response = await api.get(`/files?path=${encodeURIComponent(filePath)}`);
      setTranscriptionContent(response.content || 'No content available');
    } catch (error) {
      console.error('Error fetching transcription content:', error);
      setTranscriptionContent('Error loading transcription content.');
    }
  };

  // Handle start transcription
  const handleStartTranscription = () => {
    startTranscriptionMutation.mutate({
      capture_id: id,
      format,
      language,
      model,
      speaker_id: selectedSpeakerId
    });
  };

  // Handle delete transcription
  const handleDeleteTranscription = (transcriptionId: number) => {
    if (confirm('Are you sure you want to delete this transcription?')) {
      deleteTranscriptionMutation.mutate(transcriptionId);
    }
  };

  // Poll for updates if there are processing transcriptions
  useEffect(() => {
    if (transcriptions && Array.isArray(transcriptions) && transcriptions.some((t: Transcription) => t.status === 'processing')) {
      const interval = setInterval(() => {
        refetchTranscriptions();
      }, 5000);
      
      return () => clearInterval(interval);
    }
  }, [transcriptions, refetchTranscriptions]);

  // Loading state
  if (isLoadingCapture || isLoadingSpeakers || isLoadingTranscriptions) {
    return (
      <MainLayout>
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary"></div>
        </div>
      </MainLayout>
    );
  }

  // Error state if capture not found
  if (!capture) {
    return (
      <MainLayout>
        <div className="bg-red-50 border-l-4 border-red-500 p-4 mb-4">
          <Link href={`/capture/${id}`} className="inline-flex items-center text-sm text-gray-500 hover:text-gray-700">
            <svg className="mr-1 h-5 w-5" fill="currentColor" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
              <path fillRule="evenodd" d="M12.707 5.293a1 1 0 010 1.414L9.414 10l3.293 3.293a1 1 0 01-1.414 1.414l-4-4a1 1 0 010-1.414l4-4a1 1 0 011.414 0z" clipRule="evenodd"></path>
            </svg>
            Back to Capture
          </Link>
          <div className="ml-3">
            <p className="text-sm text-red-700">Capture not found or you don't have permission to view it.</p>
          </div>
        </div>
      </MainLayout>
    );
  }

  return (
    <MainLayout title={`Transcription: ${capture.title} | Parliament Video Clip Manager`}>
      <div className="page-container">
        <div className="mb-4 flex justify-between items-center">
          <h1 className="text-3xl font-bold text-gray-900">Transcription: {capture.title}</h1>
          <Link href={`/capture/${id}`}>
            <span className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 cursor-pointer">
              Back to Capture
            </span>
          </Link>
        </div>

        <div className="bg-white shadow-md rounded-lg overflow-hidden">
          <div className="border-b border-gray-200">
            <nav className="flex -mb-px">
              <button
                onClick={() => setActiveTab('start')}
                className={`py-4 px-6 text-center border-b-2 font-medium text-sm ${
                  activeTab === 'start'
                    ? 'border-primary text-primary'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                Start Transcription
              </button>
              <button
                onClick={() => setActiveTab('list')}
                className={`py-4 px-6 text-center border-b-2 font-medium text-sm ${
                  activeTab === 'list'
                    ? 'border-primary text-primary'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                Transcriptions
              </button>
              <button
                onClick={() => setActiveTab('view')}
                className={`py-4 px-6 text-center border-b-2 font-medium text-sm ${
                  activeTab === 'view'
                    ? 'border-primary text-primary'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                View Transcription
              </button>
            </nav>
          </div>

          <div className="p-6">
            {activeTab === 'start' && (
              <div>
                <h2 className="text-lg font-medium text-gray-800 mb-4">Start New Transcription</h2>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Language</label>
                    <select 
                      value={language}
                      onChange={(e) => setLanguage(e.target.value)}
                      className="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-primary focus:border-primary sm:text-sm rounded-md"
                    >
                      <option value="en">English</option>
                      <option value="cy">Welsh</option>
                      <option value="ga">Irish</option>
                      <option value="gd">Scottish Gaelic</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Output Format</label>
                    <select 
                      value={format}
                      onChange={(e) => setFormat(e.target.value)}
                      className="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-primary focus:border-primary sm:text-sm rounded-md"
                    >
                      <option value="txt">Plain Text (TXT)</option>
                      <option value="srt">Subtitles (SRT)</option>
                      <option value="json">JSON</option>
                      <option value="docx">Word Document (DOCX)</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Model Size</label>
                    <select 
                      value={model}
                      onChange={(e) => setModel(e.target.value)}
                      className="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-primary focus:border-primary sm:text-sm rounded-md"
                    >
                      <option value="tiny">Tiny (Fast, less accurate)</option>
                      <option value="base">Base</option>
                      <option value="small">Small</option>
                      <option value="medium">Medium (Recommended)</option>
                      <option value="large">Large (Slow, most accurate)</option>
                    </select>
                    <p className="mt-1 text-sm text-gray-500">
                      Larger models are more accurate but take longer to process.
                    </p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Speaker Identification (Optional)</label>
                    <select 
                      value={selectedSpeakerId || ''}
                      onChange={(e) => setSelectedSpeakerId(e.target.value ? parseInt(e.target.value) : null)}
                      className="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-primary focus:border-primary sm:text-sm rounded-md"
                    >
                      <option value="">None (No speaker attribution)</option>
                      {speakerIdentifications && Array.isArray(speakerIdentifications) && 
                        speakerIdentifications
                          .filter((si: SpeakerIdentification) => si.status === 'completed')
                          .map((si: SpeakerIdentification) => (
                            <option key={si.id} value={si.id}>
                              Speaker ID #{si.id} ({new Date(si.created_at).toLocaleDateString()})
                            </option>
                          ))}
                    </select>
                    <p className="mt-1 text-sm text-gray-500">
                      Selecting a speaker identification will attribute speech to identified speakers.
                    </p>
                  </div>

                  <div className="pt-4">
                    <button 
                      type="button" 
                      onClick={handleStartTranscription}
                      disabled={startTranscriptionMutation.isPending}
                      className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-primary hover:bg-primary-dark focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary disabled:opacity-50"
                    >
                      {startTranscriptionMutation.isPending ? (
                        <>
                          <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                          </svg>
                          Starting...
                        </>
                      ) : (
                        'Start Transcription'
                      )}
                    </button>
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'list' && (
              <div>
                <h2 className="text-lg font-medium text-gray-800 mb-4">Transcription History</h2>
                {transcriptions && Array.isArray(transcriptions) && transcriptions.length > 0 ? (
                  <div className="space-y-4">
                    {transcriptions.map((transcription: Transcription) => (
                      <div key={transcription.id} className="border rounded-lg p-4 hover:bg-gray-50">
                        <div className="flex justify-between items-center mb-2">
                          <h3 className="font-medium">
                            Transcription #{transcription.id}
                            <span 
                              className={`ml-2 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                                transcription.status === 'completed' ? 'bg-green-100 text-green-800' : 
                                transcription.status === 'processing' ? 'bg-yellow-100 text-yellow-800' : 
                                transcription.status === 'failed' ? 'bg-red-100 text-red-800' : 'bg-gray-100 text-gray-800'
                              }`}
                            >
                              {transcription.status}
                            </span>
                          </h3>
                          <span className="text-sm text-gray-500">{new Date(transcription.created_at).toLocaleString()}</span>
                        </div>
                        <div className="text-sm text-gray-600 mb-3">
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 mr-2">
                            {transcription.format.toUpperCase()}
                          </span>
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 mr-2">
                            {transcription.language}
                          </span>
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                            {transcription.model}
                          </span>
                        </div>
                        
                        {transcription.status === 'processing' && (
                          <div className="flex items-center text-yellow-700 text-sm mt-2">
                            <div className="animate-spin rounded-full h-4 w-4 border-t-2 border-b-2 border-yellow-700 mr-2"></div>
                            Processing transcription...
                          </div>
                        )}
                        
                        {transcription.status === 'failed' && (
                          <div className="bg-red-50 border-l-4 border-red-500 p-3 mt-2">
                            <div className="text-sm text-red-700">
                              <strong>Error:</strong> {transcription.error_message || 'Unknown error occurred'}
                            </div>
                          </div>
                        )}
                        
                        {transcription.status === 'completed' && transcription.output_file && (
                          <div className="mt-2 flex space-x-2">
                            <button 
                              type="button" 
                              onClick={() => {
                                fetchTranscriptionContent(transcription.output_file!);
                                setActiveTab('view');
                              }}
                              className="inline-flex items-center px-3 py-1.5 border border-gray-300 text-xs font-medium rounded text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary"
                            >
                              View Transcription
                            </button>
                            <a 
                              href={`/api/v1/files/download?path=${encodeURIComponent(transcription.output_file)}`}
                              className="inline-flex items-center px-3 py-1.5 border border-green-300 text-xs font-medium rounded text-green-700 bg-white hover:bg-green-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500"
                              target="_blank"
                              rel="noopener noreferrer"
                            >
                              Download
                            </a>
                            <button 
                              type="button" 
                              onClick={() => handleDeleteTranscription(transcription.id)}
                              className="inline-flex items-center px-3 py-1.5 border border-red-300 text-xs font-medium rounded text-red-700 bg-white hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
                            >
                              Delete
                            </button>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="bg-blue-50 border-l-4 border-blue-500 p-4">
                    <div className="flex">
                      <div className="ml-3">
                        <p className="text-sm text-blue-700">
                          No transcriptions found for this capture. Start a new transcription to see results here.
                        </p>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {activeTab === 'view' && (
              <div>
                <h2 className="text-lg font-medium text-gray-800 mb-4">Transcription Content</h2>
                {transcriptionContent ? (
                  <div className="space-y-4">
                    {/* Transcription controls */}
                    <div className="flex flex-wrap gap-2 mb-4">
                      <button 
                        className="px-3 py-1.5 bg-gray-100 hover:bg-gray-200 rounded-md text-sm font-medium"
                        onClick={() => {
                          try {
                            // Try to parse the content as JSON
                            const jsonContent = JSON.parse(transcriptionContent);
                            // Format it for better readability
                            setTranscriptionContent(JSON.stringify(jsonContent, null, 2));
                          } catch (e) {
                            // If it's not valid JSON, do nothing
                            console.error('Not valid JSON or already formatted');
                          }
                        }}
                      >
                        Format JSON
                      </button>
                      <button 
                        className="px-3 py-1.5 bg-gray-100 hover:bg-gray-200 rounded-md text-sm font-medium"
                        onClick={() => {
                          try {
                            // Try to copy to clipboard
                            navigator.clipboard.writeText(transcriptionContent);
                            alert('Copied to clipboard!');
                          } catch (e) {
                            console.error('Failed to copy', e);
                          }
                        }}
                      >
                        Copy to Clipboard
                      </button>
                    </div>
                    
                    {/* Try to parse and display as segments if it's JSON */}
                    {(() => {
                      try {
                        const jsonContent = JSON.parse(transcriptionContent);
                        if (jsonContent.segments && Array.isArray(jsonContent.segments)) {
                          return (
                            <div>
                              {/* Full text preview */}
                              <div className="mb-6">
                                <h3 className="text-md font-medium mb-2">Full Transcript</h3>
                                <div className="bg-white border border-gray-200 rounded-md p-4 max-h-[200px] overflow-y-auto">
                                  <p className="text-gray-700">{jsonContent.text}</p>
                                </div>
                              </div>
                              
                              {/* Segments with timestamps */}
                              <h3 className="text-md font-medium mb-2">Segments ({jsonContent.segments.length})</h3>
                              <div className="bg-white border border-gray-200 rounded-md overflow-hidden">
                                <table className="min-w-full divide-y divide-gray-200">
                                  <thead className="bg-gray-50">
                                    <tr>
                                      <th scope="col" className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Time</th>
                                      {jsonContent.segments.some((s: any) => s.speaker) && (
                                        <th scope="col" className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Speaker</th>
                                      )}
                                      <th scope="col" className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Text</th>
                                    </tr>
                                  </thead>
                                  <tbody className="bg-white divide-y divide-gray-200">
                                    {jsonContent.segments.map((segment: any, index: number) => {
                                      // Format time
                                      const formatTime = (seconds: number) => {
                                        const mins = Math.floor(seconds / 60);
                                        const secs = Math.floor(seconds % 60);
                                        return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
                                      };
                                      
                                      return (
                                        <tr key={index} className={index % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                                          <td className="px-3 py-2 whitespace-nowrap text-xs text-gray-500">
                                            {formatTime(segment.start)} - {formatTime(segment.end)}
                                          </td>
                                          {jsonContent.segments.some((s: any) => s.speaker) && (
                                            <td className="px-3 py-2 whitespace-nowrap">
                                              {segment.speaker ? (
                                                <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-blue-100 text-blue-800">
                                                  {segment.speaker}
                                                </span>
                                              ) : (
                                                <span className="text-gray-400 text-xs">Unknown</span>
                                              )}
                                            </td>
                                          )}
                                          <td className="px-3 py-2 text-sm text-gray-900">{segment.text}</td>
                                        </tr>
                                      );
                                    })}
                                  </tbody>
                                </table>
                              </div>
                              
                              {/* Metadata */}
                              <div className="mt-6">
                                <h3 className="text-md font-medium mb-2">Metadata</h3>
                                <div className="bg-gray-50 rounded-md p-4 text-sm">
                                  <div className="grid grid-cols-2 gap-2">
                                    <div>
                                      <span className="font-medium">Language:</span> {jsonContent.language || 'Unknown'}
                                    </div>
                                    <div>
                                      <span className="font-medium">Duration:</span> {(() => {
                                        const duration = jsonContent.duration || 0;
                                        const mins = Math.floor(duration / 60);
                                        const secs = Math.floor(duration % 60);
                                        return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
                                      })()}
                                    </div>
                                    <div>
                                      <span className="font-medium">Model:</span> {jsonContent.model || 'Unknown'}
                                    </div>
                                    <div>
                                      <span className="font-medium">Speaker Detection:</span> {jsonContent.has_speaker_data ? 'Yes' : 'No'}
                                    </div>
                                  </div>
                                </div>
                              </div>
                            </div>
                          );
                        }
                      } catch (e) {
                        // Not valid JSON or doesn't have segments array
                        console.log('Not a valid transcription JSON');
                      }
                      
                      // Fallback to displaying as raw text
                      return (
                        <pre className="bg-gray-50 p-4 rounded-md overflow-auto max-h-[600px] text-sm font-mono whitespace-pre-wrap">
                          {transcriptionContent}
                        </pre>
                      );
                    })()}
                  </div>
                ) : (
                  <div className="bg-blue-50 border-l-4 border-blue-500 p-4">
                    <div className="flex">
                      <div className="ml-3">
                        <p className="text-sm text-blue-700">
                          Select a transcription from the Transcriptions tab to view its content.
                        </p>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </MainLayout>
  );
};

export default withAuth(TranscriptionPage, [UserRole.ADMIN, UserRole.MP, UserRole.STAFF]);