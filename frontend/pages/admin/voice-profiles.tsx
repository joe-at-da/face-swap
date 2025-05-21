import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../../utils/api';
import { toast } from 'react-toastify';
import AdminLayout from '../../components/layouts/AdminLayout';
import { useAuth } from '../../contexts/AuthContext';

interface VoiceProfile {
  id: string;
  name: string;
  role: string;
  party: string;
  created_at: string;
  updated_at: string;
  sample_count: number;
  confidence_score: number;
}

const VoiceProfilesPage = () => {
  const { token } = useAuth();
  const queryClient = useQueryClient();
  const [selectedProfile, setSelectedProfile] = useState<VoiceProfile | null>(null);
  const [audioFile, setAudioFile] = useState<File | null>(null);
  const [newProfileName, setNewProfileName] = useState('');
  const [newProfileRole, setNewProfileRole] = useState('');
  const [newProfileParty, setNewProfileParty] = useState('');
  const [isCreating, setIsCreating] = useState(false);

  // Fetch voice profiles
  const { data: profiles, isLoading, error } = useQuery<VoiceProfile[]>({
    queryKey: ['voiceProfiles'],
    queryFn: async () => {
      const response = await api.get('/voice-profiles');
      // Handle both array response and {profiles: []} response format
      return Array.isArray(response.data) ? response.data : (response.data?.profiles || []);
    },
    enabled: !!token,
    staleTime: 60000
  });

  // Upload audio sample mutation
  const uploadSampleMutation = useMutation({
    mutationFn: async ({ profileId, file }: { profileId: string, file: File }) => {
      const formData = new FormData();
      formData.append('audio_file', file);
      
      const response = await api.post(`/voice-profiles/${profileId}/samples`, formData);
      return response.data;
    },
    onSuccess: () => {
      toast.success('Audio sample uploaded successfully');
      queryClient.invalidateQueries({ queryKey: ['voiceProfiles'] });
      setAudioFile(null);
    },
    onError: (error) => {
      toast.error(`Failed to upload audio sample: ${error instanceof Error ? error.message : String(error)}`);
    }
  });

  // Create new profile mutation
  const createProfileMutation = useMutation({
    mutationFn: async (profileData: { name: string, role: string, party: string }) => {
      const response = await api.post('/voice-profiles', profileData);
      return response.data;
    },
    onSuccess: () => {
      toast.success('Voice profile created successfully');
      queryClient.invalidateQueries({ queryKey: ['voiceProfiles'] });
      setNewProfileName('');
      setNewProfileRole('');
      setNewProfileParty('');
      setIsCreating(false);
    },
    onError: (error) => {
      toast.error(`Failed to create voice profile: ${error instanceof Error ? error.message : String(error)}`);
    }
  });

  // Delete profile mutation
  const deleteProfileMutation = useMutation({
    mutationFn: async (profileId: string) => {
      const response = await api.delete(`/voice-profiles/${profileId}`);
      return response.data;
    },
    onSuccess: () => {
      toast.success('Voice profile deleted successfully');
      queryClient.invalidateQueries({ queryKey: ['voiceProfiles'] });
      setSelectedProfile(null);
    },
    onError: (error) => {
      toast.error(`Failed to delete voice profile: ${error instanceof Error ? error.message : String(error)}`);
    }
  });

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setAudioFile(e.target.files[0]);
    }
  };

  const handleUploadSample = () => {
    if (!selectedProfile || !audioFile) return;
    uploadSampleMutation.mutate({ profileId: selectedProfile.id, file: audioFile });
  };

  const handleCreateProfile = () => {
    if (!newProfileName) {
      toast.error('Profile name is required');
      return;
    }
    
    createProfileMutation.mutate({
      name: newProfileName,
      role: newProfileRole,
      party: newProfileParty
    });
  };

  const handleDeleteProfile = () => {
    if (!selectedProfile) return;
    
    if (window.confirm(`Are you sure you want to delete the voice profile for ${selectedProfile.name}?`)) {
      deleteProfileMutation.mutate(selectedProfile.id);
    }
  };

  return (
    <AdminLayout title="Voice Profiles">
      <div className="container mx-auto px-4 py-8">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-2xl font-semibold">Voice Profiles Management</h1>
          <button
            onClick={() => setIsCreating(true)}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Create New Profile
          </button>
        </div>

        {isLoading ? (
          <div className="flex justify-center items-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
          </div>
        ) : error ? (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative" role="alert">
            <strong className="font-bold">Error!</strong>
            <span className="block sm:inline"> Failed to load voice profiles.</span>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Profile List */}
            <div className="bg-gray-800 rounded-lg shadow p-4 md:col-span-1">
              <h2 className="text-xl font-semibold mb-4 text-white">Voice Profiles</h2>
              {profiles && profiles.length > 0 ? (
                <div className="space-y-2 max-h-[500px] overflow-y-auto">
                  {profiles.map(profile => (
                    <div
                      key={profile.id}
                      onClick={() => setSelectedProfile(profile)}
                      className={`p-3 rounded-lg cursor-pointer transition-colors ${
                        selectedProfile?.id === profile.id
                          ? 'bg-blue-700 text-white'
                          : 'bg-gray-700 text-blue-100 hover:bg-gray-600'
                      }`}
                    >
                      <div className="font-medium">{profile.name}</div>
                      <div className="text-sm opacity-80">{profile.role}</div>
                      <div className="flex justify-between items-center mt-1">
                        <span className="text-xs opacity-70">{profile.party}</span>
                        <span className="text-xs bg-gray-800 px-2 py-1 rounded-full">
                          {profile.sample_count} samples
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-gray-400">
                  <p>No voice profiles found</p>
                  <p className="text-sm mt-2">Create a new profile to get started</p>
                </div>
              )}
            </div>

            {/* Profile Details */}
            <div className="bg-gray-800 rounded-lg shadow p-4 md:col-span-2">
              {isCreating ? (
                <div>
                  <div className="flex justify-between items-center mb-4">
                    <h2 className="text-xl font-semibold text-white">Create New Voice Profile</h2>
                    <button
                      onClick={() => setIsCreating(false)}
                      className="text-gray-400 hover:text-white"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-1">Name</label>
                      <input
                        type="text"
                        value={newProfileName}
                        onChange={(e) => setNewProfileName(e.target.value)}
                        className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white"
                        placeholder="e.g. John Smith MP"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-1">Role</label>
                      <input
                        type="text"
                        value={newProfileRole}
                        onChange={(e) => setNewProfileRole(e.target.value)}
                        className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white"
                        placeholder="e.g. Minister for Digital"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-1">Party</label>
                      <input
                        type="text"
                        value={newProfileParty}
                        onChange={(e) => setNewProfileParty(e.target.value)}
                        className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-white"
                        placeholder="e.g. Conservative"
                      />
                    </div>
                    <div className="pt-4">
                      <button
                        onClick={handleCreateProfile}
                        disabled={createProfileMutation.isPending}
                        className="w-full px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-gray-500 disabled:cursor-not-allowed"
                      >
                        {createProfileMutation.isPending ? 'Creating...' : 'Create Profile'}
                      </button>
                    </div>
                  </div>
                </div>
              ) : selectedProfile ? (
                <div>
                  <div className="flex justify-between items-center mb-4">
                    <h2 className="text-xl font-semibold text-white">{selectedProfile.name}</h2>
                    <button
                      onClick={handleDeleteProfile}
                      className="text-red-500 hover:text-red-700"
                      disabled={deleteProfileMutation.isPending}
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    </button>
                  </div>
                  <div className="grid grid-cols-2 gap-4 mb-6">
                    <div className="bg-gray-700 p-3 rounded-lg">
                      <div className="text-sm text-gray-400">Role</div>
                      <div className="text-white">{selectedProfile.role || 'Not specified'}</div>
                    </div>
                    <div className="bg-gray-700 p-3 rounded-lg">
                      <div className="text-sm text-gray-400">Party</div>
                      <div className="text-white">{selectedProfile.party || 'Not specified'}</div>
                    </div>
                    <div className="bg-gray-700 p-3 rounded-lg">
                      <div className="text-sm text-gray-400">Audio Samples</div>
                      <div className="text-white">{selectedProfile.sample_count}</div>
                    </div>
                    <div className="bg-gray-700 p-3 rounded-lg">
                      <div className="text-sm text-gray-400">Confidence Score</div>
                      <div className="text-white">{selectedProfile.confidence_score ? `${(selectedProfile.confidence_score * 100).toFixed(1)}%` : 'N/A'}</div>
                    </div>
                  </div>

                  <div className="bg-gray-700 p-4 rounded-lg mb-4">
                    <h3 className="text-lg font-medium text-white mb-3">Upload Audio Sample</h3>
                    <div className="space-y-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-300 mb-2">
                          Audio File (MP3, WAV, M4A)
                        </label>
                        <input
                          type="file"
                          accept="audio/*"
                          onChange={handleFileChange}
                          className="block w-full text-sm text-gray-400
                            file:mr-4 file:py-2 file:px-4
                            file:rounded-full file:border-0
                            file:text-sm file:font-semibold
                            file:bg-blue-600 file:text-white
                            hover:file:bg-blue-700"
                        />
                      </div>
                      <button
                        onClick={handleUploadSample}
                        disabled={!audioFile || uploadSampleMutation.isPending}
                        className="w-full px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-gray-500 disabled:cursor-not-allowed"
                      >
                        {uploadSampleMutation.isPending ? 'Uploading...' : 'Upload Sample'}
                      </button>
                    </div>
                  </div>

                  <div className="bg-gray-700 p-4 rounded-lg">
                    <h3 className="text-lg font-medium text-white mb-3">Usage Instructions</h3>
                    <ul className="list-disc list-inside text-gray-300 space-y-2">
                      <li>Upload at least 3 audio samples for better recognition</li>
                      <li>Use clear audio with minimal background noise</li>
                      <li>Samples should be 10-30 seconds of the speaker talking</li>
                      <li>Include different speech patterns for better accuracy</li>
                      <li>After uploading samples, enable speaker identification when transcribing</li>
                    </ul>
                  </div>
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center h-full py-12 text-gray-400">
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-16 w-16 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                  </svg>
                  <p className="text-lg">Select a voice profile or create a new one</p>
                  <p className="text-sm mt-2 max-w-md text-center">
                    Voice profiles help identify speakers in audio transcriptions. Create profiles for MPs and other frequent speakers.
                  </p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </AdminLayout>
  );
};

export default VoiceProfilesPage;
