"use client";

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { User, Upload, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { useLazyImage } from "@/hooks/use-lazy-image";

interface SmartAvatarProps {
  /** User's profile image URL */
  profileImage?: string | null;
  /** User's first name */
  firstName?: string | null;
  /** User's last name */
  lastName?: string | null;
  /** User's email address */
  email?: string | null;
  /** MP portrait URL (if user is an MP) */
  mpPortraitUrl?: string | null;
  /** Whether the user is an MP */
  isMP?: boolean;
  /** Avatar size class */
  className?: string;
  /** Click handler for avatar */
  onClick?: () => void;
  /** Whether avatar is clickable */
  isClickable?: boolean;
  /** Whether avatar is currently loading */
  isLoading?: boolean;
  /** Show upload icon overlay */
  showUploadIcon?: boolean;
  /** Enable lazy loading for images (useful for MP portraits) */
  enableLazyLoading?: boolean;
}

/**
 * Smart Avatar component that intelligently chooses the best avatar source
 * with fallback logic for initials based on available user data.
 * 
 * Priority order:
 * 1. MP portrait (if user is MP)
 * 2. User's uploaded profile image
 * 3. Initials from first + last name
 * 4. Initials from first 2 letters of email
 * 5. User icon fallback
 */
export function SmartAvatar({
  profileImage,
  firstName,
  lastName,
  email,
  mpPortraitUrl,
  isMP = false,
  className,
  onClick,
  isClickable = false,
  isLoading = false,
  showUploadIcon = false,
  enableLazyLoading = false,
}: SmartAvatarProps) {
  
  // Priority 1: MP portrait if user is an MP
  const originalAvatarSrc = isMP && mpPortraitUrl ? mpPortraitUrl : profileImage;
  
  // Use lazy loading if enabled (for MP portraits to avoid rate limits)
  const { imgRef, imageSrc } = useLazyImage({ 
    src: enableLazyLoading ? originalAvatarSrc : null,
    threshold: 0.1 
  });
  
  // Use lazy loaded src if enabled, otherwise use original
  const avatarSrc = enableLazyLoading ? imageSrc : originalAvatarSrc;
  
  // Generate initials with fallback logic
  const getInitials = (): string => {
    // Priority 1: First + Last name initials
    if (firstName && lastName) {
      return `${firstName.charAt(0)}${lastName.charAt(0)}`.toUpperCase();
    }
    
    // Priority 2: First name + first letter of email local part
    if (firstName && email) {
      const emailInitial = email.split('@')[0]?.charAt(0) || '';
      return `${firstName.charAt(0)}${emailInitial}`.toUpperCase();
    }
    
    // Priority 3: First 2 letters of email local part
    if (email) {
      const emailLocal = email.split('@')[0] || '';
      if (emailLocal.length >= 2) {
        return emailLocal.slice(0, 2).toUpperCase();
      } else if (emailLocal.length === 1) {
        return emailLocal.charAt(0).toUpperCase();
      }
    }
    
    // Priority 4: Single letter fallbacks
    if (firstName) {
      return firstName.charAt(0).toUpperCase();
    }
    
    if (lastName) {
      return lastName.charAt(0).toUpperCase();
    }
    
    // No initials available
    return '';
  };

  const initials = getInitials();
  
  const avatarContent = (
    <div ref={enableLazyLoading ? imgRef : undefined}>
      <Avatar className={cn(
        className,
        isClickable && "cursor-pointer hover:opacity-75 transition-opacity",
        isLoading && "opacity-50"
      )}>
        <AvatarImage 
          src={avatarSrc || undefined} 
          alt={
            isMP 
              ? `${firstName || ''} ${lastName || ''}`.trim() || 'MP Portrait'
              : `${firstName || ''} ${lastName || ''}`.trim() || 'Profile picture'
          }
        />
        <AvatarFallback>
          {initials || <User className="h-4 w-4" />}
        </AvatarFallback>
      
      {/* Loading overlay */}
      {isLoading && (
        <div className="absolute inset-0 flex items-center justify-center bg-black/20 rounded-full">
          <Loader2 className="h-4 w-4 animate-spin text-white" />
        </div>
      )}
      
      {/* Upload icon overlay */}
      {showUploadIcon && !isLoading && (
        <div className="absolute -bottom-1 -right-1 p-1 bg-primary text-primary-foreground rounded-full shadow-sm">
          <Upload className="h-3 w-3" />
        </div>
      )}
      </Avatar>
    </div>
  );

  if (isClickable && onClick) {
    return (
      <button
        type="button"
        onClick={onClick}
        disabled={isLoading}
        className={cn(
          "relative focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 rounded-full",
          isLoading && "cursor-not-allowed"
        )}
        aria-label={isLoading ? "Uploading image..." : "Click to change profile picture"}
      >
        {avatarContent}
      </button>
    );
  }

  return <div className="relative">{avatarContent}</div>;
}