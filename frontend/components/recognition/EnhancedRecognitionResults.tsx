import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import { api } from '../../utils/api';
import { formatTime } from '../../utils/formatTime';
import { toast } from 'react-toastify';
import EnhancedVideoPlayer from '../player/EnhancedVideoPlayer';
import UnidentifiedSpeakersPanel from './UnidentifiedSpeakersPanel';

interface Speaker {
  id: string;
  name: string;
  confidence: number;
  segments: number;
  duration: number;
  profileId?: string;
}

interface Face {
  id: string;
  name?: string;
  confidence: number;
  thumbnailUrl: string;
  profileId?: string;
  startTime: number;
  endTime: number;
}

interface EnhancedRecognitionResultsProps {
  videoId: string;
}

const EnhancedRecognitionResults: React.FC<EnhancedRecognitionResultsProps> = ({ videoId }) => {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [captureData, setCaptureData] = useState<any>(null);
  const [recognitionData, setRecognitionData] = useState<any>(null);
  const [videoUrl, setVideoUrl] = useState<string>('');
  const [activeTab, setActiveTab] = useState<'speakers' | 'faces' | 'transcript'>('speakers');
  const [currentTime, setCurrentTime] = useState(0);
  const [speakers, setSpeakers] = useState<Speaker[]>([]);
  const [faces, setFaces] = useState<Face[]>([]);
  const [selectedFace, setSelectedFace] = useState<Face | null>(null);
  const [showFaceProfileModal, setShowFaceProfileModal] = useState<boolean>(false);
  const [transcriptSegments, setTranscriptSegments] = useState<any[]>([]);
  
  useEffect(() => {
    if (videoId) {
      fetchData();
    }
  }, [videoId]);
  
  const fetchData = async () => {
    try {
      setIsLoading(true);
      
      // Fetch capture data
      const captureResponse = await api.get(`/capture/${videoId}`);
      const captureDataObj = captureResponse.data || captureResponse;
      setCaptureData(captureDataObj);
      
      // Get video URL
      if (captureDataObj.video_url) {
        setVideoUrl(captureDataObj.video_url);
      } else if (captureDataObj.file_path) {
        // Construct URL from file path if needed
        setVideoUrl(`/api/v1/media/stream/${videoId}`);
      }
      
      // Fetch recognition results
      const resultsResponse = await api.get(`/recognition/results/${videoId}`);
      const resultsData = resultsResponse.data || resultsResponse;
      setRecognitionData(resultsData);
      
      // Process speakers
      if (resultsData.speakers) {
        const speakersData = resultsData.speakers.map((speaker: any) => ({
          id: speaker.id,
          name: speaker.name || 'Unknown Speaker',
          confidence: speaker.confidence || 1.0,
          segments: speaker.segments || 0,
          duration: speaker.duration || 0,
          profileId: speaker.profile_id || speaker.profileId
        }));
        setSpeakers(speakersData);
      }
      
      // Process faces
      if (resultsData.faces) {
        const facesData = resultsData.faces.map((face: any) => ({
          id: face.id,
          name: face.name || 'Unknown Face',
          confidence: face.confidence || 1.0,
          thumbnailUrl: face.thumbnail_url || face.thumbnailUrl || '/placeholder-face.png',
          profileId: face.profile_id || face.profileId,
          startTime: face.start_time || face.startTime || 0,
          endTime: face.end_time || face.endTime || 0
        }));
        setFaces(facesData);
      }
      
      // Process transcript segments
      if (resultsData.transcript && resultsData.transcript.segments) {
        setTranscriptSegments(resultsData.transcript.segments);
      }
      
    } catch (err) {
      console.error('Error fetching recognition data:', err);
      setError('Failed to load recognition data. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };
  
  const handleTimeUpdate = (time: number) => {
    setCurrentTime(time);
  };
  
  const handleSpeakerSelect = (speakerId: string) => {
    // Find speaker segments and jump to the first one
    const speakerSegment = transcriptSegments.find(
      (segment: any) => segment.speaker_id === speakerId || segment.speakerId === speakerId
    );
    
    if (speakerSegment) {
      const startTime = speakerSegment.start_time || speakerSegment.startTime || 0;
      setCurrentTime(startTime);
    }
  };
  
  const handleSpeakerIdentified = (speakerId: string, profileId: string) => {
    // Update local state to reflect the speaker identification
    setSpeakers(prevSpeakers => 
      prevSpeakers.map(speaker => 
        speaker.id === speakerId 
          ? { ...speaker, profileId }
          : speaker
      )
    );
    
    // Refresh data to get updated recognition results
    fetchData();
  };
  
  const navigateToFaceProfiles = () => {
    router.push('/admin/face-profiles');
  };
  
  const handleFaceSelect = (face: Face) => {
    setSelectedFace(face);
    setShowFaceProfileModal(true);
  };
  
  const handleAssignFaceToProfile = async (faceId: string, profileId: string) => {
    try {
      const response = await api.post('/profiles/assign-face', {
        face_id: faceId,
        profile_id: profileId,
        capture_id: videoId
      });
      
      if (response && response.success) {
        toast.success('Face assigned to profile successfully');
        
        // Update local state
        setFaces(prevFaces => 
          prevFaces.map(face => 
            face.id === faceId 
              ? { ...face, profileId }
              : face
          )
        );
        
        setShowFaceProfileModal(false);
      } else {
        toast.error('Failed to assign face to profile');
      }
    } catch (err) {
      console.error('Error assigning face to profile:', err);
      toast.error('Error assigning face to profile');
    }
  };
  
  if (isLoading) {
    return (
      <div className="bg-gray-800 text-white rounded-lg p-6 mb-6">
        <div className="flex justify-center items-center h-32">
          <div className="spinner"></div>
        </div>
      </div>
    );
  }
  
  if (error) {
    return (
      <div className="bg-gray-800 text-white rounded-lg p-6 mb-6">
        <div className="bg-red-900 border border-red-700 text-white px-4 py-3 rounded mb-4">
          {error}
        </div>
        <button 
          onClick={() => fetchData()}
          className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded"
        >
          Try Again
        </button>
      </div>
    );
  }
  
  return (
    <div className="space-y-6">
      {/* Video Player */}
      <div className="bg-gray-800 text-white rounded-lg overflow-hidden">
        <h2 className="text-xl font-semibold p-4 border-b border-gray-700">
          {captureData?.title || 'Video Playback'}
        </h2>
        <div className="p-4">
          {videoUrl ? (
            <EnhancedVideoPlayer 
              captureId={parseInt(videoId)} 
              videoUrl={videoUrl} 
              onTimeUpdate={handleTimeUpdate}
            />
          ) : (
            <div className="bg-gray-900 h-64 flex items-center justify-center">
              <p className="text-gray-400">Video not available</p>
            </div>
          )}
        </div>
      </div>
      
      {/* Tabs Navigation */}
      <div className="bg-gray-800 text-white rounded-lg overflow-hidden">
        <div className="border-b border-gray-700">
          <nav className="flex">
            <button
              className={`px-4 py-3 font-medium ${
                activeTab === 'speakers'
                  ? 'text-blue-400 border-b-2 border-blue-400'
                  : 'text-gray-400 hover:text-gray-300'
              }`}
              onClick={() => setActiveTab('speakers')}
            >
              Speakers
            </button>
            <button
              className={`px-4 py-3 font-medium ${
                activeTab === 'faces'
                  ? 'text-blue-400 border-b-2 border-blue-400'
                  : 'text-gray-400 hover:text-gray-300'
              }`}
              onClick={() => setActiveTab('faces')}
            >
              Faces
            </button>
            <button
              className={`px-4 py-3 font-medium ${
                activeTab === 'transcript'
                  ? 'text-blue-400 border-b-2 border-blue-400'
                  : 'text-gray-400 hover:text-gray-300'
              }`}
              onClick={() => setActiveTab('transcript')}
            >
              Full Transcript
            </button>
          </nav>
        </div>
        
        <div className="p-4">
          {/* Speakers Tab */}
          {activeTab === 'speakers' && (
            <div>
              <h3 className="text-lg font-medium mb-4">Speaker Recognition</h3>
              
              {/* Unidentified Speakers Panel */}
              <UnidentifiedSpeakersPanel 
                captureId={parseInt(videoId)} 
                onSpeakerSelect={handleSpeakerSelect}
                onSpeakerIdentified={handleSpeakerIdentified}
              />
              
              {/* Identified Speakers */}
              {speakers.filter(s => s.profileId).length > 0 && (
                <div className="mt-6">
                  <h3 className="text-lg font-medium mb-4">Identified Speakers</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {speakers
                      .filter(speaker => speaker.profileId)
                      .map(speaker => (
                        <div 
                          key={speaker.id}
                          className="border border-gray-700 rounded-lg p-4 hover:bg-gray-700 cursor-pointer transition-colors"
                          onClick={() => handleSpeakerSelect(speaker.id)}
                        >
                          <div className="flex justify-between items-start">
                            <div>
                              <h4 className="text-white font-medium">{speaker.name}</h4>
                              <div className="text-gray-400 text-sm">
                                {speaker.segments} segments · {formatTime(speaker.duration)}
                              </div>
                            </div>
                            <div className="bg-green-900 text-green-200 text-xs px-2 py-1 rounded">
                              Identified
                            </div>
                          </div>
                        </div>
                      ))}
                  </div>
                </div>
              )}
            </div>
          )}
          
          {/* Faces Tab */}
          {activeTab === 'faces' && (
            <div>
              <h3 className="text-lg font-medium mb-4">Face Recognition</h3>
              
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-medium">Face Recognition</h3>
                <button
                  onClick={navigateToFaceProfiles}
                  className="bg-blue-600 hover:bg-blue-700 text-white text-sm px-3 py-1 rounded flex items-center"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                  </svg>
                  Manage Face Profiles
                </button>
              </div>
              
              {faces.length === 0 ? (
                <p className="text-gray-400">No faces detected in this video.</p>
              ) : (
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
                  {faces.map(face => (
                    <div 
                      key={face.id}
                      className="border border-gray-700 rounded-lg p-3 hover:bg-gray-700 cursor-pointer transition-colors"
                    >
                      <div 
                        className="aspect-w-1 aspect-h-1 mb-2"
                        onClick={() => setCurrentTime(face.startTime)}
                      >
                        <img 
                          src={face.thumbnailUrl} 
                          alt={face.name}
                          className="object-cover rounded-md w-full h-full"
                          onError={(e) => {
                            (e.target as HTMLImageElement).src = '/placeholder-face.png';
                          }}
                        />
                      </div>
                      <div className="flex justify-between items-start">
                        <div>
                          <h4 className="text-white text-sm font-medium truncate">
                            {face.name}
                          </h4>
                          <div className="text-gray-400 text-xs">
                            {formatTime(face.startTime)}
                          </div>
                        </div>
                        <div className="text-xs bg-blue-900 text-blue-200 px-1.5 py-0.5 rounded">
                          {Math.round(face.confidence * 100)}%
                        </div>
                      </div>
                      
                      {face.profileId ? (
                        <div className="mt-2 text-xs text-green-400 flex items-center">
                          <svg xmlns="http://www.w3.org/2000/svg" className="h-3 w-3 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                          </svg>
                          Identified
                        </div>
                      ) : (
                        <button
                          onClick={() => handleFaceSelect(face)}
                          className="mt-2 w-full text-xs bg-blue-800 hover:bg-blue-700 text-white px-2 py-1 rounded flex items-center justify-center"
                        >
                          <svg xmlns="http://www.w3.org/2000/svg" className="h-3 w-3 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                          </svg>
                          Identify Face
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
          
          {/* Transcript Tab */}
          {activeTab === 'transcript' && (
            <div>
              <h3 className="text-lg font-medium mb-4">Full Transcript</h3>
              
              {transcriptSegments.length === 0 ? (
                <p className="text-gray-400">No transcript available for this video.</p>
              ) : (
                <div className="space-y-4">
                  {transcriptSegments.map((segment: any, index: number) => {
                    const speakerId = segment.speaker_id || segment.speakerId;
                    const speaker = speakers.find(s => s.id === speakerId);
                    const speakerName = speaker?.name || 'Unknown Speaker';
                    
                    return (
                      <div 
                        key={index}
                        className={`p-3 rounded-lg ${
                          currentTime >= (segment.start_time || segment.startTime || 0) && 
                          currentTime <= (segment.end_time || segment.endTime || 0)
                            ? 'bg-gray-700'
                            : 'bg-gray-900'
                        }`}
                        onClick={() => {
                          setCurrentTime(segment.start_time || segment.startTime || 0);
                        }}
                      >
                        <div className="flex justify-between items-center mb-2">
                          <div className="flex items-center">
                            <span className="font-medium text-blue-400 mr-2">{speakerName}</span>
                            <span className="text-gray-400 text-sm">
                              {formatTime(segment.start_time || segment.startTime || 0)}
                            </span>
                          </div>
                          <button
                            className="text-xs bg-blue-600 hover:bg-blue-700 text-white px-2 py-1 rounded"
                            onClick={(e) => {
                              e.stopPropagation();
                              setCurrentTime(segment.start_time || segment.startTime || 0);
                            }}
                          >
                            Jump to
                          </button>
                        </div>
                        <p className="text-white">
                          {segment.text || 'No text available'}
                        </p>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
      
      {/* Face Profile Modal */}
      {showFaceProfileModal && selectedFace && (
        <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50">
          <div className="bg-gray-800 rounded-lg p-6 max-w-md w-full mx-4">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-medium text-white">Identify Face</h3>
              <button 
                onClick={() => setShowFaceProfileModal(false)}
                className="text-gray-400 hover:text-white"
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            
            <div className="flex items-center mb-4">
              <div className="w-20 h-20 mr-4">
                <img 
                  src={selectedFace.thumbnailUrl} 
                  alt={selectedFace.name}
                  className="w-full h-full object-cover rounded-md"
                  onError={(e) => {
                    (e.target as HTMLImageElement).src = '/placeholder-face.png';
                  }}
                />
              </div>
              <div>
                <p className="text-white">{selectedFace.name}</p>
                <p className="text-gray-400 text-sm">Confidence: {Math.round(selectedFace.confidence * 100)}%</p>
                <p className="text-gray-400 text-sm">Time: {formatTime(selectedFace.startTime)}</p>
              </div>
            </div>
            
            <div className="mb-4">
              <p className="text-gray-300 mb-2">Choose an action:</p>
              <div className="space-y-2">
                <button
                  onClick={() => router.push(`/admin/face-profiles/add?face_id=${selectedFace.id}&capture_id=${videoId}`)}
                  className="w-full bg-green-600 hover:bg-green-700 text-white py-2 px-4 rounded flex items-center justify-center"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                  </svg>
                  Create New Profile
                </button>
                
                <button
                  onClick={navigateToFaceProfiles}
                  className="w-full bg-blue-600 hover:bg-blue-700 text-white py-2 px-4 rounded flex items-center justify-center"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
                  </svg>
                  Manage Face Profiles
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
      
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

export default EnhancedRecognitionResults;
