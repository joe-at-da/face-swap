"use client";

import { useState, useRef } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { SetupStep1Data, setupStep1Schema } from "@/schemas/authSchema";
import { Button } from "@/components/ui/button";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { SmartAvatar } from "@/components/smart-avatar";
import { Loader2, Crown, Building } from "lucide-react";
import { uploadAvatar, validateImageFile } from "@/lib/upload-avatar";
import { toast } from "sonner";
import { createSupabaseBrowserClient } from "@/supabase/supabaseBrowserClient";
import { ErrorLogger } from "@/lib/errorLogger";

type MP = {
  member_id: number;
  display_name: string;
  party_abbreviation: string;
  party_name?: string;
  constituency_name: string;
  parliament_member_portraits: Array<{
    image_url: string;
    is_primary: boolean;
  }>;
};

interface MpProfileSetupStepProps {
  onNext: (data: SetupStep1Data) => void;
  initialData?: Partial<SetupStep1Data>;
  isLoading?: boolean;
  mpRecord?: MP | null;
}

export function MpProfileSetupStep({ onNext, initialData, isLoading, mpRecord }: MpProfileSetupStepProps) {
  const [imagePreview, setImagePreview] = useState<string | null>(
    initialData?.profileImage as string || null
  );
  const [uploadingImage, setUploadingImage] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  const form = useForm<SetupStep1Data>({
    resolver: zodResolver(setupStep1Schema),
    defaultValues: {
      firstName: initialData?.firstName || "",
      lastName: initialData?.lastName || "",
      profileImage: initialData?.profileImage,
    },
  });

  const handleImageChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Clear previous errors
    setUploadError(null);

    // Validate file
    const validation = validateImageFile(file);
    if (!validation.valid) {
      setUploadError(validation.error || "Invalid file");
      toast.error(validation.error || "Invalid file");
      return;
    }

    // Show preview immediately
    const reader = new FileReader();
    reader.onload = (e) => {
      const result = e.target?.result as string;
      setImagePreview(result);
    };
    reader.readAsDataURL(file);

    // Upload to Supabase
    setUploadingImage(true);
    let userId: string | undefined;
    try {
      const supabase = createSupabaseBrowserClient();
      const { data: { user } } = await supabase.auth.getUser();

      if (!user) {
        throw new Error("User not authenticated");
      }

      userId = user.id;

      const uploadResult = await uploadAvatar(file, user.id);

      if (!uploadResult.success) {
        throw new Error(uploadResult.error || "Upload failed");
      }

      // Save the public URL to the form
      form.setValue("profileImage", uploadResult.publicUrl);
      toast.success("Profile picture uploaded successfully!");
    } catch (error) {
      console.error("Image upload error:", error);
      const errorMessage = error instanceof Error ? error.message : "Failed to upload image";

      // Log error to Glitchtip with proper context
      ErrorLogger.logClientError(
        error,
        'MpProfileSetupStep',
        userId,
        '/mp-setup',
        {
          fileName: file.name,
          fileSize: file.size,
          fileType: file.type,
        }
      );

      setUploadError(errorMessage);
      toast.error(errorMessage);
      // Reset preview on error
      setImagePreview(initialData?.profileImage as string || null);
    } finally {
      setUploadingImage(false);
    }
  };

  const handleAvatarClick = () => {
    if (!uploadingImage) {
      fileInputRef.current?.click();
    }
  };

  const onSubmit = (data: SetupStep1Data) => {
    onNext(data);
  };

  return (
    <Card className="w-full max-w-2xl mx-auto">
      <CardHeader className="text-center">
        <div className="flex justify-center mb-2">
          <Crown className="h-8 w-8 text-primary" />
        </div>
        <CardTitle className="text-2xl font-semibold">MP Profile Setup</CardTitle>
        <CardDescription>
          Set up your parliamentary profile information
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
            {/* Profile Image Upload */}
            <div className="flex flex-col items-center space-y-4">
              <div className="relative">
                <SmartAvatar
                  profileImage={imagePreview}
                  mpPortraitUrl={mpRecord?.parliament_member_portraits?.[0]?.image_url}
                  firstName={form.watch("firstName")}
                  lastName={form.watch("lastName")}
                  isMP={true}
                  className="h-24 w-24 text-lg"
                  onClick={handleAvatarClick}
                  isClickable={!uploadingImage}
                  isLoading={uploadingImage}
                  showUploadIcon={!uploadingImage}
                  enableLazyLoading={false} // Don't lazy load for profile setup
                />
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  onChange={handleImageChange}
                  className="sr-only"
                  disabled={uploadingImage}
                />
              </div>
              <p className="text-sm text-muted-foreground text-center">
                {uploadingImage ? "Uploading image..." : "Click avatar to upload a profile picture (optional)"}<br />
                <span className="text-xs">JPEG, PNG, or WebP • Max 25MB</span>
              </p>
              {uploadError && (
                <p className="text-sm text-destructive text-center" role="alert" aria-live="polite">
                  {uploadError}
                </p>
              )}
              {form.formState.errors.profileImage?.message && (
                <FormMessage 
                  className="text-center"
                  role="alert" 
                  aria-live="polite"
                >
                  {String(form.formState.errors.profileImage.message)}
                </FormMessage>
              )}
            </div>

            {/* MP Information Display */}
            {mpRecord && (
              <div className="p-4 border border-primary/20 bg-primary/5 rounded-lg space-y-3">
                <div className="flex items-center space-x-2">
                  <Building className="h-4 w-4 text-primary" />
                  <span className="text-sm font-medium text-primary">Parliamentary Information</span>
                </div>
                <div className="grid gap-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Name:</span>
                    <span className="font-medium">{mpRecord.display_name}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Constituency:</span>
                    <span className="font-medium">{mpRecord.constituency_name}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-muted-foreground">Party:</span>
                    <div className="flex items-center space-x-2">
                      <Badge variant="outline" className="text-xs">
                        {mpRecord.party_abbreviation}
                      </Badge>
                      {mpRecord.party_name && (
                        <span className="text-xs text-muted-foreground">{mpRecord.party_name}</span>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Name Fields */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <FormField
                control={form.control}
                name="firstName"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>First Name</FormLabel>
                    <FormControl>
                      <Input 
                        placeholder="Enter your first name" 
                        {...field}
                        disabled={isLoading || uploadingImage}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="lastName"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Last Name</FormLabel>
                    <FormControl>
                      <Input 
                        placeholder="Enter your last name" 
                        {...field}
                        disabled={isLoading || uploadingImage}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            {/* Submit Button */}
            <div className="pt-4">
              <Button 
                type="submit" 
                className="w-full" 
                size="lg"
                disabled={isLoading || uploadingImage}
              >
                {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Continue
              </Button>
            </div>
          </form>
        </Form>
      </CardContent>
    </Card>
  );
}