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
}

interface SpeakerProfile {
  id: number;
  name: string;
  role?: string;
  party?: string;
  image_url?: string;
}

interface TranscriptionSegment {
  id: number;
  start_time: number;
  end_time: number;
  text: string;
  speaker_id?: string;
}

const SocialMediaShare: React.FC<SocialMediaShareProps> = ({
  clipId,
  clipTitle,
  clipUrl,
  thumbnailUrl,
  duration,
  hasTranscription
}) => {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(false);
  const [transcription, setTranscription] = useState<any>(null);
  const [speakerProfiles, setSpeakerProfiles] = useState<SpeakerProfile[]>([]);
  const [shareText, setShareText] = useState('');
  const [platform, setPlatform] = useState<'twitter' | 'linkedin' | 'facebook'>('twitter');
  const [includeTranscript, setIncludeTranscript] = useState(true);
  const [includeSpeakers, setIncludeSpeakers] = useState(true);
  
  // Character limits for different platforms
  const characterLimits = {
    twitter: 280,
    linkedin: 700,
    facebook: 500
  };
  
  useEffect(() => {
    // Load transcription if available
    if (hasTranscription) {
      fetchTranscription();
    }
    
    // Generate initial share text
    generateShareText();
  }, [clipId, hasTranscription]);
  
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
  
  // Generate share text based on selected options
  const generateShareText = () => {
    let text = `${clipTitle}`;
    
    // Add speaker information if available and selected
    if (includeSpeakers && speakerProfiles.length > 0) {
      const speakerNames = speakerProfiles
        .map(profile => profile.name)
        .join(', ');
      
      text += `\n\nFeaturing: ${speakerNames}`;
    }
    
    // Add transcript excerpt if available and selected
    if (includeTranscript && transcription && transcription.segments && transcription.segments.length > 0) {
      // Get first 1-2 segments depending on length
      const segments = transcription.segments.slice(0, 2);
      const excerptText = segments
        .map((seg: TranscriptionSegment) => seg.text)
        .join(' ');
      
      // Truncate if needed
      const maxExcerptLength = 100;
      const truncatedExcerpt = excerptText.length > maxExcerptLength
        ? excerptText.substring(0, maxExcerptLength) + '...'
        : excerptText;
      
      text += `\n\n"${truncatedExcerpt}"`;
    }
    
    // Add URL
    text += `\n\nWatch the full clip: ${typeof window !== 'undefined' ? window.location.origin : ''}/clips/${clipId}`;
    
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
    }
    
    // Regenerate share text after a short delay
    setTimeout(() => {
      generateShareText();
    }, 100);
  };
  
  // Share to social media
  const shareToSocialMedia = () => {
    let url = '';
    const currentUrl = typeof window !== 'undefined' ? window.location.href : '';
    
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
  };
  
  // Create social media post in the system
  const createSocialPost = () => {
    router.push({
      pathname: '/social/new',
      query: {
        clip_id: clipId,
        content: shareText,
        platform
      }
    });
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
            <option value="linkedin">LinkedIn</option>
            <option value="facebook">Facebook</option>
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
          
          {/* Options */}
          <div className="flex items-center space-x-4">
            <label className="flex items-center">
              <input
                type="checkbox"
                name="includeTranscript"
                checked={includeTranscript}
                onChange={handleCheckboxChange}
                className="h-4 w-4 text-primary focus:ring-primary border-gray-300 rounded"
                disabled={!hasTranscription}
              />
              <span className="ml-2 text-sm text-gray-700">Include transcript excerpt</span>
            </label>
            
            <label className="flex items-center">
              <input
                type="checkbox"
                name="includeSpeakers"
                checked={includeSpeakers}
                onChange={handleCheckboxChange}
                className="h-4 w-4 text-primary focus:ring-primary border-gray-300 rounded"
                disabled={speakerProfiles.length === 0}
              />
              <span className="ml-2 text-sm text-gray-700">Include speaker info</span>
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
          
          {/* Action buttons */}
          <div className="flex space-x-3">
            <button
              onClick={shareToSocialMedia}
              disabled={remainingCharacters < 0 || isLoading}
              className="flex-1 bg-blue-600 hover:bg-blue-700 text-white py-2 px-4 rounded disabled:opacity-50"
            >
              Share Now
            </button>
            
            <button
              onClick={createSocialPost}
              className="flex-1 bg-gray-100 hover:bg-gray-200 text-gray-800 py-2 px-4 rounded"
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
