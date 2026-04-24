"use client";

import { useState, useEffect, useRef } from "react";

interface UseLazyImageProps {
  src?: string | null;
  threshold?: number;
}

export function useLazyImage({ src, threshold = 0.1 }: UseLazyImageProps) {
  const [imageSrc, setImageSrc] = useState<string | null>(null);
  const [isLoaded, setIsLoaded] = useState(false);
  const [isInView, setIsInView] = useState(false);
  const imgRef = useRef<HTMLImageElement>(null);

  useEffect(() => {
    if (!src) return;

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setIsInView(true);
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold }
    );

    const currentRef = imgRef.current;
    if (currentRef) {
      observer.observe(currentRef);
    }

    return () => {
      if (currentRef) {
        observer.unobserve(currentRef);
      }
    };
  }, [src, threshold]);

  useEffect(() => {
    if (isInView && src && !imageSrc) {
      setImageSrc(src);
    }
  }, [isInView, src, imageSrc]);

  const handleImageLoad = () => {
    setIsLoaded(true);
  };

  const handleImageError = () => {
    setImageSrc(null);
    setIsLoaded(false);
  };

  return {
    imgRef,
    imageSrc,
    isLoaded,
    isInView,
    handleImageLoad,
    handleImageError,
  };
}