import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import { api } from '../../utils/api';
import { formatTime } from '../../utils/formatTime';
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
              
              {faces.length === 0 ? (
                <p className="text-gray-400">No faces detected in this video.</p>
              ) : (
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
                  {faces.map(face => (
                    <div 
                      key={face.id}
                      className="border border-gray-700 rounded-lg p-3 hover:bg-gray-700 cursor-pointer transition-colors"
                      onClick={() => {
                        setCurrentTime(face.startTime);
                      }}
                    >
                      <div className="aspect-w-1 aspect-h-1 mb-2">
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
                      {face.profileId && (
                        <div className="mt-1 text-xs text-green-400">
                          Identified
                        </div>
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
