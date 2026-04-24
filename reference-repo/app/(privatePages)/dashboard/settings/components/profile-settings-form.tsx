"use client";

import { useState, useRef } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import {
  Camera,
  Loader2
} from "lucide-react";
import { toast } from "sonner";
import { uploadAvatar, deleteAvatar } from "@/lib/upload-avatar";

interface ProfileData {
  id: string;
  email: string;
  first_name?: string;
  last_name?: string;
  avatar_url?: string;
  created_at: string;
}

interface ProfileSettingsFormProps {
  profile: ProfileData;
  onProfileUpdate: (updatedProfile: Partial<ProfileData>) => void;
}

export function ProfileSettingsForm({ profile, onProfileUpdate }: ProfileSettingsFormProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isUploadingAvatar, setIsUploadingAvatar] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [formData, setFormData] = useState({
    first_name: profile.first_name || "",
    last_name: profile.last_name || "",
    avatar_url: profile.avatar_url || "",
  });

  const handleInputChange = (field: string, value: string) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handleSave = async () => {
    setIsSaving(true);

    try {
      const response = await fetch("/api/settings/profile", {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(formData),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Failed to update profile");
      }

      // Update parent component with new data
      onProfileUpdate(formData);

      setIsEditing(false);
      toast.success("Profile updated successfully");
    } catch (error) {
      console.error("Error updating profile:", error);
      toast.error(error instanceof Error ? error.message : "Failed to update profile");
    } finally {
      setIsSaving(false);
    }
  };

  const handleAvatarClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate file type
    const allowedTypes = ['image/jpeg', 'image/png', 'image/webp'];
    if (!allowedTypes.includes(file.type)) {
      toast.error("Please upload a JPEG, PNG, or WebP image");
      return;
    }

    // Validate file size (25MB limit)
    const maxSize = 25 * 1024 * 1024; // 25MB in bytes
    if (file.size > maxSize) {
      toast.error("Image must be smaller than 25MB");
      return;
    }

    setIsUploadingAvatar(true);

    try {
      // Store the old avatar URL for cleanup if upload fails
      const oldAvatarUrl = formData.avatar_url;

      // Delete old avatar if it exists (using improved deleteAvatar function)
      if (oldAvatarUrl) {
        await deleteAvatar(oldAvatarUrl);
      }

      // Upload the new avatar using the utility function
      const uploadResult = await uploadAvatar(file, profile.id);

      if (!uploadResult.success || !uploadResult.publicUrl) {
        throw new Error(uploadResult.error || "Failed to upload avatar");
      }

      // Persist the avatar URL to the database immediately
      const response = await fetch("/api/settings/profile", {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ avatar_url: uploadResult.publicUrl }),
      });

      const data = await response.json();

      if (!response.ok) {
        // If database update fails, try to clean up the uploaded file
        await deleteAvatar(uploadResult.publicUrl);
        throw new Error(data.error || "Failed to save avatar to profile");
      }

      // Update the form data with the new avatar URL
      handleInputChange('avatar_url', uploadResult.publicUrl);

      // Update parent component with new data
      onProfileUpdate({ avatar_url: uploadResult.publicUrl });

      toast.success("Avatar uploaded and saved successfully");
    } catch (error) {
      console.error("Error uploading avatar:", error);
      toast.error(error instanceof Error ? error.message : "Failed to upload avatar");
    } finally {
      setIsUploadingAvatar(false);
      // Reset the file input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const getInitials = () => {
    const firstName = formData.first_name || profile.first_name || "";
    const lastName = formData.last_name || profile.last_name || "";
    return `${firstName.charAt(0)}${lastName.charAt(0)}`.toUpperCase() ||
      profile.email?.charAt(0).toUpperCase() || "?";
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-GB', {
      day: 'numeric',
      month: 'long',
      year: 'numeric'
    });
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-lg font-bold font-sans">
              Profile Information
            </CardTitle>
            <p className="text-base text-muted-foreground font-normal mt-1 pb-4">
              Update your personal and parliamentary information
            </p>
          </div>

          {!isEditing ? (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsEditing(true)}
              className="border-primary"
            >
              Edit Profile
            </Button>
          ) : (
            <Button
              size="sm"
              onClick={handleSave}
              disabled={isSaving}
              className="flex items-center gap-2"
            >
              {isSaving ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                "Save"
              )}
            </Button>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Avatar Section */}
        <div className="flex items-center gap-4">
          <div className="relative">
            <Avatar className="h-16 w-16">
              <AvatarImage
                src={isEditing ? formData.avatar_url : profile.avatar_url}
                alt="Profile picture"
              />
              <AvatarFallback className="text-lg font-medium">
                {getInitials()}
              </AvatarFallback>
            </Avatar>
            {isEditing && (
              <>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  onChange={handleFileChange}
                  className="hidden"
                  aria-label="Upload avatar"
                />
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="absolute -bottom-2 -right-2 h-8 w-8 p-0 rounded-full"
                  title="Change avatar"
                  onClick={handleAvatarClick}
                  disabled={isUploadingAvatar}
                >
                  {isUploadingAvatar ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Camera className="h-4 w-4" />
                  )}
                </Button>
              </>
            )}
          </div>
        </div>

        {/* Account Information */}
        {isEditing ? (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="first_name" className="font-bold">First Name</Label>
                <Input
                  id="first_name"
                  type="text"
                  value={formData.first_name}
                  onChange={(e) => handleInputChange("first_name", e.target.value)}
                  placeholder="Enter first name"
                  className={formData.first_name ? "bg-slate-100" : ""}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="last_name" className="font-bold">Last Name</Label>
                <Input
                  id="last_name"
                  type="text"
                  value={formData.last_name}
                  onChange={(e) => handleInputChange("last_name", e.target.value)}
                  placeholder="Enter last name"
                  className={formData.last_name ? "bg-slate-100" : ""}
                />
              </div>
            </div>
            <div>
              <h4 className="text-sm font-bold py-2">Email Address</h4>
              <div className="text-sm text-foreground">
                {profile.email}
              </div>
              <p className="text-sm text-muted-foreground">
                Parliament email cannot be changed
              </p>
            </div>
          </div>
        ) : (
          <div className="space-y-1">
            <div className="font-medium">
              {(formData.first_name || formData.last_name)
                ? `${formData.first_name} ${formData.last_name}`.trim()
                : (profile.first_name || profile.last_name)
                  ? `${profile.first_name || ''} ${profile.last_name || ''}`.trim()
                  : "Name not set"
              }
            </div>
            <div className="text-sm text-foreground">
              {profile.email}
            </div>
          </div>
        )}
        <div className="space-y-2">
          <h4 className="text-sm font-bold">Account Information</h4>
          <div className="grid gap-2 text-sm">
            <div className="flex justify-between">
              <span className="text-foreground font-normal text-sm font-sans">Account Created:</span>
              <span className="text-primary">{formatDate(profile.created_at)}</span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}