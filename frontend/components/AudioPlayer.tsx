import React, { useState, useRef } from 'react';

interface AudioPlayerProps {
  audioUrl: string;
  title?: string;
}

const AudioPlayer: React.FC<AudioPlayerProps> = ({ audioUrl, title }) => {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);

  const handlePlay = () => {
    setIsPlaying(true);
  };

  const handlePause = () => {
    setIsPlaying(false);
  };

  const handleError = (e: React.SyntheticEvent<HTMLAudioElement, Event>) => {
    console.error('Audio playback error:', e);
    setError('Failed to load audio. The audio file may not be available yet or there might be an issue with the server.');
  };

  return (
    <div className="bg-white rounded-lg shadow-sm p-4 mb-4">
      <div className="flex flex-col">
        {title && <h3 className="text-lg font-medium mb-2">{title}</h3>}
        
        <audio 
          ref={audioRef}
          className="w-full" 
          controls
          src={audioUrl}
          onPlay={handlePlay}
          onPause={handlePause}
          onError={handleError}
        >
          Your browser does not support the audio element.
        </audio>
        
        {error && (
          <div className="mt-2 text-red-500 text-sm">{error}</div>
        )}
        
        <div className="mt-2 text-xs text-gray-500">
          {isPlaying ? 'Now playing' : 'Paused'} - {audioUrl.split('/').pop()}
        </div>
      </div>
    </div>
  );
};

export default AudioPlayer;
