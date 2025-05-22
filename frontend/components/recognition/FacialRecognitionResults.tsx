/**
 * @deprecated This component is deprecated and will be removed in a future release.
 * Please use UnifiedRecognitionPanel instead.
 */

import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../../contexts/AuthContext';
import { toast } from 'react-toastify';

// API base URL
const API_BASE_URL = 'http://localhost:8000/api/v1';

interface FacialRecognitionResultsProps {
  captureId: number;
  onProcessingComplete?: () => void;
}

interface FaceProfile {
  id: number;
  name: string;
  role?: string;
  party?: string;
  confidence_score?: number;
}

interface FaceSample {
  id: number;
  image_path: string;
  timestamp?: number;
}

interface Speaker {
  id: string;
  name: string;
  face_profile_id: number;
  voice_profile_id?: number;
  face_samples: number;
}

interface FacialRecognitionStatus {
  success: boolean;
  capture_id: number;
  status: 'not_started' | 'scheduled' | 'processing' | 'completed' | 'failed';
  results?: {
    speakers: Speaker[];
    total_faces: number;
    segments_processed: number;
  };
  error?: string;
  started_at?: string;
  completed_at?: string;
}

const FacialRecognitionResults: React.FC<FacialRecognitionResultsProps> = ({ 
  captureId,
  onProcessingComplete
}) => {
  const { token } = useAuth();
  const [status, setStatus] = useState<FacialRecognitionStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [processing, setProcessing] = useState(false);
  const [faceProfiles, setFaceProfiles] = useState<Record<number, FaceProfile>>({});
  const [faceSamples, setFaceSamples] = useState<Record<number, FaceSample[]>>({});
  const [selectedSpeaker, setSelectedSpeaker] = useState<Speaker | null>(null);

  useEffect(() => {
    if (captureId) {
      fetchStatus();
      const interval = setInterval(fetchStatus, 5000); // Poll every 5 seconds
      return () => clearInterval(interval);
    }
  }, [captureId]);

  const fetchStatus = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API_BASE_URL}/facial-recognition/status/${captureId}`, {
        headers: {
          Authorization: `Bearer ${token}`
        }
      });
      
      const data = response.data as FacialRecognitionStatus;
      setStatus(data);
      
      // If processing is complete, fetch face profiles and samples
      if (data.status === 'completed' && data.results) {
        fetchFaceProfiles(data.results.speakers);
        if (onProcessingComplete) {
          onProcessingComplete();
        }
      }
      
      setLoading(false);
    } catch (err) {
      console.error('Error fetching facial recognition status:', err);
      setError('Failed to fetch facial recognition status');
      setLoading(false);
    }
  };

  const fetchFaceProfiles = async (speakers: Speaker[]) => {
    try {
      const profileIds = speakers.map(speaker => speaker.face_profile_id).filter(Boolean);
      
      // Fetch face profiles
      const profilePromises = profileIds.map(id => 
        axios.get(`${API_BASE_URL}/face-profiles/${id}`, {
          headers: {
            Authorization: `Bearer ${token}`
          }
        })
      );
      
      const profileResponses = await Promise.all(profilePromises);
      const profiles: Record<number, FaceProfile> = {};
      
      profileResponses.forEach(response => {
        const profile = response.data as FaceProfile;
        profiles[profile.id] = profile;
      });
      
      setFaceProfiles(profiles);
      
      // Fetch face samples for each profile
      const samplePromises = profileIds.map(id => 
        axios.get(`${API_BASE_URL}/face-profiles/${id}/samples`, {
          headers: {
            Authorization: `Bearer ${token}`
          }
        })
      );
      
      const sampleResponses = await Promise.all(samplePromises);
      const samples: Record<number, FaceSample[]> = {};
      
      sampleResponses.forEach((response, index) => {
        const profileId = profileIds[index];
        samples[profileId] = response.data as FaceSample[];
      });
      
      setFaceSamples(samples);
    } catch (err) {
      console.error('Error fetching face profiles:', err);
    }
  };

  const startProcessing = async () => {
    try {
      setProcessing(true);
      await axios.post(`${API_BASE_URL}/facial-recognition/process-video/${captureId}`, {}, {
        headers: {
          Authorization: `Bearer ${token}`
        }
      });
      
      toast.success('Facial recognition processing started');
      fetchStatus(); // Refresh status immediately
    } catch (err) {
      console.error('Error starting facial recognition processing:', err);
      toast.error('Failed to start facial recognition processing');
    } finally {
      setProcessing(false);
    }
  };

  const renderStatusBadge = (status: string) => {
    let bgColor = 'bg-gray-100';
    let textColor = 'text-gray-800';
    
    switch (status) {
      case 'not_started':
        bgColor = 'bg-gray-100';
        textColor = 'text-gray-800';
        break;
      case 'scheduled':
        bgColor = 'bg-blue-100';
        textColor = 'text-blue-800';
        break;
      case 'processing':
        bgColor = 'bg-yellow-100';
        textColor = 'text-yellow-800';
        break;
      case 'completed':
        bgColor = 'bg-green-100';
        textColor = 'text-green-800';
        break;
      case 'failed':
        bgColor = 'bg-red-100';
        textColor = 'text-red-800';
        break;
    }
    
    return (
      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${bgColor} ${textColor}`}>
        {status.replace('_', ' ')}
      </span>
    );
  };

  const formatTimestamp = (seconds?: number) => {
    if (!seconds) return '-';
    
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.floor(seconds % 60);
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
  };

  if (loading && !status) {
    return (
      <div className="flex justify-center items-center h-40">
        <div className="spinner"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
        {error}
      </div>
    );
  }

  return (
    <div className="bg-white shadow rounded-lg p-6 mb-6">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-semibold">Facial Recognition</h2>
        {status?.status === 'not_started' && (
          <button
            onClick={startProcessing}
            disabled={processing}
            className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline disabled:bg-blue-300"
          >
            {processing ? 'Starting...' : 'Start Processing'}
          </button>
        )}
      </div>
      
      {status && (
        <div className="mb-4">
          <div className="flex items-center mb-2">
            <span className="font-semibold mr-2">Status:</span>
            {renderStatusBadge(status.status)}
          </div>
          
          {status.started_at && (
            <div className="text-sm text-gray-600 mb-1">
              Started: {new Date(status.started_at).toLocaleString()}
            </div>
          )}
          
          {status.completed_at && (
            <div className="text-sm text-gray-600 mb-1">
              Completed: {new Date(status.completed_at).toLocaleString()}
            </div>
          )}
          
          {status.error && (
            <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mt-2">
              {status.error}
            </div>
          )}
        </div>
      )}
      
      {status?.status === 'processing' && (
        <div className="flex items-center my-4">
          <div className="spinner-sm mr-2"></div>
          <span className="text-gray-600">Processing facial recognition...</span>
        </div>
      )}
      
      {status?.status === 'completed' && status.results && (
        <div>
          <div className="mb-4">
            <div className="text-sm text-gray-600 mb-1">
              Total Faces Detected: {status.results.total_faces}
            </div>
            <div className="text-sm text-gray-600 mb-1">
              Segments Processed: {status.results.segments_processed}
            </div>
          </div>
          
          <h3 className="text-lg font-semibold mb-2">Detected Speakers</h3>
          
          {status.results.speakers.length === 0 ? (
            <div className="text-gray-500">No speakers detected</div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {status.results.speakers.map(speaker => (
                <div 
                  key={speaker.id}
                  className={`border rounded-lg overflow-hidden hover:shadow-md cursor-pointer transition-shadow ${selectedSpeaker?.id === speaker.id ? 'ring-2 ring-blue-500' : ''}`}
                  onClick={() => setSelectedSpeaker(speaker)}
                >
                  <div className="p-4">
                    <h4 className="font-semibold">{speaker.name}</h4>
                    <div className="text-sm text-gray-600">
                      Face Profile: {faceProfiles[speaker.face_profile_id]?.name || `ID: ${speaker.face_profile_id}`}
                    </div>
                    {speaker.voice_profile_id && (
                      <div className="text-sm text-gray-600">
                        Voice Profile: ID {speaker.voice_profile_id}
                      </div>
                    )}
                    <div className="text-sm text-gray-600">
                      Face Samples: {speaker.face_samples}
                    </div>
                  </div>
                  
                  {faceSamples[speaker.face_profile_id] && faceSamples[speaker.face_profile_id].length > 0 && (
                    <div className="p-4 bg-gray-50 border-t">
                      <div className="grid grid-cols-3 gap-2">
                        {faceSamples[speaker.face_profile_id].slice(0, 3).map(sample => (
                          <div key={sample.id} className="relative">
                            <img 
                              src={`${API_BASE_URL}/storage/file?path=${encodeURIComponent(sample.image_path)}`}
                              alt={`Face sample ${sample.id}`}
                              className="w-full h-16 object-cover rounded"
                              onError={(e) => {
                                (e.target as HTMLImageElement).src = '/placeholder-face.png';
                              }}
                            />
                            {sample.timestamp && (
                              <div className="absolute bottom-0 right-0 bg-black bg-opacity-50 text-white text-xs px-1 rounded-tl">
                                {formatTimestamp(sample.timestamp)}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
          
          {selectedSpeaker && faceSamples[selectedSpeaker.face_profile_id] && (
            <div className="mt-6">
              <h3 className="text-lg font-semibold mb-2">
                Face Samples for {selectedSpeaker.name}
              </h3>
              <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
                {faceSamples[selectedSpeaker.face_profile_id].map(sample => (
                  <div key={sample.id} className="relative">
                    <img 
                      src={`${API_BASE_URL}/storage/file?path=${encodeURIComponent(sample.image_path)}`}
                      alt={`Face sample ${sample.id}`}
                      className="w-full h-32 object-cover rounded shadow"
                      onError={(e) => {
                        (e.target as HTMLImageElement).src = '/placeholder-face.png';
                      }}
                    />
                    {sample.timestamp && (
                      <div className="absolute bottom-0 right-0 bg-black bg-opacity-50 text-white text-xs px-1 py-0.5 rounded-tl">
                        {formatTimestamp(sample.timestamp)}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
      
      <style jsx>{`
        .spinner {
          border: 4px solid rgba(0, 0, 0, 0.1);
          width: 36px;
          height: 36px;
          border-radius: 50%;
          border-left-color: #09f;
          animation: spin 1s linear infinite;
        }
        .spinner-sm {
          border: 3px solid rgba(0, 0, 0, 0.1);
          width: 20px;
          height: 20px;
          border-radius: 50%;
          border-left-color: #09f;
          animation: spin 1s linear infinite;
        }
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};

export default FacialRecognitionResults;
