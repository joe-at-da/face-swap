"use client";

import { useState, useEffect } from "react";

interface VideoSizeResult {
  horizontalSizeBytes: number | null;
  verticalSizeBytes: number | null;
  isLoading: boolean;
  isHorizontalLoading: boolean;
  isVerticalLoading: boolean;
}

const sizeCache = new Map<string, Promise<number | null>>();

function fetchVideoSize(url: string): Promise<number | null> {
  const cached = sizeCache.get(url);
  if (cached) return cached;

  const promise = fetch(`/api/video-size?url=${encodeURIComponent(url)}`)
    .then((res) =>
      res.ok
        ? res.json().then((d: { size_bytes?: number }) => d.size_bytes ?? null)
        : null
    )
    .catch(() => null)
    .then((result) => {
      if (result === null) sizeCache.delete(url);
      return result;
    });

  sizeCache.set(url, promise);
  return promise;
}

export function useVideoSize(
  clipUrl: string | null,
  verticalClipUrl: string | null
): VideoSizeResult {
  const [horizontalSizeBytes, setHorizontalSizeBytes] = useState<number | null>(
    null
  );
  const [verticalSizeBytes, setVerticalSizeBytes] = useState<number | null>(
    null
  );
  const [isHorizontalLoading, setIsHorizontalLoading] = useState(
    Boolean(clipUrl)
  );
  const [isVerticalLoading, setIsVerticalLoading] = useState(
    Boolean(verticalClipUrl)
  );

  useEffect(() => {
    if (!clipUrl && !verticalClipUrl) return;

    setHorizontalSizeBytes(null);
    setVerticalSizeBytes(null);
    setIsHorizontalLoading(Boolean(clipUrl));
    setIsVerticalLoading(Boolean(verticalClipUrl));

    let cancelled = false;

    if (clipUrl) {
      fetchVideoSize(clipUrl).then((size) => {
        if (!cancelled) {
          setHorizontalSizeBytes(size);
          setIsHorizontalLoading(false);
        }
      });
    }

    if (verticalClipUrl) {
      fetchVideoSize(verticalClipUrl).then((size) => {
        if (!cancelled) {
          setVerticalSizeBytes(size);
          setIsVerticalLoading(false);
        }
      });
    }

    return () => {
      cancelled = true;
    };
  }, [clipUrl, verticalClipUrl]);

  const isLoading = isHorizontalLoading || isVerticalLoading;

  return {
    horizontalSizeBytes,
    verticalSizeBytes,
    isLoading,
    isHorizontalLoading,
    isVerticalLoading,
  };
}
