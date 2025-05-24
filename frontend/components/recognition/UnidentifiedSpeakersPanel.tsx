import React, { useState, useEffect } from 'react';
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
  const [speakers, setSpeakers] = useState<Speaker[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string>('');
  const [voiceProfiles, setVoiceProfiles] = useState<any[]>([]);
  const [selectedSpeakerId, setSelectedSpeakerId] = useState<string | null>(null);
  const [isAssigning, setIsAssigning] = useState<boolean>(false);

  useEffect(() => {
    if (captureId) {
      fetchSpeakers();
      fetchVoiceProfiles();
    }
  }, [captureId]);

  const fetchSpeakers = async () => {
    try {
      setLoading(true);
      
      const response = await api.get(`/recognition/speakers/${captureId}`);
      
      if (response && response.success) {
        const data = response.data || response;
        
        // Filter for unidentified speakers (those without a profileId)
        const unidentifiedSpeakers = (data.speakers || [])
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
        setError('Failed to load speakers data');
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
      const response = await api.get('/profiles/voice');
      
      if (response && response.success) {
        const data = response.data || response;
        setVoiceProfiles(data.profiles || []);
      }
    } catch (err) {
      console.error('Error fetching voice profiles:', err);
      // Don't set error state as this is supplementary
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

  const createNewProfile = async (speakerId: string, name: string) => {
    try {
      setIsAssigning(true);
      
      // First create a new voice profile
      const createResponse = await api.post('/profiles/voice', {
        name: name,
        source_capture_id: captureId,
        source_speaker_id: speakerId
      });
      
      if (createResponse && createResponse.success) {
        const newProfileId = createResponse.data?.id || createResponse.id;
        const profileName = name;
        
        toast.success(`Created new profile: ${profileName}`);
        
        // Now assign the speaker to this profile
        await assignToProfile(speakerId, newProfileId, profileName);
        
        // Refresh voice profiles
        fetchVoiceProfiles();
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
                  
                  {/* Create new profile button */}
                  <button
                    onClick={() => {
                      const name = prompt('Enter name for new profile:');
                      if (name) {
                        createNewProfile(speaker.id, name);
                      }
                    }}
                    disabled={isAssigning}
                    className="mt-2 px-3 py-2 bg-blue-700 hover:bg-blue-600 rounded text-sm text-white flex items-center justify-center"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                    </svg>
                    Create New Profile
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
