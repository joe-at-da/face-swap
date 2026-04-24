"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Progress } from "@/components/ui/progress";
import { CheckCircle, Users, Loader2, Upload, X } from "lucide-react";
import { handleError } from "@/lib/getErrorMessage";
import { toast } from "sonner";
import Image from "next/image";
import { createSupabaseBrowserClient } from "@/supabase/supabaseBrowserClient";

interface TeamMemberSetupWizardProps {
  initialUserData?: {
    firstName: string;
    lastName: string;
    profileImage: string | null;
  };
  teamInfo: {
    teamId: string;
    teamName: string;
    role: string;
  };
}

export function TeamMemberSetupWizard({ initialUserData, teamInfo }: TeamMemberSetupWizardProps) {
  const router = useRouter();
  const supabase = createSupabaseBrowserClient();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form state
  const [firstName, setFirstName] = useState(initialUserData?.firstName || "");
  const [lastName, setLastName] = useState(initialUserData?.lastName || "");
  const [profileImage, setProfileImage] = useState<string | null>(initialUserData?.profileImage || null);
  const [uploadingImage, setUploadingImage] = useState(false);

  const handleImageUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Validate file type - allow JPEG, PNG, WebP (matching bucket configuration)
    const validTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp'];
    if (!validTypes.includes(file.type)) {
      toast.error("Please upload a JPEG, PNG, or WebP image");
      return;
    }

    // Validate file size (max 25MB - matching bucket configuration)
    if (file.size > 25 * 1024 * 1024) {
      toast.error("Image size should be less than 25MB");
      return;
    }

    setUploadingImage(true);
    let userId: string | undefined;
    try {
      // Get current user
      const { data: { user } } = await supabase.auth.getUser();
      if (!user) throw new Error("Not authenticated");

      userId = user.id;

      // Upload to Supabase Storage using the same pattern as profile-setup-step
      const fileExt = file.name.split('.').pop()?.toLowerCase() || 'jpg';
      const fileName = `${Date.now()}.${fileExt}`;
      const filePath = `${user.id}/${fileName}`;

      const { error: uploadError } = await supabase.storage
        .from('user_avatars')
        .upload(filePath, file, {
          cacheControl: '3600',
          upsert: true,
        });

      if (uploadError) throw uploadError;

      // Get public URL
      const { data: { publicUrl } } = supabase.storage
        .from('user_avatars')
        .getPublicUrl(filePath);

      setProfileImage(publicUrl);
      toast.success("Profile image uploaded successfully");
    } catch (err) {
      toast.error(handleError(err, {
        component: 'TeamMemberSetupWizard',
        action: 'image-upload',
        userId,
        route: '/team-setup',
      }));
    } finally {
      setUploadingImage(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!firstName || !lastName) {
      setError("Please fill in all required fields");
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      // Save profile information
      const response = await fetch("/api/setup/profile", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          firstName,
          lastName,
          profileImage,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || "Failed to save profile");
      }

      // Mark setup as complete
      const completeResponse = await fetch("/api/setup/complete", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
      });

      if (!completeResponse.ok) {
        const errorData = await completeResponse.json();
        throw new Error(errorData.error || "Failed to complete setup");
      }

      toast.success("Setup completed successfully! Welcome to the team!");

      // Redirect to team dashboard for team members
      router.push(`/dashboard/teams/${teamInfo.teamId}`);
      router.refresh();
    } catch (err) {
      setError(handleError(err));
      toast.error(handleError(err));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="w-full max-w-2xl mx-auto space-y-8">
      <Progress value={100} className="h-2" />

      <Card className="p-8">
        <div className="space-y-6">
          <div className="text-center space-y-2">
            <div className="flex justify-center mb-4">
              <div className="rounded-full bg-primary/10 p-3">
                <Users className="h-6 w-6 text-primary" />
              </div>
            </div>
            <h3 className="text-2xl font-semibold">Complete Your Profile</h3>
            <p className="text-muted-foreground">
              Set up your profile to get started with your team
            </p>
            <div className="flex items-center justify-center gap-2 mt-3">
              <Badge variant="secondary" className="text-sm">
                {teamInfo.teamName}
              </Badge>
              <Badge variant="outline" className="text-sm">
                {teamInfo.role === "administrator" ? "Administrator" : "Team Member"}
              </Badge>
            </div>
          </div>

          {error && (
            <Alert variant="destructive">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="firstName">
                  First Name <span className="text-destructive">*</span>
                </Label>
                <Input
                  id="firstName"
                  placeholder="John"
                  value={firstName}
                  onChange={(e) => setFirstName(e.target.value)}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="lastName">
                  Last Name <span className="text-destructive">*</span>
                </Label>
                <Input
                  id="lastName"
                  placeholder="Doe"
                  value={lastName}
                  onChange={(e) => setLastName(e.target.value)}
                  required
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="profileImage">Profile Image</Label>
              <div className="flex items-center gap-4">
                {profileImage ? (
                  <div className="relative">
                    <Image
                      src={profileImage}
                      alt="Profile"
                      width={80}
                      height={80}
                      className="rounded-lg object-cover w-20 h-20"
                    />
                    <button
                      type="button"
                      onClick={() => setProfileImage(null)}
                      className="absolute -top-2 -right-2 bg-destructive text-destructive-foreground rounded-full p-1"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </div>
                ) : (
                  <div className="w-20 h-20 rounded-lg bg-muted flex items-center justify-center">
                    {uploadingImage ? (
                      <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                    ) : (
                      <Upload className="h-6 w-6 text-muted-foreground" />
                    )}
                  </div>
                )}
                <div>
                  <Input
                    id="profileImage"
                    type="file"
                    accept="image/*"
                    onChange={handleImageUpload}
                    disabled={uploadingImage}
                    className="hidden"
                  />
                  <Label
                    htmlFor="profileImage"
                    className="cursor-pointer inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 border border-input bg-background hover:bg-accent hover:text-accent-foreground h-10 px-4 py-2"
                  >
                    {uploadingImage ? "Uploading..." : "Choose Image"}
                  </Label>
                  <p className="text-xs text-muted-foreground mt-1">
                    PNG, JPG up to 5MB
                  </p>
                </div>
              </div>
            </div>

            {/* Benefits Section */}
            <Alert className="border-primary/20 bg-primary/5">
              <CheckCircle className="h-4 w-4 text-primary" />
              <AlertDescription className="text-sm">
                As a team member, you&apos;ll have access to:
                <ul className="mt-2 space-y-1 list-disc list-inside">
                  <li>Create and edit video clips from parliament sessions</li>
                  <li>Search parliament footage by topic and context</li>
                  <li>Collaborate with your team on content creation</li>
                  <li>Schedule and share clips on social media</li>
                </ul>
              </AlertDescription>
            </Alert>

            <Button
              type="submit"
              className="w-full"
              size="lg"
              disabled={isLoading || !firstName || !lastName}
            >
              {isLoading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Completing Setup...
                </>
              ) : (
                <>
                  <CheckCircle className="mr-2 h-4 w-4" />
                  Complete Setup & Join Team
                </>
              )}
            </Button>
          </form>
        </div>
      </Card>
    </div>
  );
}