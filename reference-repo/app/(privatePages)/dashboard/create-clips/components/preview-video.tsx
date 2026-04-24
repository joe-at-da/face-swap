"use client";

import { useState, useRef, useEffect } from "react";
import { Play, Pause } from "lucide-react";
import { cn } from "@/lib/utils";
import Image from "next/image";

interface PreviewVideoProps {
  src: string | null;
  poster?: string | null;
  className?: string;
  onClick?: () => void;
  muted?: boolean;
  onDurationLoaded?: (duration: number) => void;
}

export default function PreviewVideo({
  src,
  poster,
  className,
  onClick,
  muted = true,
  onDurationLoaded
}: PreviewVideoProps) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [hasError, setHasError] = useState(false);
  const [isHovered, setIsHovered] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    if (videoRef.current) {
      const video = videoRef.current;

      const handlePlay = () => setIsPlaying(true);
      const handlePause = () => setIsPlaying(false);
      const handleError = () => setHasError(true);
      const handleLoadedMetadata = () => {
        if (video.duration && isFinite(video.duration)) {
          onDurationLoaded?.(video.duration);
        }
      };

      video.addEventListener('play', handlePlay);
      video.addEventListener('pause', handlePause);
      video.addEventListener('error', handleError);
      video.addEventListener('loadedmetadata', handleLoadedMetadata);

      // If metadata is already loaded, call the callback immediately
      if (video.readyState >= 1 && video.duration && isFinite(video.duration)) {
        onDurationLoaded?.(video.duration);
      }

      return () => {
        video.removeEventListener('play', handlePlay);
        video.removeEventListener('pause', handlePause);
        video.removeEventListener('error', handleError);
        video.removeEventListener('loadedmetadata', handleLoadedMetadata);
      };
    }
  }, [onDurationLoaded]);

  const handleMouseEnter = () => {
    setIsHovered(true);
    if (videoRef.current && !hasError && src) {
      videoRef.current.play().catch(() => {
        setHasError(true);
      });
    }
  };

  const handleMouseLeave = () => {
    setIsHovered(false);
    if (videoRef.current && !hasError) {
      videoRef.current.pause();
      videoRef.current.currentTime = 0;
    }
  };

  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    onClick?.();
  };

  if (!src || hasError) {
    return (
      <div 
        className={cn(
          "relative w-full h-full bg-gradient-to-br from-muted to-muted-foreground/20 flex items-center justify-center cursor-pointer",
          className
        )}
        onClick={handleClick}
      >
        {poster ? (
          <Image 
            src={poster} 
            alt="Video thumbnail"
            fill
            sizes="(max-width: 768px) 100vw, (max-width: 1024px) 50vw, 33vw"
            className="object-cover"
          />
        ) : (
          <div className="text-muted-foreground text-center">
            <div className="w-12 h-12 mx-auto mb-2 rounded-full bg-white/90 flex items-center justify-center">
              <Play className="h-6 w-6 text-foreground fill-foreground" />
            </div>
            <p className="text-base md:text-sm">Video unavailable</p>
          </div>
        )}
        
        {/* Play overlay */}
        <div className="absolute inset-0 bg-black/20 hover:bg-black/30 transition-colors flex items-center justify-center">
          <div className="bg-white/90 hover:bg-white rounded-full min-h-[44px] min-w-[44px] flex items-center justify-center transition-colors">
            <Play className="h-6 w-6 text-foreground fill-foreground" />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div 
      className={cn("relative w-full h-full cursor-pointer", className)}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      onClick={handleClick}
    >
      <video
        ref={videoRef}
        src={src}
        poster={poster || undefined}
        muted={muted}
        playsInline
        preload="metadata"
        className="w-full h-full object-cover"
        loop
      />
      
      {/* Play overlay - shows when not hovered or when paused */}
      <div 
        className={cn(
          "absolute inset-0 bg-black/20 transition-all duration-200 flex items-center justify-center",
          isHovered && isPlaying ? "opacity-0" : "opacity-100 hover:bg-black/30"
        )}
      >
        <div className="bg-white/90 hover:bg-white rounded-full min-h-[44px] min-w-[44px] flex items-center justify-center transition-colors">
          {isPlaying ? (
            <Pause className="h-6 w-6 text-foreground" />
          ) : (
            <Play className="h-6 w-6 text-foreground fill-foreground" />
          )}
        </div>
      </div>
    </div>
  );
}