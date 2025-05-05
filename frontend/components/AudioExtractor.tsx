import React, { useState } from 'react';
import axios from 'axios';
import { toast } from 'react-toastify';

interface AudioExtractorProps {
  token: string;
  apiBaseUrl: string;
}

const AudioExtractor: React.FC<AudioExtractorProps> = ({ token, apiBaseUrl }) => {
  const [parliamentTvUrl, setParliamentTvUrl] = useState('');
  const [isExtracting, setIsExtracting] = useState(false);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleExtractAudio = async () => {
    if (!parliamentTvUrl) {
      toast.error('Please enter a Parliament TV URL');
      return;
    }

    if (!parliamentTvUrl.includes('parliamentlive.tv') && !parliamentTvUrl.includes('parliament.tv')) {
      toast.error('Please enter a valid Parliament TV URL');
      return;
    }

    setIsExtracting(true);
    setError(null);
    setAudioUrl(null);

    try {
      const formData = new FormData();
      formData.append('url', parliamentTvUrl);

      console.log('Extracting audio from URL:', parliamentTvUrl);
      
      // Make the request to extract audio
      const response = await axios.post(
        `${apiBaseUrl}/videos/extract-audio-from-url`,
        formData,
        {
          headers: {
            'Authorization': `Bearer ${token}`
          },
          responseType: 'blob',
          timeout: 60000 // 60 second timeout to prevent UI hanging
        }
      );

      // Check if we received valid audio data
      const responseData = response.data as Blob;
      if (responseData.size === 0) {
        throw new Error('Received empty audio file');
      }
      
      // Create a URL for the audio blob
      const audioBlob = new Blob([response.data as BlobPart], { type: 'audio/mpeg' });
      const url = URL.createObjectURL(audioBlob);
      setAudioUrl(url);
      toast.success('Audio extracted successfully');
    } catch (error: any) {
      console.error('Error extracting audio:', error);
      
      // Try to extract a more specific error message if available
      let errorMessage = 'Failed to extract audio from the URL';
      
      if (error.response) {
        // The request was made and the server responded with a status code
        // that falls out of the range of 2xx
        if (error.response.data) {
          try {
            // Try to parse the error response if it's not a blob
            if (error.response.data instanceof Blob) {
              const text = await error.response.data.text();
              try {
                const jsonError = JSON.parse(text);
                errorMessage = jsonError.detail || jsonError.error || jsonError.message || errorMessage;
              } catch (e) {
                // If it's not JSON, use the text directly
                errorMessage = text || errorMessage;
              }
            } else if (typeof error.response.data === 'object') {
              errorMessage = error.response.data.detail || error.response.data.error || error.response.data.message || errorMessage;
            }
          } catch (e) {
            console.error('Error parsing error response:', e);
          }
        }
      } else if (error.request) {
        // The request was made but no response was received
        errorMessage = 'No response received from server. The request may have timed out.';
      } else if (error.message) {
        // Something happened in setting up the request that triggered an Error
        errorMessage = error.message;
      }
      
      setError(errorMessage);
      toast.error(`Failed to extract audio: ${errorMessage}`);
    } finally {
      setIsExtracting(false);
    }
  };

  return (
    <div className="bg-white shadow rounded-lg p-6 mb-6">
      <h2 className="text-xl font-semibold mb-4">Extract Audio from Parliament TV</h2>
      <p className="text-gray-600 mb-4">
        Use this tool to extract and play audio from a Parliament TV URL to verify if it has sound.
      </p>

      <div className="mb-4">
        <label htmlFor="parliamentTvUrl" className="block text-sm font-medium text-gray-700 mb-1">
          Parliament TV URL
        </label>
        <input
          type="text"
          id="parliamentTvUrl"
          value={parliamentTvUrl}
          onChange={(e) => setParliamentTvUrl(e.target.value)}
          placeholder="https://parliamentlive.tv/event/index/..."
          className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
        />
      </div>

      <button
        onClick={handleExtractAudio}
        disabled={isExtracting || !parliamentTvUrl}
        className={`w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white ${
          isExtracting || !parliamentTvUrl ? 'bg-indigo-400 cursor-not-allowed' : 'bg-indigo-600 hover:bg-indigo-700'
        }`}
      >
        {isExtracting ? 'Extracting...' : 'Extract Audio'}
      </button>

      {error && (
        <div className="mt-4 p-3 bg-red-100 text-red-700 rounded-md">
          {error}
        </div>
      )}

      {audioUrl && (
        <div className="mt-4">
          <h3 className="text-lg font-medium mb-2">Audio Preview</h3>
          <audio controls className="w-full" src={audioUrl}>
            Your browser does not support the audio element.
          </audio>
          <p className="mt-2 text-sm text-gray-600">
            If you can hear sound in this audio player, the Parliament TV stream has audio.
          </p>
        </div>
      )}
    </div>
  );
};

export default AudioExtractor;
