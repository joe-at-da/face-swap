"use client";

import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import {
  Play,
  Pause,
  Volume2,
  VolumeX,
  SkipBack,
  SkipForward,
  Maximize,
  Minimize,
  Loader2
} from "lucide-react";
import { cn } from "@/lib/utils";
import Image from "next/image";

interface NativeVideoPlayerProps {
  src: string | null;
  poster?: string | null;
  className?: string;
  onError?: () => void;
  onTimeUpdate?: (currentTime: number) => void;
  onDurationLoaded?: (duration: number) => void;
}

export default function NativeVideoPlayer({
  src,
  poster,
  className,
  onError,
  onTimeUpdate,
  onDurationLoaded
}: NativeVideoPlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(1);
  const [isMuted, setIsMuted] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [showControls, setShowControls] = useState(true);
  const [hasError, setHasError] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isSeeking, setIsSeeking] = useState(false);

  const formatTime = (seconds: number) => {
    if (!seconds || !isFinite(seconds)) return "0:00";

    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);

    if (hours > 0) {
      return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${minutes}:${secs.toString().padStart(2, '0')}`;
  };

  const handlePlayPause = () => {
    if (!videoRef.current) return;

    if (isPlaying) {
      videoRef.current.pause();
    } else {
      videoRef.current.play();
    }
  };

  const handleSeek = (value: number[]) => {
    if (!videoRef.current) return;
    setIsSeeking(true);
    videoRef.current.currentTime = value[0];
  };

  const handleVolumeChange = (value: number[]) => {
    if (!videoRef.current) return;
    const newVolume = value[0];
    videoRef.current.volume = newVolume;
    setVolume(newVolume);
    setIsMuted(newVolume === 0);
  };

  const handleMute = () => {
    if (!videoRef.current) return;

    if (isMuted) {
      videoRef.current.volume = volume;
      setIsMuted(false);
    } else {
      videoRef.current.volume = 0;
      setIsMuted(true);
    }
  };

  const handleSkip = (seconds: number) => {
    if (!videoRef.current) return;
    videoRef.current.currentTime = Math.max(0, Math.min(duration, videoRef.current.currentTime + seconds));
  };

  const handleFullscreen = () => {
    if (!videoRef.current) return;

    if (!isFullscreen) {
      if (videoRef.current.requestFullscreen) {
        videoRef.current.requestFullscreen();
      }
    } else {
      if (document.exitFullscreen) {
        document.exitFullscreen();
      }
    }
  };

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const handleLoadedMetadata = () => {
      if (video.duration && isFinite(video.duration)) {
        setDuration(video.duration);
        onDurationLoaded?.(video.duration);
      }
      setIsLoading(false);
    };

    const handleLoadStart = () => {
      setIsLoading(true);
    };

    const handleLoadedData = () => {
      setIsLoading(false);
    };

    const handleWaiting = () => {
      setIsLoading(true);
    };

    const handleCanPlay = () => {
      setIsLoading(false);
    };

    const handleSeeking = () => {
      setIsSeeking(true);
    };

    const handleSeeked = () => {
      setIsSeeking(false);
    };

    // If metadata is already loaded, set the duration immediately
    if (video.readyState >= 1 && video.duration && isFinite(video.duration)) {
      setDuration(video.duration);
      onDurationLoaded?.(video.duration);
    }

    const handleTimeUpdate = () => {
      setCurrentTime(video.currentTime);
      onTimeUpdate?.(video.currentTime);
    };

    const handlePlay = () => {
      setIsPlaying(true);
    };

    const handlePause = () => {
      setIsPlaying(false);
    };

    const handleVolumeChange = () => {
      setVolume(video.volume);
      setIsMuted(video.muted);
    };

    const handleError = () => {
      setHasError(true);
      onError?.();
    };

    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement);
    };

    video.addEventListener('loadstart', handleLoadStart);
    video.addEventListener('loadedmetadata', handleLoadedMetadata);
    video.addEventListener('loadeddata', handleLoadedData);
    video.addEventListener('waiting', handleWaiting);
    video.addEventListener('canplay', handleCanPlay);
    video.addEventListener('seeking', handleSeeking);
    video.addEventListener('seeked', handleSeeked);
    video.addEventListener('timeupdate', handleTimeUpdate);
    video.addEventListener('play', handlePlay);
    video.addEventListener('pause', handlePause);
    video.addEventListener('volumechange', handleVolumeChange);
    video.addEventListener('error', handleError);
    document.addEventListener('fullscreenchange', handleFullscreenChange);

    return () => {
      video.removeEventListener('loadstart', handleLoadStart);
      video.removeEventListener('loadedmetadata', handleLoadedMetadata);
      video.removeEventListener('loadeddata', handleLoadedData);
      video.removeEventListener('waiting', handleWaiting);
      video.removeEventListener('canplay', handleCanPlay);
      video.removeEventListener('seeking', handleSeeking);
      video.removeEventListener('seeked', handleSeeked);
      video.removeEventListener('timeupdate', handleTimeUpdate);
      video.removeEventListener('play', handlePlay);
      video.removeEventListener('pause', handlePause);
      video.removeEventListener('volumechange', handleVolumeChange);
      video.removeEventListener('error', handleError);
      document.removeEventListener('fullscreenchange', handleFullscreenChange);
    };
  }, [onError, onTimeUpdate, onDurationLoaded]);

  if (!src || hasError) {
    return (
      <div className={cn("w-full aspect-video bg-muted flex items-center justify-center rounded-lg", className)}>
        <div className="text-center space-y-2">
          <div className="text-muted-foreground">
            {hasError ? "Failed to load video" : "Video not available"}
          </div>
          {poster && (
            <Image
              src={poster}
              alt="Video thumbnail"
              width={384}
              height={128}
              className="max-w-sm max-h-32 object-cover rounded mx-auto"
            />
          )}
        </div>
      </div>
    );
  }

  return (
    <div
      className={cn("relative w-full bg-black rounded-lg overflow-hidden group", className)}
      onMouseEnter={() => setShowControls(true)}
      onMouseLeave={() => setShowControls(false)}
    >
      <video
        ref={videoRef}
        src={src}
        poster={poster || undefined}
        className="w-full h-full object-contain"
        playsInline
        preload="metadata"
        onClick={handlePlayPause}
      />

      {/* Controls overlay */}
      <div
        className={cn(
          "absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent transition-opacity duration-300",
          showControls ? "opacity-100" : "opacity-0"
        )}
      >
        {/* Bottom controls - positioned at bottom, lower on mobile */}
        <div className="absolute bottom-0 left-0 right-0 pb-2 px-4 pt-2 md:p-4 space-y-0 md:space-y-2 z-10">
          {/* Progress bar */}
          <Slider
            value={[currentTime]}
            max={duration || 100}
            step={0.1}
            onValueChange={handleSeek}
            className="w-full min-h-[22px] md:min-h-[44px] mb-0 md:mb-0 [&_[data-slot=slider-track]]:h-1 [&_[data-slot=slider-track]]:md:h-1.5"
            aria-label="Video progress"
          />

          {/* Control buttons */}
          <div className="flex items-center justify-between text-white -mt-1 md:mt-0">
            <div className="flex items-center space-x-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={handlePlayPause}
                className="text-white hover:bg-white/20 border-0 min-h-[32px] min-w-[32px] md:min-h-[44px] md:min-w-[44px] p-1.5 md:p-2"
                aria-label={isPlaying ? "Pause video" : "Play video"}
              >
                {isPlaying ? <Pause className="h-3.5 w-3.5 md:h-4 md:w-4" /> : <Play className="h-3.5 w-3.5 md:h-4 md:w-4" />}
              </Button>

              <Button
                variant="ghost"
                size="sm"
                onClick={() => handleSkip(-30)}
                className="text-white hover:bg-white/20 border-0 min-h-[32px] min-w-[32px] md:min-h-[44px] md:min-w-[44px] p-1.5 md:p-2"
                aria-label="Rewind 30 seconds"
              >
                <SkipBack className="h-3.5 w-3.5 md:h-4 md:w-4" />
              </Button>

              <Button
                variant="ghost"
                size="sm"
                onClick={() => handleSkip(30)}
                className="text-white hover:bg-white/20 border-0 min-h-[32px] min-w-[32px] md:min-h-[44px] md:min-w-[44px] p-1.5 md:p-2"
                aria-label="Fast forward 30 seconds"
              >
                <SkipForward className="h-3.5 w-3.5 md:h-4 md:w-4" />
              </Button>

              <div className="flex items-center space-x-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleMute}
                  className="text-white hover:bg-white/20 border-0 min-h-[32px] min-w-[32px] md:min-h-[44px] md:min-w-[44px] p-1.5 md:p-2"
                  aria-label={isMuted ? "Unmute video" : "Mute video"}
                >
                  {isMuted ? <VolumeX className="h-3.5 w-3.5 md:h-4 md:w-4" /> : <Volume2 className="h-3.5 w-3.5 md:h-4 md:w-4" />}
                </Button>

                <Slider
                  value={[isMuted ? 0 : volume]}
                  max={1}
                  step={0.01}
                  onValueChange={handleVolumeChange}
                  className="w-20 min-h-[32px] md:min-h-[44px]"
                  aria-label="Volume control"
                />
              </div>
            </div>

            <div className="flex items-center space-x-2">
              <span className="text-sm font-mono">
                {formatTime(currentTime)} / {formatTime(duration)}
              </span>

              <Button
                variant="ghost"
                size="sm"
                onClick={handleFullscreen}
                className="text-white hover:bg-white/20 border-0 min-h-[32px] min-w-[32px] md:min-h-[44px] md:min-w-[44px] p-1.5 md:p-2"
                aria-label={isFullscreen ? "Exit fullscreen" : "Enter fullscreen"}
              >
                {isFullscreen ? <Minimize className="h-3.5 w-3.5 md:h-4 md:w-4" /> : <Maximize className="h-3.5 w-3.5 md:h-4 md:w-4" />}
              </Button>
            </div>
          </div>
        </div>

        {/* Play/Pause overlay - positioned in center, excluding bottom controls area on mobile */}
        <div className="absolute inset-0 md:inset-0 bottom-[140px] md:bottom-0 flex items-center justify-center z-30 pointer-events-none pt-14 md:pt-0">
          {(isLoading || isSeeking) ? (
            <div className="bg-black/40 rounded-full p-4 pointer-events-none">
              <Loader2 className="h-8 w-8 text-white animate-spin" />
            </div>
          ) : (
            <Button
              variant="ghost"
              size="lg"
              onClick={handlePlayPause}
              className="bg-black/40 hover:bg-black/60 text-white border-0 rounded-full min-h-[44px] min-w-[44px] md:min-h-[64px] md:min-w-[64px] p-4 md:p-6 pointer-events-auto"
              aria-label={isPlaying ? "Pause video" : "Play video"}
            >
              {isPlaying ? (
                <Pause className="h-8 w-8 md:h-12 md:w-12" />
              ) : (
                <Play className="h-8 w-8 md:h-12 md:w-12 ml-1" />
              )}
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}