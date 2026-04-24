"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import Image from "next/image";
import { Button } from "@/components/ui/button";
import { Loader2, Check, Trash2 } from "lucide-react";
import type { ReviewStats } from "../page";

interface MPWithPortraits {
  member_id: number;
  display_name: string | null;
  primaryImage: {
    id: string;
    image_url: string;
    fallback_url: string | null;
  } | null;
  hasPrimaryImage: boolean;
  otherImages: Array<{
    id: string;
    image_url: string;
    fallback_url: string | null;
  }>;
}

interface PortraitReviewClientProps {
  mps: MPWithPortraits[];
  stats: ReviewStats;
  completionMessage: string;
}

export function PortraitReviewClient({
  mps,
  stats,
  completionMessage,
}: PortraitReviewClientProps) {
  const [mpIndex, setMpIndex] = useState(0);
  const [imageIndex, setImageIndex] = useState(0);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isValidating, setIsValidating] = useState(false);
  const [isSwitchingMp, setIsSwitchingMp] = useState(false);
  const [deletedIds, setDeletedIds] = useState<Set<string>>(new Set());
  const [validatedIds, setValidatedIds] = useState<Set<string>>(new Set());
  const [prevMpIndex, setPrevMpIndex] = useState<number | null>(null);
  const switchTimerRef = useRef<NodeJS.Timeout | null>(null);
  const [isPrimaryImageLoading, setIsPrimaryImageLoading] = useState(true);
  const [isReviewImageLoading, setIsReviewImageLoading] = useState(true);
  const [cachedPrimaryImageUrl, setCachedPrimaryImageUrl] = useState<
    string | null
  >(null);
  const [usePrimaryFallback, setUsePrimaryFallback] = useState(false);
  const [useReviewFallback, setUseReviewFallback] = useState(false);

  const currentMp = mps[mpIndex];

  // Helper function: Find current image by starting from imageIndex and skipping processed ones
  // imageIndex now indexes into the original currentMp.otherImages array
  const getCurrentImageFromIndex = (
    index: number,
    mp: MPWithPortraits | undefined
  ): { image: { id: string; image_url: string; fallback_url: string | null }; actualIndex: number } | null => {
    if (!mp) return null;
    
    // Start from imageIndex and find first unprocessed image
    for (let i = index; i < mp.otherImages.length; i++) {
      const img = mp.otherImages[i];
      if (!deletedIds.has(img.id) && !validatedIds.has(img.id)) {
        return { image: img, actualIndex: i };
      }
    }
    return null;
  };

  // Helper function: Find next unprocessed image index in original array
  const findNextUnprocessedIndex = (
    startFrom: number,
    mp: MPWithPortraits | undefined
  ): number | null => {
    if (!mp) return null;
    
    for (let i = startFrom + 1; i < mp.otherImages.length; i++) {
      const img = mp.otherImages[i];
      if (!deletedIds.has(img.id) && !validatedIds.has(img.id)) {
        return i;
      }
    }
    return null; // No more images for this MP
  };

  // Get current image using helper function
  // imageIndex now indexes into original array, we find the actual unprocessed image
  const currentImageResult = getCurrentImageFromIndex(imageIndex, currentMp);
  const currentImageInList = currentImageResult?.image || null;
  const actualImageIndex = currentImageResult?.actualIndex ?? imageIndex;

  // Detect MP switch and disable buttons for 2 seconds
  useEffect(() => {
    // Skip on initial load (prevMpIndex is null)
    if (prevMpIndex === null) {
      setPrevMpIndex(mpIndex);
      return;
    }

    // Only trigger if MP actually changed
    if (mpIndex !== prevMpIndex) {
      // Clear any existing timer
      if (switchTimerRef.current) {
        clearTimeout(switchTimerRef.current);
        switchTimerRef.current = null;
      }

      setIsSwitchingMp(true);
      setPrevMpIndex(mpIndex);

      // Set new timer and store in ref
      switchTimerRef.current = setTimeout(() => {
        setIsSwitchingMp(false);
        switchTimerRef.current = null;
      }, 2000);
    }

    // Cleanup on unmount
    return () => {
      if (switchTimerRef.current) {
        clearTimeout(switchTimerRef.current);
        switchTimerRef.current = null;
      }
    };
  }, [mpIndex, prevMpIndex]);

  // Auto-advance when images are deleted or MP changes
  // Now works with original array indices
  useEffect(() => {
    if (currentMp) {
      // Check if there are any unprocessed images left for this MP
      const hasUnprocessedImages = currentMp.otherImages.some(
        (img) => !deletedIds.has(img.id) && !validatedIds.has(img.id)
      );

      // If no images left for current MP, move to next MP
      if (!hasUnprocessedImages) {
        if (mpIndex < mps.length - 1) {
          setMpIndex(mpIndex + 1);
          setImageIndex(0);
        }
      } else {
        // Ensure imageIndex points to an unprocessed image
        // If current index is beyond array bounds or points to processed image, find next unprocessed
        if (imageIndex >= currentMp.otherImages.length) {
          // Index is out of bounds, find first unprocessed image
          const nextIndex = findNextUnprocessedIndex(-1, currentMp);
          if (nextIndex !== null) {
            setImageIndex(nextIndex);
          }
        } else {
          // Check if current index points to a processed image
          const currentImg = currentMp.otherImages[imageIndex];
          if (currentImg && (deletedIds.has(currentImg.id) || validatedIds.has(currentImg.id))) {
            // Current image is processed, find next unprocessed
            const nextIndex = findNextUnprocessedIndex(imageIndex - 1, currentMp);
            if (nextIndex !== null) {
              setImageIndex(nextIndex);
            }
          }
        }
      }
    }
  }, [deletedIds, validatedIds, currentMp, mpIndex, imageIndex, mps.length]);

  // Safety check: Ensure buttons are enabled if timer completed but state didn't update
  useEffect(() => {
    if (isSwitchingMp && switchTimerRef.current === null) {
      // Timer completed but state wasn't updated, fix it
      const safetyTimer = setTimeout(() => {
        setIsSwitchingMp(false);
      }, 100);
      return () => clearTimeout(safetyTimer);
    }
  }, [isSwitchingMp]);

  // Reset primary image loading and fallback state when MP changes
  useEffect(() => {
    const currentPrimaryUrl = currentMp?.primaryImage?.image_url || null;

    // Only reset primary image loading if the URL actually changed
    if (currentPrimaryUrl !== cachedPrimaryImageUrl) {
      setIsPrimaryImageLoading(true);
      setCachedPrimaryImageUrl(currentPrimaryUrl);
      setUsePrimaryFallback(false); // Reset fallback state on MP change

      // Safety timeout: if image doesn't load within 10 seconds, stop showing spinner
      const primaryTimeout = setTimeout(() => {
        setIsPrimaryImageLoading(false);
      }, 10000);

      return () => {
        clearTimeout(primaryTimeout);
      };
    } else if (
      currentPrimaryUrl === cachedPrimaryImageUrl &&
      currentPrimaryUrl !== null
    ) {
      // Image URL is the same (cached), ensure loading state is false
      setIsPrimaryImageLoading(false);
    }
  }, [mpIndex, currentMp?.primaryImage?.image_url, cachedPrimaryImageUrl]);

  // Reset review image loading and fallback state when MP or image changes
  useEffect(() => {
    setIsReviewImageLoading(true);
    setUseReviewFallback(false); // Reset fallback state on image change

    // Safety timeout: if image doesn't load within 10 seconds, stop showing spinner
    const reviewTimeout = setTimeout(() => {
      setIsReviewImageLoading(false);
    }, 10000);

    return () => {
      clearTimeout(reviewTimeout);
    };
  }, [mpIndex, imageIndex]);

  const handleCorrectImage = useCallback(async () => {
    if (!currentImageInList || isValidating) return;

    setIsValidating(true);
    try {
      const response = await fetch(`/api/portraits/${currentImageInList.id}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ is_valid_mp_image: true }),
      });

      // Parse response safely
      let errorMessage = "Failed to validate portrait";
      if (!response.ok) {
        try {
          const errorData = await response.json();
          errorMessage = errorData.error || errorMessage;
        } catch {
          // If JSON parsing fails, use status text
          errorMessage = response.statusText || errorMessage;
        }
        throw new Error(errorMessage);
      }

      // Verify we got a success response
      const result = await response.json();
      if (!result.success) {
        throw new Error(result.error || "Portrait validation failed");
      }

      // Only update state after successful API response
      setValidatedIds((prev) => new Set(prev).add(currentImageInList.id));

      // Find next unprocessed image in original array
      const nextIndex = findNextUnprocessedIndex(actualImageIndex, currentMp);
      if (nextIndex !== null) {
        setImageIndex(nextIndex);
      } else {
        // No more images for this MP, move to next MP
        if (mpIndex < mps.length - 1) {
          setMpIndex(mpIndex + 1);
          setImageIndex(0);
        }
      }
    } catch (error) {
      console.error("Error validating portrait:", error);
      const message =
        error instanceof Error ? error.message : "Failed to validate portrait. Please try again.";
      alert(message);
      // State is NOT updated on error - image remains available for review
    } finally {
      setIsValidating(false);
    }
  }, [currentImageInList, isValidating, actualImageIndex, currentMp, mpIndex, mps.length]);

  const handleDelete = useCallback(async () => {
    if (!currentImageInList || isDeleting) return;

    setIsDeleting(true);
    try {
      const response = await fetch(`/api/portraits/${currentImageInList.id}`, {
        method: "DELETE",
      });

      // Parse response safely
      let errorMessage = "Failed to delete portrait";
      if (!response.ok) {
        try {
          const errorData = await response.json();
          errorMessage = errorData.error || errorMessage;
        } catch {
          // If JSON parsing fails, use status text
          errorMessage = response.statusText || errorMessage;
        }
        throw new Error(errorMessage);
      }

      // Verify we got a success response
      const result = await response.json();
      if (!result.success) {
        throw new Error(result.error || "Portrait deletion failed");
      }

      // Only update state after successful API response
      setDeletedIds((prev) => new Set(prev).add(currentImageInList.id));

      // Find next unprocessed image in original array
      const nextIndex = findNextUnprocessedIndex(actualImageIndex, currentMp);
      if (nextIndex !== null) {
        setImageIndex(nextIndex);
      } else {
        // No more images for this MP, move to next MP
        if (mpIndex < mps.length - 1) {
          setMpIndex(mpIndex + 1);
          setImageIndex(0);
        }
      }
    } catch (error) {
      console.error("Error deleting portrait:", error);
      const message =
        error instanceof Error ? error.message : "Failed to delete portrait. Please try again.";
      alert(message);
      // State is NOT updated on error - image remains available for review
    } finally {
      setIsDeleting(false);
    }
  }, [currentImageInList, isDeleting, actualImageIndex, currentMp, mpIndex, mps.length]);

  // Keyboard shortcuts: Q to mark as correct, P to delete
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      // Don't trigger if user is typing in an input field
      const target = event.target as HTMLElement;
      if (
        target.tagName === "INPUT" ||
        target.tagName === "TEXTAREA" ||
        target.isContentEditable
      ) {
        return;
      }

      // Check if buttons are disabled (same conditions as button disabled props)
      const isDisabled =
        isDeleting ||
        isValidating ||
        isSwitchingMp ||
        isPrimaryImageLoading ||
        isReviewImageLoading ||
        !currentImageInList;

      if (isDisabled) {
        return;
      }

      // Q key: Mark as correct
      if (event.key === "q" || event.key === "Q") {
        event.preventDefault();
        handleCorrectImage();
      }

      // P key: Delete
      if (event.key === "p" || event.key === "P") {
        event.preventDefault();
        handleDelete();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [
    isDeleting,
    isValidating,
    isSwitchingMp,
    isPrimaryImageLoading,
    isReviewImageLoading,
    currentImageInList,
    handleCorrectImage,
    handleDelete,
  ]);

  // Check if we're done (all images are either deleted or validated)
  const allMpsProcessed = mps.every((mp) => {
    const mpAvailableImages = mp.otherImages.filter(
      (img) => !deletedIds.has(img.id) && !validatedIds.has(img.id)
    );
    return mpAvailableImages.length === 0;
  });

  if (allMpsProcessed) {
    return (
      <div className="p-8 text-center space-y-2">
        <p className="text-lg font-semibold text-foreground">
          MP image evaluation has ended.
        </p>
        <p className="text-muted-foreground">{completionMessage}</p>
        <p className="text-sm text-muted-foreground">
          Average images per MP: {stats.averageImagesPerMp} · Lowest count:{" "}
          {stats.minImagesPerMp}
        </p>
      </div>
    );
  }

  if (!currentMp || !currentImageInList) {
    return (
      <div className="p-8 text-center">
        <p className="text-muted-foreground">Loading...</p>
      </div>
    );
  }

  // Counter shows position in original array
  const totalImagesForMp = currentMp.otherImages.length;
  const currentImageNumber = imageIndex + 1;

  return (
    <div className="space-y-6">
      {/* Progress indicator */}
      <div className="flex items-center justify-between text-sm text-muted-foreground">
        <div>
          MP {mpIndex + 1} of {mps.length}:{" "}
          {currentMp.display_name || `Member ${currentMp.member_id}`} (ID:{" "}
          {currentMp.member_id})
        </div>
        <div>
          Image {currentImageNumber} of {totalImagesForMp}
        </div>
      </div>

      {/* Main content: split screen */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Left side: Primary image */}
        <div className="space-y-4">
          <div className="space-y-2">
            <p className="text-sm font-medium text-foreground">
              This is the MP we are evaluating
            </p>
            {currentMp.hasPrimaryImage && currentMp.primaryImage ? (
              <div className="relative aspect-square w-full rounded-lg overflow-hidden border border-border bg-muted">
                {isPrimaryImageLoading && (
                  <div className="absolute inset-0 flex items-center justify-center bg-muted z-10">
                    <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                  </div>
                )}
                <Image
                  key={`${currentMp.member_id}-${usePrimaryFallback ? 'fallback' : 'primary'}`}
                  src={
                    usePrimaryFallback && currentMp.primaryImage.fallback_url
                      ? currentMp.primaryImage.fallback_url
                      : currentMp.primaryImage.image_url
                  }
                  alt={`${currentMp.display_name || "MP"} primary portrait`}
                  fill
                  className="object-cover"
                  sizes="(max-width: 768px) 100vw, 50vw"
                  unoptimized // Disable Next.js image optimization to prevent retries
                  loading="lazy" // Lazy load images to reduce initial load
                  onLoad={() => {
                    setIsPrimaryImageLoading(false);
                  }}
                  onError={() => {
                    console.error(
                      "Failed to load primary image:",
                      currentMp.primaryImage?.image_url
                    );
                    setIsPrimaryImageLoading(false);
                    // Try fallback if available and not already using it
                    if (!usePrimaryFallback && currentMp.primaryImage?.fallback_url) {
                      setUsePrimaryFallback(true);
                      setIsPrimaryImageLoading(true);
                    }
                  }}
                  onLoadingComplete={() => {
                    setIsPrimaryImageLoading(false);
                  }}
                />
              </div>
            ) : (
              <div className="rounded-lg border border-dashed border-border bg-muted/40 p-4 text-sm text-muted-foreground space-y-2">
                <p className="font-semibold text-foreground">
                  {currentMp.display_name || `Member ${currentMp.member_id}`}{" "}
                  (ID: {currentMp.member_id})
                </p>
                <p>
                  We do not have a verified primary portrait for this MP yet.
                </p>
                <p>
                  Please search their name (for example, on Google) to confirm
                  their face and then mark every correct image on the right as
                  “Correct MP Image”.
                </p>
                <p className="text-xs">
                  Delete any photos that clearly do not feature this MP.
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Right side: Current image to review */}
        <div className="space-y-4">
          <div className="space-y-2">
            <div className="space-y-1">
              <p className="text-base font-semibold text-foreground">
                {currentMp.display_name || `Member ${currentMp.member_id}`} (ID:{" "}
                {currentMp.member_id})
              </p>
              <p className="text-sm font-medium text-muted-foreground">
                Image to review
              </p>
            </div>
            <div className="relative aspect-square w-full rounded-lg overflow-hidden border border-border bg-muted">
              {isReviewImageLoading && (
                <div className="absolute inset-0 flex items-center justify-center bg-muted z-10">
                  <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                </div>
              )}
              <Image
                key={`${currentImageInList.id}-${useReviewFallback ? 'fallback' : 'primary'}`}
                src={
                  useReviewFallback && currentImageInList.fallback_url
                    ? currentImageInList.fallback_url
                    : currentImageInList.image_url
                }
                alt={`Portrait ${currentImageNumber} for ${
                  currentMp.display_name || "MP"
                }`}
                fill
                className="object-cover"
                sizes="(max-width: 768px) 100vw, 50vw"
                unoptimized // Disable Next.js image optimization to prevent retries
                loading="lazy" // Lazy load images to reduce initial load
                onLoad={() => {
                  setIsReviewImageLoading(false);
                }}
                onError={() => {
                  // Try fallback if available and not already using it
                  if (!useReviewFallback && currentImageInList.fallback_url) {
                    setUseReviewFallback(true);
                    setIsReviewImageLoading(true);
                  }
                  console.error(
                    "Failed to load review image:",
                    currentImageInList.image_url
                  );
                  setIsReviewImageLoading(false);
                }}
                onLoadingComplete={() => {
                  setIsReviewImageLoading(false);
                }}
              />
            </div>
          </div>

          {/* Action buttons */}
          <div className="space-y-3">
            <Button
              onClick={handleCorrectImage}
              disabled={
                isDeleting ||
                isValidating ||
                isSwitchingMp ||
                isPrimaryImageLoading ||
                isReviewImageLoading
              }
              className="w-full"
              size="lg"
            >
              {isValidating ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Validating...
                </>
              ) : (
                <>
                  <Check className="h-4 w-4" />
                  Correct MP Image
                </>
              )}
            </Button>

            <div className="space-y-2">
              <Button
                onClick={handleDelete}
                disabled={
                  isDeleting ||
                  isValidating ||
                  isSwitchingMp ||
                  isPrimaryImageLoading ||
                  isReviewImageLoading
                }
                variant="destructive"
                className="w-full"
                size="lg"
              >
                {isDeleting ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Deleting...
                  </>
                ) : (
                  <>
                    <Trash2 className="h-4 w-4" />
                    Delete
                  </>
                )}
              </Button>
              <p className="text-xs text-muted-foreground text-center">
                Delete all pictures that have no faces or multiple faces or
                image that have a face that is not of the MP
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
