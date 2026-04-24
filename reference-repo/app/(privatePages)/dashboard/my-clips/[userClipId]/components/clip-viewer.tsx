"use client";

import { useState, useRef } from "react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Play,
  Pause,
  Volume2,
  VolumeX,
  Maximize,
  Smartphone,
  Monitor,
  Video,
  RectangleHorizontal,
  RectangleVertical
} from "lucide-react";
import { cn } from "@/lib/utils";

interface ClipViewerProps {
  clip_url: string | null;
  vertical_clip_url: string | null;
  thumbnail_url: string | null;
  vertical_thumbnail_url: string | null;
  duration: string | null;
  watermark_url: string | null;
  watermark_position: string | null;
  title?: string | null;
  defaultTitle?: string;
  canEdit?: boolean;
  onEditClick?: () => void;
}

export function ClipViewer({
  clip_url,
  vertical_clip_url,
  thumbnail_url,
  vertical_thumbnail_url,
  watermark_url,
  watermark_position,
}: ClipViewerProps) {
  const [currentFormat, setCurrentFormat] = useState<'horizontal' | 'vertical'>(
    clip_url ? 'horizontal' : 'vertical'
  );
  const [isPlaying, setIsPlaying] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [totalDuration, setTotalDuration] = useState(0);
  const [hasPlayedOnce, setHasPlayedOnce] = useState(false);

  const videoRef = useRef<HTMLVideoElement>(null);

  const currentThumbnailUrl = currentFormat === 'horizontal' ? thumbnail_url : vertical_thumbnail_url;

  const handlePlayPause = () => {
    if (!videoRef.current) return;

    if (isPlaying) {
      videoRef.current.pause();
      setIsPlaying(false);
    } else {
      videoRef.current.play();
      setIsPlaying(true);
      setHasPlayedOnce(true);
    }
  };

  const handleVolumeToggle = () => {
    if (!videoRef.current) return;

    videoRef.current.muted = !isMuted;
    setIsMuted(!isMuted);
  };

  const handleTimeUpdate = () => {
    if (!videoRef.current) return;
    setCurrentTime(videoRef.current.currentTime);
  };

  const handleLoadedMetadata = () => {
    if (!videoRef.current) return;
    setTotalDuration(videoRef.current.duration);
  };

  const handleSeek = (time: number) => {
    if (!videoRef.current) return;
    videoRef.current.currentTime = time;
    setCurrentTime(time);
  };

  if (!clip_url && !vertical_clip_url) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center h-64">
          <div className="text-center space-y-2">
            <Video className="h-8 w-8 mx-auto text-muted-foreground" />
            <p className="text-muted-foreground">No video files available</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {/* Premium Format Selector */}
      <Card className="border  py-3 gap-2">
        <CardHeader className=" px-4 py-3 pb-3">
          <div className="flex items-center justify-between gap-4 flex-wrap">
            <h1 className="text-2xl font-bold bg-gradient-to-r from-foreground to-foreground/70 bg-clip-text break-words flex items-center gap-2" style={{ fontFamily: "Inter, sans-serif" }}>
              <span className="bg-slate-200 rounded p-1 font-sans font-bold text-lg">
                <Video className="h-6 w-6" />
              </span>
              Video Player
            </h1>
            {/* Format Buttons */}
            <div className="flex items-center gap-2">
              <Button
                variant={currentFormat === 'horizontal' ? 'default' : 'outline'}
                size="sm"
                disabled={!clip_url}
                onClick={() => setCurrentFormat('horizontal')}
                className="flex items-center gap-2"
              >
                <RectangleHorizontal className="h-4 w-4" />
                <span className="font-semibold">Horizontal</span>
                {!clip_url && <Badge variant="secondary" className="ml-2 text-xs">Unavailable</Badge>}
              </Button>
              <Button
                variant={currentFormat === 'vertical' ? 'default' : 'outline'}
                size="sm"
                disabled={!vertical_clip_url}
                onClick={() => setCurrentFormat('vertical')}
                className="flex items-center gap-2"
              >
                <RectangleVertical className="h-4 w-4" />
                <span className="font-semibold">Vertical</span>
                {!vertical_clip_url && <Badge variant="secondary" className="ml-2 text-xs">Unavailable</Badge>}
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent className="px-4 py-2">
          {currentFormat === 'horizontal' ? (
            <div>
              {clip_url ? (
                <div className="relative rounded overflow-hidden border-1 border-border">
                  <VideoPlayer
                    videoUrl={clip_url}
                    thumbnailUrl={currentThumbnailUrl}
                    aspectRatio="aspect-video"
                    videoRef={videoRef}
                    isPlaying={isPlaying}
                    isMuted={isMuted}
                    currentTime={currentTime}
                    totalDuration={totalDuration}
                    hasPlayedOnce={hasPlayedOnce}
                    watermarkUrl={watermark_url}
                    watermarkPosition={watermark_position}
                    onPlayPause={handlePlayPause}
                    onVolumeToggle={handleVolumeToggle}
                    onTimeUpdate={handleTimeUpdate}
                    onLoadedMetadata={handleLoadedMetadata}
                    onSeek={handleSeek}
                  />
                </div>
              ) : (
                <div className="aspect-video bg-muted rounded-xl flex items-center justify-center border-2 border-dashed">
                  <div className="text-center space-y-3">
                    <div className="p-4 rounded-full bg-muted-foreground/10">
                      <Monitor className="h-10 w-10 mx-auto text-muted-foreground" />
                    </div>
                    <p className="text-muted-foreground font-medium">Horizontal format not available</p>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div>
              {vertical_clip_url ? (
                <div className="flex justify-center">
                  <div className="w-full max-w-sm relative rounded-xl overflow-hidden border-2 border-border shadow-lg">
                    <VideoPlayer
                      videoUrl={vertical_clip_url}
                      thumbnailUrl={vertical_thumbnail_url}
                      aspectRatio="aspect-[9/16]"
                      videoRef={videoRef}
                      isPlaying={isPlaying}
                      isMuted={isMuted}
                      currentTime={currentTime}
                      totalDuration={totalDuration}
                      hasPlayedOnce={hasPlayedOnce}
                      watermarkUrl={watermark_url}
                      watermarkPosition={watermark_position}
                      onPlayPause={handlePlayPause}
                      onVolumeToggle={handleVolumeToggle}
                      onTimeUpdate={handleTimeUpdate}
                      onLoadedMetadata={handleLoadedMetadata}
                      onSeek={handleSeek}
                    />
                  </div>
                </div>
              ) : (
                <div className="flex justify-center">
                  <div className="aspect-[9/16] bg-muted rounded-xl flex items-center justify-center max-w-sm w-full border-2 border-dashed">
                    <div className="text-center space-y-3">
                      <div className="p-4 rounded-full bg-muted-foreground/10">
                        <Smartphone className="h-10 w-10 mx-auto text-muted-foreground" />
                      </div>
                      <p className="text-muted-foreground font-medium">Vertical format not available</p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// Video Player Component
interface VideoPlayerProps {
  videoUrl: string;
  thumbnailUrl: string | null;
  aspectRatio: string;
  videoRef: React.RefObject<HTMLVideoElement | null>;
  isPlaying: boolean;
  isMuted: boolean;
  currentTime: number;
  totalDuration: number;
  hasPlayedOnce: boolean;
  onPlayPause: () => void;
  onVolumeToggle: () => void;
  onTimeUpdate: () => void;
  onLoadedMetadata: () => void;
  onSeek: (time: number) => void;
  watermarkUrl: string | null;
  watermarkPosition: string | null;
}

function VideoPlayer({
  videoUrl,
  thumbnailUrl,
  aspectRatio,
  videoRef,
  isPlaying,
  isMuted,
  currentTime,
  totalDuration,
  hasPlayedOnce,
  onPlayPause,
  onVolumeToggle,
  onTimeUpdate,
  onLoadedMetadata,
  onSeek
}: VideoPlayerProps) {
  const progressPercentage = totalDuration > 0 ? (currentTime / totalDuration) * 100 : 0;

  const formatTime = (seconds: number): string => {
    if (!seconds || !isFinite(seconds) || isNaN(seconds)) {
      return "0:00";
    }
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const handleProgressBarClick = (e: React.MouseEvent<HTMLDivElement>) => {
    const progressBar = e.currentTarget;
    const rect = progressBar.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const percentage = clickX / rect.width;
    const targetTime = percentage * totalDuration;
    onSeek(targetTime);
  };

  return (
    <div className="relative group">
      <div className={cn("relative bg-background rounded-lg overflow-hidden", aspectRatio)}>
        <video
          ref={videoRef}
          src={videoUrl}
          poster={thumbnailUrl || undefined}
          className="w-full h-full object-contain"
          onTimeUpdate={onTimeUpdate}
          onLoadedMetadata={onLoadedMetadata}
          onPlay={() => { }}
          onPause={() => { }}
        />

        {/* Initial Play Button Overlay */}
        {!hasPlayedOnce && !isPlaying && (
          <div
            className="absolute inset-0 z-20 flex items-center justify-center cursor-pointer"
            onClick={onPlayPause}
          >
            <div className="p-4 rounded-full bg-white shadow-2xl hover:bg-white/90 hover:scale-110 transition-all duration-300 pointer-events-none">
              <Play className="h-10 w-10 text-primary fill-current pointer-events-none" />
            </div>
          </div>
        )}

        {/* Video Controls Overlay */}
        <div className="absolute inset-0 z-10 bg-gradient-to-t from-background/80 via-transparent to-transparent opacity-0 group-hover:opacity-100 group-focus-within:opacity-100 transition-opacity pointer-events-none group-hover:pointer-events-auto group-focus-within:pointer-events-auto">
          <div className="absolute bottom-0 left-0 right-0 p-4">
            {/* Progress Bar */}
            <div className="mb-3">
              <div
                className="w-full bg-background/30 rounded-full h-1.5 hover:h-2.5 cursor-pointer transition-all duration-200"
                onClick={handleProgressBarClick}
                role="slider"
                aria-label="Video progress"
                aria-valuenow={currentTime}
                aria-valuemin={0}
                aria-valuemax={totalDuration}
                tabIndex={0}
              >
                <div
                  className="bg-primary h-full rounded-full transition-all duration-200 pointer-events-none"
                  style={{ width: `${progressPercentage}%` }}
                />
              </div>
            </div>

            {/* Controls */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={onPlayPause}
                  aria-label={isPlaying ? "Pause video" : "Play video"}
                  className="text-foreground hover:bg-accent h-11 w-11"
                >
                  {isPlaying ? (
                    <Pause className="h-5 w-5" />
                  ) : (
                    <Play className="h-5 w-5" />
                  )}
                </Button>

                <Button
                  variant="ghost"
                  size="sm"
                  onClick={onVolumeToggle}
                  aria-label={isMuted ? "Unmute video" : "Mute video"}
                  className="text-foreground hover:bg-accent h-11 w-11"
                >
                  {isMuted ? (
                    <VolumeX className="h-5 w-5" />
                  ) : (
                    <Volume2 className="h-5 w-5" />
                  )}
                </Button>

                <span className="text-foreground text-sm font-medium">
                  {formatTime(currentTime)} / {formatTime(totalDuration)}
                </span>
              </div>

              <Button
                variant="ghost"
                size="sm"
                aria-label="Enter fullscreen"
                className="text-foreground hover:bg-accent h-11 w-11"
                onClick={() => {
                  if (videoRef.current) {
                    videoRef.current.requestFullscreen();
                  }
                }}
              >
                <Maximize className="h-5 w-5" />
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}