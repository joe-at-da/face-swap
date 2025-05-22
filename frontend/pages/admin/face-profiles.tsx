import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import axios from 'axios';
import { useAuth } from '../../contexts/AuthContext';
import DarkLayout from '../../components/layout/DarkLayout';
import { toast } from 'react-toastify';

// API base URL
const API_BASE_URL = 'http://localhost:8000/api/v1';

interface FaceProfile {
  id: number;
  name: string;
  role?: string;
  party?: string;
  voice_profile_id?: number;
  created_at: string;
  updated_at?: string;
  sample_count: number;
  confidence_score?: number;
  is_verified: boolean;
}

interface VoiceProfile {
  id: number;
  name: string;
  role?: string;
  party?: string;
}

const FaceProfiles: React.FC = () => {
  const router = useRouter();
  const { token, isAuthenticated } = useAuth();
  const [faceProfiles, setFaceProfiles] = useState<FaceProfile[]>([]);
  const [voiceProfiles, setVoiceProfiles] = useState<VoiceProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newProfile, setNewProfile] = useState({
    name: '',
    role: '',
    party: '',
    voice_profile_id: ''
  });
  const [selectedProfile, setSelectedProfile] = useState<FaceProfile | null>(null);
  const [uploadingImage, setUploadingImage] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  useEffect(() => {
    if (isAuthenticated) {
      fetchFaceProfiles();
      fetchVoiceProfiles();
    }
  }, [isAuthenticated]);

  const fetchFaceProfiles = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API_BASE_URL}/face-profiles`, {
        headers: {
          Authorization: `Bearer ${token}`
        }
      });
      setFaceProfiles(response.data as FaceProfile[]);
      setLoading(false);
    } catch (err) {
      console.error('Error fetching face profiles:', err);
      setError('Failed to fetch face profiles');
      setLoading(false);
    }
  };

  const fetchVoiceProfiles = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/voice-profiles`, {
        headers: {
          Authorization: `Bearer ${token}`
        }
      });
      setVoiceProfiles(response.data as VoiceProfile[]);
    } catch (err) {
      console.error('Error fetching voice profiles:', err);
    }
  };

  const handleCreateProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const payload = {
        name: newProfile.name,
        role: newProfile.role || undefined,
        party: newProfile.party || undefined,
        voice_profile_id: newProfile.voice_profile_id ? parseInt(newProfile.voice_profile_id) : undefined
      };

      const response = await axios.post(`${API_BASE_URL}/face-profiles`, payload, {
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      const newFaceProfile = response.data as FaceProfile;
      toast.success('Face profile created successfully');
      setFaceProfiles([...faceProfiles, newFaceProfile]);
      setShowCreateForm(false);
      setNewProfile({
        name: '',
        role: '',
        party: '',
        voice_profile_id: ''
      });
    } catch (err) {
      console.error('Error creating face profile:', err);
      toast.error('Failed to create face profile');
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setSelectedFile(e.target.files[0]);
    }
  };

  const handleUploadSample = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedProfile || !selectedFile) return;

    try {
      setUploadingImage(true);
      const formData = new FormData();
      formData.append('file', selectedFile);

      const response = await axios.post(
        `${API_BASE_URL}/face-profiles/${selectedProfile.id}/samples`,
        formData,
        {
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'multipart/form-data'
          }
        }
      );

      toast.success('Face sample uploaded successfully');
      setSelectedFile(null);
      
      // Refresh the face profiles to update the sample count
      fetchFaceProfiles();
      setUploadingImage(false);
    } catch (err) {
      console.error('Error uploading face sample:', err);
      toast.error('Failed to upload face sample');
      setUploadingImage(false);
    }
  };

  const handleLinkVoiceProfile = async (faceProfileId: number, voiceProfileId: number) => {
    try {
      await axios.post(
        `${API_BASE_URL}/face-profiles/${faceProfileId}/link-voice`,
        { voice_profile_id: voiceProfileId },
        {
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        }
      );

      toast.success('Profiles linked successfully');
      fetchFaceProfiles(); // Refresh the data
    } catch (err) {
      console.error('Error linking profiles:', err);
      toast.error('Failed to link profiles');
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setNewProfile({
      ...newProfile,
      [name]: value
    });
  };

  return (
    <DarkLayout title="Face Profiles">
      <div className="container mx-auto px-4 py-8">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-3xl font-bold text-gray-800">Face Profiles</h1>
          <button
            onClick={() => setShowCreateForm(!showCreateForm)}
            className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded"
          >
            {showCreateForm ? 'Cancel' : 'Create New Profile'}
          </button>
        </div>

        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
            {error}
          </div>
        )}

        {showCreateForm && (
          <div className="bg-white shadow-md rounded px-8 pt-6 pb-8 mb-6">
            <h2 className="text-xl font-semibold mb-4">Create New Face Profile</h2>
            <form onSubmit={handleCreateProfile}>
              <div className="mb-4">
                <label className="block text-gray-700 text-sm font-bold mb-2" htmlFor="name">
                  Name
                </label>
                <input
                  className="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline"
                  id="name"
                  type="text"
                  name="name"
                  value={newProfile.name}
                  onChange={handleInputChange}
                  required
                />
              </div>
              <div className="mb-4">
                <label className="block text-gray-700 text-sm font-bold mb-2" htmlFor="role">
                  Role
                </label>
                <input
                  className="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline"
                  id="role"
                  type="text"
                  name="role"
                  value={newProfile.role}
                  onChange={handleInputChange}
                />
              </div>
              <div className="mb-4">
                <label className="block text-gray-700 text-sm font-bold mb-2" htmlFor="party">
                  Party
                </label>
                <input
                  className="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline"
                  id="party"
                  type="text"
                  name="party"
                  value={newProfile.party}
                  onChange={handleInputChange}
                />
              </div>
              <div className="mb-4">
                <label className="block text-gray-700 text-sm font-bold mb-2" htmlFor="voice_profile_id">
                  Voice Profile
                </label>
                <select
                  className="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline"
                  id="voice_profile_id"
                  name="voice_profile_id"
                  value={newProfile.voice_profile_id}
                  onChange={handleInputChange}
                >
                  <option value="">-- Select Voice Profile --</option>
                  {voiceProfiles.map(profile => (
                    <option key={profile.id} value={profile.id}>
                      {profile.name} {profile.role ? `(${profile.role})` : ''}
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex items-center justify-end">
                <button
                  className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline"
                  type="submit"
                >
                  Create Profile
                </button>
              </div>
            </form>
          </div>
        )}

        {selectedProfile && (
          <div className="bg-white shadow-md rounded px-8 pt-6 pb-8 mb-6">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-semibold">Upload Face Sample</h2>
              <button
                onClick={() => setSelectedProfile(null)}
                className="text-gray-500 hover:text-gray-700"
              >
                ✕
              </button>
            </div>
            <p className="mb-4">
              Upload a face image for <strong>{selectedProfile.name}</strong>
            </p>
            <form onSubmit={handleUploadSample}>
              <div className="mb-4">
                <label className="block text-gray-700 text-sm font-bold mb-2" htmlFor="file">
                  Face Image
                </label>
                <input
                  className="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline"
                  id="file"
                  type="file"
                  accept="image/*"
                  onChange={handleFileChange}
                  required
                />
              </div>
              <div className="flex items-center justify-end">
                <button
                  className="bg-green-500 hover:bg-green-700 text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline"
                  type="submit"
                  disabled={uploadingImage || !selectedFile}
                >
                  {uploadingImage ? 'Uploading...' : 'Upload Sample'}
                </button>
              </div>
            </form>
          </div>
        )}

        {loading ? (
          <div className="text-center py-10">
            <div className="spinner"></div>
            <p className="mt-2 text-gray-600">Loading face profiles...</p>
          </div>
        ) : (
          <div className="bg-white shadow-md rounded overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Name
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Role
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Party
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Samples
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Voice Profile
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {faceProfiles.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-6 py-4 text-center text-gray-500">
                      No face profiles found
                    </td>
                  </tr>
                ) : (
                  faceProfiles.map(profile => (
                    <tr key={profile.id}>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-medium text-gray-900">{profile.name}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-500">{profile.role || '-'}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-500">{profile.party || '-'}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-500">{profile.sample_count}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        {profile.voice_profile_id ? (
                          <div className="text-sm text-gray-900">
                            {voiceProfiles.find(vp => vp.id === profile.voice_profile_id)?.name || 'Linked'}
                          </div>
                        ) : (
                          <select
                            className="text-sm border rounded py-1 px-2"
                            onChange={(e) => {
                              const voiceProfileId = parseInt(e.target.value);
                              if (voiceProfileId) {
                                handleLinkVoiceProfile(profile.id, voiceProfileId);
                              }
                            }}
                            defaultValue=""
                          >
                            <option value="">-- Link Voice Profile --</option>
                            {voiceProfiles.map(vp => (
                              <option key={vp.id} value={vp.id}>
                                {vp.name}
                              </option>
                            ))}
                          </select>
                        )}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                        <button
                          onClick={() => setSelectedProfile(profile)}
                          className="text-indigo-600 hover:text-indigo-900 mr-4"
                        >
                          Add Sample
                        </button>
                        <button
                          onClick={() => router.push(`/admin/face-profiles/${profile.id}`)}
                          className="text-green-600 hover:text-green-900"
                        >
                          View
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
      <style jsx>{`
        .spinner {
          border: 4px solid rgba(0, 0, 0, 0.1);
          width: 36px;
          height: 36px;
          border-radius: 50%;
          border-left-color: #09f;
          animation: spin 1s linear infinite;
          margin: 0 auto;
        }
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
    </DarkLayout>
  );
};

export default FaceProfiles;
