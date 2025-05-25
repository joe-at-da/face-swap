import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import { toast } from 'react-toastify';
import { api } from '../../utils/api';

interface SocialMediaShareProps {
  clipId: number;
  clipTitle: string;
  clipUrl: string;
  thumbnailUrl?: string;
  duration: number;
  hasTranscription: boolean;
  startTime?: string;
  endTime?: string;
}

interface SpeakerProfile {
  id: number;
  name: string;
  role?: string;
  party?: string;
  image_url?: string;
}

interface FaceRecognitionData {
  id: number;
  person_name: string;
  confidence: number;
  timestamp: string;
  face_box?: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
  image_url?: string;
}

interface SpeakerRecognitionData {
  id: number;
  speaker_name: string;
  confidence: number;
  timestamp: string;
  duration: number;
}

interface TranscriptionSegment {
  id: number;
  start_time: number;
  end_time: number;
  text: string;
  speaker_id?: string;
  speaker?: string;
}

const SocialMediaShare: React.FC<SocialMediaShareProps> = ({
  clipId,
  clipTitle,
  clipUrl,
  thumbnailUrl,
  duration,
  hasTranscription,
  startTime,
  endTime
}) => {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(false);
  const [transcription, setTranscription] = useState<any>(null);
  const [speakerProfiles, setSpeakerProfiles] = useState<SpeakerProfile[]>([]);
  const [faceRecognitionData, setFaceRecognitionData] = useState<FaceRecognitionData[]>([]);
  const [speakerRecognitionData, setSpeakerRecognitionData] = useState<SpeakerRecognitionData[]>([]);
  const [shareText, setShareText] = useState('');
  const [platform, setPlatform] = useState<'twitter' | 'linkedin' | 'facebook'>('twitter');
  const [includeTranscript, setIncludeTranscript] = useState(true);
  const [includeSpeakers, setIncludeSpeakers] = useState(true);
  const [includeFaceRecognition, setIncludeFaceRecognition] = useState(true);
  const [clipStartTime, setClipStartTime] = useState<Date | null>(startTime ? new Date(startTime) : null);
  const [clipEndTime, setClipEndTime] = useState<Date | null>(endTime ? new Date(endTime) : null);
  
  // Character limits for different platforms
  const characterLimits = {
    twitter: 280,
    linkedin: 700,
    facebook: 500
  };
  
  // Track clip status
  const [clipStatus, setClipStatus] = useState<string>('');
  
  useEffect(() => {
    // Check clip status first
    const checkClipStatus = async () => {
      try {
        const clipData = await api.get(`/clips/${clipId}`);
        setClipStatus(clipData.status);
        
        // Only proceed with other data fetching if clip is COMPLETED
        if (clipData.status === 'COMPLETED') {
          // Load transcription if available
          if (hasTranscription) {
            fetchTranscription();
          }
          
          // Fetch face and speaker recognition data
          fetchRecognitionData();
        }
      } catch (error) {
        console.error('Error checking clip status:', error);
      }
    };
    
    checkClipStatus();
    
    // Generate initial share text
    generateShareText();
  }, [clipId, hasTranscription, clipStartTime, clipEndTime]);
  
  // Fetch transcription data
  const fetchTranscription = async () => {
    try {
      setIsLoading(true);
      const data = await api.get(`/transcriptions/clip/${clipId}`);
      setTranscription(data);
      
      // Extract unique speaker IDs from transcription
      if (data && data.segments) {
        const speakerIdsArray = data.segments
          .filter((seg: TranscriptionSegment) => seg.speaker_id)
          .map((seg: TranscriptionSegment) => seg.speaker_id);
        
        // Get unique speaker IDs
        const speakerIds = speakerIdsArray.filter((id: string, index: number) => 
          speakerIdsArray.indexOf(id) === index
        );
        
        // Fetch speaker profiles
        if (speakerIds.length > 0) {
          fetchSpeakerProfiles(speakerIds);
        }
      }
    } catch (error) {
      console.error('Error fetching transcription:', error);
      toast.error('Failed to load transcription');
    } finally {
      setIsLoading(false);
    }
  };
  
  // Fetch speaker profiles
  const fetchSpeakerProfiles = async (speakerIds: string[]) => {
    try {
      const profiles = await Promise.all(
        speakerIds.map(async (id) => {
          try {
            return await api.get(`/profiles/voice/${id}`);
          } catch (error) {
            console.error(`Failed to fetch profile for speaker ${id}:`, error);
            return null;
          }
        })
      );
      
      setSpeakerProfiles(profiles.filter(Boolean));
    } catch (error) {
      console.error('Error fetching speaker profiles:', error);
    }
  };
  
  // Fetch face and speaker recognition data
  const fetchRecognitionData = async () => {
    if (!clipId || clipStatus !== 'COMPLETED') {
      console.log('Skipping recognition data fetch - clip not completed yet');
      return;
    }
    
    try {
      setIsLoading(true);
      
      // Fetch face recognition data
      try {
        const faceData = await api.get(`/recognition/faces/clip/${clipId}`);
        if (Array.isArray(faceData)) {
          // Filter by time range if start and end times are available
          const filteredFaceData = clipStartTime && clipEndTime 
            ? faceData.filter(item => {
                const timestamp = new Date(item.timestamp);
                return timestamp >= clipStartTime && timestamp <= clipEndTime;
              })
            : faceData;
            
          setFaceRecognitionData(filteredFaceData);
        } else if (faceData) {
          setFaceRecognitionData([faceData]);
        }
      } catch (error) {
        // Silently handle 404 errors for clips still being processed
        if (error.message?.includes('404')) {
          console.log('Face recognition data not available yet - clip may still be processing');
        } else {
          console.log('Error fetching face recognition data:', error);
        }
      }
      
      // Fetch speaker recognition data
      try {
        const speakerData = await api.get(`/recognition/speakers/clip/${clipId}`);
        if (Array.isArray(speakerData)) {
          // Filter by time range if start and end times are available
          const filteredSpeakerData = clipStartTime && clipEndTime 
            ? speakerData.filter(item => {
                const timestamp = new Date(item.timestamp);
                return timestamp >= clipStartTime && timestamp <= clipEndTime;
              })
            : speakerData;
            
          setSpeakerRecognitionData(filteredSpeakerData);
        } else if (speakerData) {
          setSpeakerRecognitionData([speakerData]);
        }
      } catch (error) {
        // Silently handle 404 errors for clips still being processed
        if (error.message?.includes('404')) {
          console.log('Speaker recognition data not available yet - clip may still be processing');
        } else {
          console.log('Error fetching speaker recognition data:', error);
        }
      }
    } catch (error) {
      console.error('Error fetching recognition data:', error);
    } finally {
      setIsLoading(false);
    }
  };
  
  // Generate share text based on selected options
  const generateShareText = () => {
    let text = `${clipTitle}`;
    
    // Add clip duration and timestamp info
    const formattedDuration = `${Math.floor(duration / 60)}:${(duration % 60).toString().padStart(2, '0')}`;
    text += `\n\nDuration: ${formattedDuration}`;
    
    if (clipStartTime && clipEndTime) {
      const formatDate = (date: Date) => {
        return date.toLocaleString('en-GB', {
          day: 'numeric',
          month: 'short',
          year: 'numeric',
          hour: '2-digit',
          minute: '2-digit'
        });
      };
      
      text += `\nRecorded: ${formatDate(clipStartTime)} to ${formatDate(clipEndTime)}`;
    }
    
    // Add comprehensive speaker information if available and selected
    if (includeSpeakers) {
      // Add speaker profiles
      if (speakerProfiles.length > 0) {
        const speakerInfo = speakerProfiles.map(profile => {
          let info = profile.name;
          if (profile.role) info += `, ${profile.role}`;
          if (profile.party) info += ` (${profile.party})`;
          return info;
        }).join('\n• ');
        
        text += `\n\nFeaturing:\n• ${speakerInfo}`;
      }
      
      // Add speaker recognition data
      if (speakerRecognitionData.length > 0) {
        // Group by speaker name and calculate average confidence
        const speakerStats = speakerRecognitionData.reduce((acc: {[key: string]: {count: number, totalConfidence: number}}, item) => {
          if (!acc[item.speaker_name]) {
            acc[item.speaker_name] = { count: 0, totalConfidence: 0 };
          }
          acc[item.speaker_name].count += 1;
          acc[item.speaker_name].totalConfidence += item.confidence;
          return acc;
        }, {});
        
        const speakerSummary = Object.entries(speakerStats).map(([name, stats]) => {
          const avgConfidence = Math.round((stats.totalConfidence / stats.count) * 100);
          return `${name} (${avgConfidence}% confidence, ${stats.count} segments)`;
        }).join('\n• ');
        
        if (speakerSummary && !text.includes('Featuring:')) {
          text += `\n\nSpeakers Identified:\n• ${speakerSummary}`;
        }
      }
    }
    
    // Add face recognition data if available and selected
    if (includeFaceRecognition && faceRecognitionData.length > 0) {
      // Group by person name and calculate average confidence
      const faceStats = faceRecognitionData.reduce((acc: {[key: string]: {count: number, totalConfidence: number}}, item) => {
        if (!acc[item.person_name]) {
          acc[item.person_name] = { count: 0, totalConfidence: 0 };
        }
        acc[item.person_name].count += 1;
        acc[item.person_name].totalConfidence += item.confidence;
        return acc;
      }, {});
      
      const faceSummary = Object.entries(faceStats).map(([name, stats]) => {
        const avgConfidence = Math.round((stats.totalConfidence / stats.count) * 100);
        return `${name} (${avgConfidence}% confidence, visible in ${stats.count} frames)`;
      }).join('\n• ');
      
      text += `\n\nFaces Identified:\n• ${faceSummary}`;
    }
    
    // Add transcript excerpt if available and selected
    if (includeTranscript && transcription && transcription.segments && transcription.segments.length > 0) {
      // Filter segments by time range if start and end times are available
      let relevantSegments = transcription.segments;
      if (clipStartTime && clipEndTime) {
        const startTimeSeconds = clipStartTime.getTime() / 1000;
        const endTimeSeconds = clipEndTime.getTime() / 1000;
        
        relevantSegments = transcription.segments.filter((seg: TranscriptionSegment) => {
          return seg.start_time >= startTimeSeconds && seg.end_time <= endTimeSeconds;
        });
      }
      
      // Get first 2-3 segments depending on length
      const segments = relevantSegments.slice(0, 3);
      const excerptText = segments
        .map((seg: TranscriptionSegment) => {
          let text = seg.text;
          if (seg.speaker) text = `${seg.speaker}: ${text}`;
          return text;
        })
        .join('\n');
      
      // Truncate if needed
      const maxExcerptLength = 200;
      const truncatedExcerpt = excerptText.length > maxExcerptLength
        ? excerptText.substring(0, maxExcerptLength) + '...'
        : excerptText;
      
      text += `\n\nTranscript Excerpt:\n"${truncatedExcerpt}"`;
    }
    
    // Add clip URL
    text += `\n\nWatch the full clip: ${window.location.origin}/clips/${clipId}`;
    
    setShareText(text);
  };
  
  // Handle text change
  const handleTextChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setShareText(e.target.value);
  };
  
  // Handle platform change
  const handlePlatformChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setPlatform(e.target.value as 'twitter' | 'linkedin' | 'facebook');
  };
  
  // Handle checkbox changes
  const handleCheckboxChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, checked } = e.target;
    
    if (name === 'includeTranscript') {
      setIncludeTranscript(checked);
    } else if (name === 'includeSpeakers') {
      setIncludeSpeakers(checked);
    } else if (name === 'includeFaceRecognition') {
      setIncludeFaceRecognition(checked);
    }
    
    // Re-generate share text after changing options
    setTimeout(() => {
      generateShareText();
    }, 0);
  };
  
  // Share to social media
  const shareToSocialMedia = async () => {
    let url = '';
    const currentUrl = typeof window !== 'undefined' ? window.location.href : '';
    
    // First create a record in the system
    try {
      // Create post record in the database
      const response = await api.post('/social/posts/', {
        content: shareText,
        platform: platform,
        video_clip_id: clipId,
        status: 'posted',
        posted_at: new Date().toISOString()
      });
      
      console.log('Social media post created:', response);
      toast.success(`Post created for ${platform}`);
      
      // Then open the external platform
      switch (platform) {
        case 'twitter':
          url = `https://twitter.com/intent/tweet?text=${encodeURIComponent(shareText)}`;
          break;
        case 'linkedin':
          url = `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(currentUrl)}&summary=${encodeURIComponent(shareText)}`;
          break;
        case 'facebook':
          url = `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(currentUrl)}&quote=${encodeURIComponent(shareText)}`;
          break;
      }
      
      if (url && typeof window !== 'undefined') {
        window.open(url, '_blank');
      }
    } catch (error: any) {
      console.error('Failed to create social media post:', error);
      toast.error(`Failed to create post: ${error?.message || 'Unknown error'}`);
      
      // Still open the external platform even if our internal record fails
      switch (platform) {
        case 'twitter':
          url = `https://twitter.com/intent/tweet?text=${encodeURIComponent(shareText)}`;
          break;
        case 'linkedin':
          url = `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(currentUrl)}&summary=${encodeURIComponent(shareText)}`;
          break;
        case 'facebook':
          url = `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(currentUrl)}&quote=${encodeURIComponent(shareText)}`;
          break;
      }
      
      if (url && typeof window !== 'undefined') {
        window.open(url, '_blank');
      }
    }
  };
  
  // Create social media post in the system
  const createSocialPost = async () => {
    try {
      // First try to create the post in the database
      const response = await api.post('/social/posts/', {
        // Use the correct field name for content
        content: shareText, // This matches the schema requirement
        platform: platform,
        video_clip_id: clipId,
        status: 'draft'
      });
      
      console.log('Social media post created:', response);
      toast.success(`Post created for ${platform}`);
      
      // Redirect to the social dashboard
      router.push('/social');
    } catch (error: any) {
      console.error('Failed to create social media post:', error);
      toast.error(`Failed to create post: ${error?.message || 'Unknown error'}`);
      
      // Fallback to the redirect approach if the API call fails
      router.push({
        pathname: '/social/new',
        query: {
          clip_id: clipId,
          content: shareText,
          platform
        }
      });
    }
  };
  
  // Calculate remaining characters
  const remainingCharacters = characterLimits[platform] - shareText.length;
  
  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
        <h2 className="text-lg font-medium text-gray-800">Share to Social Media</h2>
        <div className="flex items-center space-x-2">
          <select
            value={platform}
            onChange={handlePlatformChange}
            className="form-select text-sm"
          >
            <option value="twitter">Twitter</option>
            <option value="facebook">Facebook</option>
            <option value="linkedin">LinkedIn</option>
          </select>
        </div>
      </div>
      
      <div className="p-6">
        <div className="space-y-4">
          {/* Preview */}
          <div className="flex space-x-4">
            {thumbnailUrl && (
              <div className="flex-shrink-0">
                <img 
                  src={thumbnailUrl} 
                  alt={clipTitle} 
                  className="w-24 h-24 object-cover rounded"
                />
              </div>
            )}
            
            <div className="flex-grow">
              <h3 className="font-medium text-gray-900">{clipTitle}</h3>
              <p className="text-sm text-gray-500">
                Duration: {Math.floor(duration / 60)}:{(duration % 60).toString().padStart(2, '0')}
              </p>
              
              {speakerProfiles.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-2">
                  {speakerProfiles.map(profile => (
                    <div 
                      key={profile.id} 
                      className="inline-flex items-center bg-blue-50 px-2 py-1 rounded-full text-xs"
                    >
                      {profile.image_url && (
                        <img 
                          src={profile.image_url} 
                          alt={profile.name} 
                          className="w-4 h-4 rounded-full mr-1"
                        />
                      )}
                      <span>{profile.name}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
          
          {/* Recognition Summary */}
          {(faceRecognitionData.length > 0 || speakerRecognitionData.length > 0) && (
            <div className="mb-4 p-4 bg-gray-800 text-white rounded-md">
              <h3 className="text-lg font-medium mb-2">Recognition Data Summary</h3>
              
              {speakerRecognitionData.length > 0 && (
                <div className="mb-3">
                  <h4 className="text-md font-medium text-blue-400">Speaker Recognition</h4>
                  <ul className="list-disc pl-5 text-sm text-gray-300">
                    {Object.entries(speakerRecognitionData.reduce((acc: {[key: string]: number}, item) => {
                      acc[item.speaker_name] = (acc[item.speaker_name] || 0) + 1;
                      return acc;
                    }, {})).map(([name, count], idx) => (
                      <li key={idx}>{name} ({count} segments)</li>
                    ))}
                  </ul>
                </div>
              )}
              
              {faceRecognitionData.length > 0 && (
                <div>
                  <h4 className="text-md font-medium text-green-400">Face Recognition</h4>
                  <ul className="list-disc pl-5 text-sm text-gray-300">
                    {Object.entries(faceRecognitionData.reduce((acc: {[key: string]: number}, item) => {
                      acc[item.person_name] = (acc[item.person_name] || 0) + 1;
                      return acc;
                    }, {})).map(([name, count], idx) => (
                      <li key={idx}>{name} ({count} frames)</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
          
          {/* Options */}
          <div className="flex flex-wrap gap-4 mb-4">
            <label className="flex items-center">
              <input
                type="checkbox"
                name="includeTranscript"
                checked={includeTranscript}
                onChange={handleCheckboxChange}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                disabled={!hasTranscription}
              />
              <span className="ml-2 text-sm text-gray-300">Include transcript excerpt</span>
            </label>
            
            <label className="flex items-center">
              <input
                type="checkbox"
                name="includeSpeakers"
                checked={includeSpeakers}
                onChange={handleCheckboxChange}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                disabled={speakerProfiles.length === 0 && speakerRecognitionData.length === 0}
              />
              <span className="ml-2 text-sm text-gray-300">Include speaker info</span>
            </label>
            
            <label className="flex items-center">
              <input
                type="checkbox"
                name="includeFaceRecognition"
                checked={includeFaceRecognition}
                onChange={handleCheckboxChange}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                disabled={faceRecognitionData.length === 0}
              />
              <span className="ml-2 text-sm text-gray-300">Include face recognition data</span>
            </label>
          </div>
          
          {/* Text area */}
          <div>
            <textarea
              value={shareText}
              onChange={handleTextChange}
              rows={6}
              className="w-full form-input"
              placeholder="Enter text to share..."
            />
            <div className="mt-1 flex justify-between text-xs text-gray-500">
              <span>
                Characters: {shareText.length}/{characterLimits[platform]}
              </span>
              <span className={remainingCharacters < 0 ? 'text-red-500' : ''}>
                {remainingCharacters < 0 ? 'Exceeds limit by ' : 'Remaining: '}
                {Math.abs(remainingCharacters)}
              </span>
            </div>
          </div>
          
          {/* Processing status */}
          {clipStatus === 'PROCESSING' && (
            <div className="mb-4 p-3 bg-blue-900 bg-opacity-30 border border-blue-700 rounded-md">
              <div className="flex items-center">
                <div className="mr-3">
                  <div className="animate-spin rounded-full h-4 w-4 border-2 border-blue-500 border-t-transparent"></div>
                </div>
                <p className="text-sm text-blue-300">
                  This clip is still being processed. Recognition data and transcription will be available once processing is complete.
                </p>
              </div>
            </div>
          )}
          
          {/* Action buttons */}
          <div className="flex space-x-3">
            <button
              onClick={shareToSocialMedia}
              disabled={remainingCharacters < 0 || isLoading || clipStatus === 'PROCESSING'}
              className="flex-1 bg-blue-600 hover:bg-blue-700 text-white py-2 px-4 rounded disabled:opacity-50"
            >
              Share Now
            </button>
            
            <button
              onClick={createSocialPost}
              disabled={clipStatus === 'PROCESSING'}
              className="flex-1 bg-gray-100 hover:bg-gray-200 text-gray-800 py-2 px-4 rounded disabled:opacity-50"
            >
              Create Post
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SocialMediaShare;
