import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import { api } from '../../utils/api';
import { toast } from 'react-toastify';

interface Speaker {
  id: string;
  name: string;
  confidence: number;
  segments: number;
  duration: number;
  profileId?: string;
  faceMatches?: FaceMatch[];
}

interface FaceMatch {
  faceId: string;
  confidence: number;
  thumbnailUrl: string;
  profileId?: string;
  profileName?: string;
}

interface UnidentifiedSpeakersPanelProps {
  captureId: number;
  onSpeakerSelect?: (speakerId: string) => void;
  onSpeakerIdentified?: (speakerId: string, profileId: string) => void;
}

const UnidentifiedSpeakersPanel: React.FC<UnidentifiedSpeakersPanelProps> = ({
  captureId,
  onSpeakerSelect,
  onSpeakerIdentified
}) => {
  const router = useRouter();
  const [speakers, setSpeakers] = useState<Speaker[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string>('');
  const [voiceProfiles, setVoiceProfiles] = useState<any[]>([]);
  const [selectedSpeakerId, setSelectedSpeakerId] = useState<string | null>(null);
  const [isAssigning, setIsAssigning] = useState<boolean>(false);
  const [showCreateForm, setShowCreateForm] = useState<boolean>(false);
  const [newProfileData, setNewProfileData] = useState({
    name: '',
    role: '',
    party: ''
  });

  useEffect(() => {
    if (captureId) {
      fetchSpeakers();
      fetchVoiceProfiles();
    }
  }, [captureId]);

  const fetchSpeakers = async () => {
    try {
      setLoading(true);
      let speakersData = null;
      
      // First try the speakers endpoint
      try {
        const response = await api.get(`/recognition/speakers/${captureId}`);
        if (response && response.success) {
          const data = response.data || response;
          if (data.speakers && data.speakers.length > 0) {
            speakersData = data.speakers;
          }
        }
      } catch (speakersErr) {
        console.log('Speakers endpoint not available, trying detailed status');
      }
      
      // If speakers endpoint failed, try detailed status
      if (!speakersData) {
        try {
          const statusResponse = await api.get(`/recognition/detailed-status/${captureId}`);
          const statusData = statusResponse.data || statusResponse;
          
          if (statusData && statusData.status && statusData.status.recognition_results) {
            let resultsData;
            
            // Parse recognition results if needed
            if (typeof statusData.status.recognition_results === 'string') {
              try {
                resultsData = JSON.parse(statusData.status.recognition_results);
              } catch (parseErr) {
                console.error('Error parsing recognition results:', parseErr);
              }
            } else {
              resultsData = statusData.status.recognition_results;
            }
            
            // Extract speakers from results
            if (resultsData && resultsData.speakers) {
              speakersData = resultsData.speakers;
            }
          }
        } catch (statusErr) {
          console.error('Error fetching detailed status:', statusErr);
        }
      }
      
      // If still no speakers data, try capture endpoint
      if (!speakersData) {
        try {
          const captureResponse = await api.get(`/capture/${captureId}`);
          const captureData = captureResponse.data || captureResponse;
          
          if (captureData && captureData.recognition_results) {
            let resultsData;
            
            if (typeof captureData.recognition_results === 'string') {
              try {
                resultsData = JSON.parse(captureData.recognition_results);
                if (resultsData && resultsData.speakers) {
                  speakersData = resultsData.speakers;
                }
              } catch (parseErr) {
                console.error('Error parsing recognition results from capture:', parseErr);
              }
            } else if (captureData.recognition_results.speakers) {
              speakersData = captureData.recognition_results.speakers;
            }
          }
        } catch (captureErr) {
          console.error('Error fetching capture data:', captureErr);
        }
      }
      
      // Process speakers data if we have it
      if (speakersData && speakersData.length > 0) {
        // Filter for unidentified speakers (those without a profileId)
        const unidentifiedSpeakers = speakersData
          .filter((speaker: any) => !speaker.profile_id && !speaker.profileId)
          .map((speaker: any) => ({
            id: speaker.id,
            name: speaker.name || `Speaker ${speaker.id.slice(0, 4)}`,
            confidence: speaker.confidence || 1.0,
            segments: speaker.segments || 0,
            duration: speaker.duration || 0,
            profileId: speaker.profile_id || speaker.profileId,
            faceMatches: (speaker.face_matches || speaker.faceMatches || []).map((match: any) => ({
              faceId: match.face_id || match.faceId,
              confidence: match.confidence || 0,
              thumbnailUrl: match.thumbnail_url || match.thumbnailUrl || '',
              profileId: match.profile_id || match.profileId,
              profileName: match.profile_name || match.profileName
            }))
          }));
        
        setSpeakers(unidentifiedSpeakers);
      } else {
        // If no speakers found, set empty array
        setSpeakers([]);
        setError('No speaker data available');
      }
    } catch (err) {
      console.error('Error fetching speakers:', err);
      setError('Error loading speakers data');
    } finally {
      setLoading(false);
    }
  };

  const fetchVoiceProfiles = async () => {
    try {
      // Try to fetch from the API first
      try {
        const response = await api.get('/profiles/voice');
        
        if (response && response.success) {
          const data = response.data || response;
          setVoiceProfiles(data.profiles || []);
          return; // Exit if successful
        }
      } catch (apiErr) {
        console.log('Voice profiles endpoint not available');
      }
      
      // If API fails, try to get profiles from the capture data
      try {
        const captureResponse = await api.get(`/capture/${captureId}`);
        const captureData = captureResponse.data || captureResponse;
        
        if (captureData && captureData.voice_profiles) {
          setVoiceProfiles(captureData.voice_profiles);
          return;
        }
      } catch (captureErr) {
        console.log('Could not get profiles from capture data');
      }
      
      // If all else fails, set empty array
      // Don't set error state as this is supplementary
      setVoiceProfiles([]);
    } catch (err) {
      console.error('Error fetching voice profiles:', err);
      setVoiceProfiles([]);
    }
  };

  const handleSpeakerSelect = (speakerId: string) => {
    setSelectedSpeakerId(speakerId);
    if (onSpeakerSelect) {
      onSpeakerSelect(speakerId);
    }
  };

  const assignToProfile = async (speakerId: string, profileId: string, profileName: string) => {
    try {
      setIsAssigning(true);
      
      const response = await api.post('/profiles/assign-speaker', {
        speaker_id: speakerId,
        profile_id: profileId,
        capture_id: captureId
      });
      
      if (response && response.success) {
        toast.success(`Speaker assigned to ${profileName}`);
        
        // Update local state
        setSpeakers(speakers.filter(s => s.id !== speakerId));
        
        if (onSpeakerIdentified) {
          onSpeakerIdentified(speakerId, profileId);
        }
      } else {
        toast.error('Failed to assign speaker to profile');
      }
    } catch (err) {
      console.error('Error assigning speaker to profile:', err);
      toast.error('Error assigning speaker to profile');
    } finally {
      setIsAssigning(false);
    }
  };

  const createNewProfile = async (speakerId: string, profileData: any) => {
    try {
      setIsAssigning(true);
      
      // First create a new voice profile
      const createResponse = await api.post('/profiles/voice', {
        name: profileData.name,
        role: profileData.role || undefined,
        party: profileData.party || undefined,
        source_capture_id: captureId,
        source_speaker_id: speakerId
      });
      
      if (createResponse && createResponse.success) {
        const newProfileId = createResponse.data?.id || createResponse.id;
        const profileName = profileData.name;
        
        toast.success(`Created new profile: ${profileName}`);
        
        // Now assign the speaker to this profile
        await assignToProfile(speakerId, newProfileId, profileName);
        
        // Refresh voice profiles
        fetchVoiceProfiles();
        
        // Reset form
        setShowCreateForm(false);
        setNewProfileData({
          name: '',
          role: '',
          party: ''
        });
      } else {
        toast.error('Failed to create new profile');
      }
    } catch (err) {
      console.error('Error creating new profile:', err);
      toast.error('Error creating new profile');
    } finally {
      setIsAssigning(false);
    }
  };
  
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setNewProfileData(prev => ({
      ...prev,
      [name]: value
    }));
  };
  
  const handleCreateProfileSubmit = (e: React.FormEvent, speakerId: string) => {
    e.preventDefault();
    if (!newProfileData.name) {
      toast.error('Profile name is required');
      return;
    }
    createNewProfile(speakerId, newProfileData);
  };
  
  const navigateToVoiceProfiles = () => {
    router.push('/admin/voice-profiles');
  };

  const formatDuration = (seconds: number): string => {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.floor(seconds % 60);
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
  };

  if (loading) {
    return (
      <div className="bg-gray-800 rounded-lg p-6">
        <div className="flex justify-center items-center h-32">
          <div className="spinner"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-gray-800 rounded-lg p-6">
        <div className="bg-red-900 border border-red-700 text-white px-4 py-3 rounded mb-4">
          {error}
        </div>
      </div>
    );
  }

  if (speakers.length === 0) {
    return (
      <div className="bg-gray-800 rounded-lg p-6">
        <p className="text-gray-400 text-center">No unidentified speakers found</p>
      </div>
    );
  }

  return (
    <div className="bg-gray-800 rounded-lg p-6">
      <h2 className="text-xl font-semibold text-white mb-4">Unidentified Speakers</h2>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {speakers.map(speaker => (
          <div 
            key={speaker.id}
            className={`border rounded-lg p-4 cursor-pointer transition-colors ${
              selectedSpeakerId === speaker.id 
                ? 'border-blue-500 bg-gray-700' 
                : 'border-gray-700 hover:border-gray-500'
            }`}
            onClick={() => handleSpeakerSelect(speaker.id)}
          >
            <div className="flex justify-between items-start mb-2">
              <div>
                <h3 className="text-white font-medium">{speaker.name}</h3>
                <div className="text-gray-400 text-sm">
                  {speaker.segments} segments · {formatDuration(speaker.duration)}
                </div>
              </div>
              
              <div className="bg-blue-900 text-blue-200 text-xs px-2 py-1 rounded">
                {Math.round(speaker.confidence * 100)}% confidence
              </div>
            </div>
            
            {/* Face matches if available */}
            {speaker.faceMatches && speaker.faceMatches.length > 0 && (
              <div className="mt-3">
                <h4 className="text-gray-300 text-sm mb-2">Possible face matches:</h4>
                <div className="flex space-x-2 overflow-x-auto pb-2">
                  {speaker.faceMatches.map((face, index) => (
                    <div key={index} className="flex-shrink-0">
                      {face.thumbnailUrl ? (
                        <img 
                          src={face.thumbnailUrl} 
                          alt={face.profileName || 'Face'} 
                          className="w-12 h-12 object-cover rounded-full"
                          title={`${face.profileName || 'Unknown'} (${Math.round(face.confidence * 100)}%)`}
                        />
                      ) : (
                        <div className="w-12 h-12 bg-gray-600 rounded-full flex items-center justify-center">
                          <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                          </svg>
                        </div>
                      )}
                      <div className="text-center text-xs text-gray-400 mt-1">
                        {Math.round(face.confidence * 100)}%
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
            
            {/* Profile assignment options - only show when selected */}
            {selectedSpeakerId === speaker.id && (
              <div className="mt-4 border-t border-gray-700 pt-3">
                <h4 className="text-gray-300 text-sm mb-2">Assign to profile:</h4>
                
                <div className="grid grid-cols-1 gap-2">
                  {/* Existing profiles */}
                  {voiceProfiles.length > 0 ? (
                    voiceProfiles.map(profile => (
                      <button
                        key={profile.id}
                        onClick={() => assignToProfile(speaker.id, profile.id, profile.name)}
                        disabled={isAssigning}
                        className="flex items-center justify-between px-3 py-2 bg-gray-700 hover:bg-gray-600 rounded text-left text-sm text-white"
                      >
                        <span>{profile.name}</span>
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                        </svg>
                      </button>
                    ))
                  ) : (
                    <p className="text-gray-500 text-sm">No existing profiles</p>
                  )}
                  
                  {/* Create new profile button/form */}
                  {!showCreateForm ? (
                    <button
                      onClick={() => setShowCreateForm(true)}
                      disabled={isAssigning}
                      className="mt-2 px-3 py-2 bg-blue-700 hover:bg-blue-600 rounded text-sm text-white flex items-center justify-center"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                      </svg>
                      Create New Profile
                    </button>
                  ) : (
                    <form onSubmit={(e) => handleCreateProfileSubmit(e, speaker.id)} className="mt-3 border border-gray-600 rounded-md p-3 bg-gray-800">
                      <div className="mb-2">
                        <label className="block text-sm text-gray-400 mb-1">Name</label>
                        <input
                          type="text"
                          name="name"
                          value={newProfileData.name}
                          onChange={handleInputChange}
                          className="w-full px-2 py-1 bg-gray-700 border border-gray-600 rounded text-white text-sm"
                          placeholder="Profile name"
                          required
                        />
                      </div>
                      <div className="mb-2">
                        <label className="block text-sm text-gray-400 mb-1">Role</label>
                        <input
                          type="text"
                          name="role"
                          value={newProfileData.role}
                          onChange={handleInputChange}
                          className="w-full px-2 py-1 bg-gray-700 border border-gray-600 rounded text-white text-sm"
                          placeholder="MP, Minister, etc."
                        />
                      </div>
                      <div className="mb-3">
                        <label className="block text-sm text-gray-400 mb-1">Party</label>
                        <input
                          type="text"
                          name="party"
                          value={newProfileData.party}
                          onChange={handleInputChange}
                          className="w-full px-2 py-1 bg-gray-700 border border-gray-600 rounded text-white text-sm"
                          placeholder="Political party"
                        />
                      </div>
                      <div className="flex space-x-2">
                        <button
                          type="submit"
                          disabled={isAssigning}
                          className="px-3 py-1 bg-green-700 hover:bg-green-600 rounded text-sm text-white flex-1"
                        >
                          {isAssigning ? 'Creating...' : 'Create'}
                        </button>
                        <button
                          type="button"
                          onClick={() => setShowCreateForm(false)}
                          className="px-3 py-1 bg-gray-600 hover:bg-gray-500 rounded text-sm text-white"
                        >
                          Cancel
                        </button>
                      </div>
                    </form>
                  )}
                  
                  {/* Link to Voice Profiles page */}
                  <button
                    onClick={navigateToVoiceProfiles}
                    className="mt-2 px-3 py-2 bg-gray-700 hover:bg-gray-600 rounded text-sm text-white flex items-center justify-center w-full"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                    </svg>
                    Manage Voice Profiles
                  </button>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
      
      <style jsx>{`
        .spinner {
          border: 4px solid rgba(255, 255, 255, 0.1);
          width: 36px;
          height: 36px;
          border-radius: 50%;
          border-left-color: #3b82f6;
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

export default UnidentifiedSpeakersPanel;
