"use client";

import { useCallback, useState, useRef } from "react";
import { observer } from "@legendapp/state/react";
import { Label } from "@/components/ui/label";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { Upload, Loader2, ImageIcon, Plus } from "lucide-react";
import Image from "next/image";
import { addImageItem, editor$, selectItem } from "@/stores/editorStore";
import { player$ } from "@/stores/remotionPlayerStore";
import { createSupabaseBrowserClient } from "@/supabase/supabaseBrowserClient";
import { toast } from "sonner";

const PRELOADED_IMAGES = [
  {
    id: "libdem-black-no-strapline",
    url: "https://thempai.lon1.cdn.digitaloceanspaces.com/defaultwatermarks/LibDemlogo_black_EPS_NO_strapline.png",
    label: "Black Logo",
    bgClass: "bg-white",
  },
  {
    id: "libdem-black-strapline",
    url: "https://thempai.lon1.cdn.digitaloceanspaces.com/defaultwatermarks/LibDemlogo_black_EPS_strapline.png",
    label: "Black Logo + Text",
    bgClass: "bg-white",
  },
  {
    id: "libdem-white-no-strapline",
    url: "https://thempai.lon1.cdn.digitaloceanspaces.com/defaultwatermarks/LibDemlogo_white_EPS_NO_strapline.png",
    label: "White Logo",
    bgClass: "bg-zinc-800",
  },
  {
    id: "libdem-white-strapline",
    url: "https://thempai.lon1.cdn.digitaloceanspaces.com/defaultwatermarks/LibDemlogo_white_EPS_strapline.png",
    label: "White Logo + Text",
    bgClass: "bg-zinc-800",
  },
];

function ImagesTabInner() {
  const [uploading, setUploading] = useState(false);
  const [uploadedImages, setUploadedImages] = useState<
    Array<{ id: string; url: string; name: string }>
  >([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleInsertImage = useCallback((src: string) => {
    const currentFrame = player$.currentFrame.peek();
    const item = addImageItem({
      src,
      insertAtFrame: currentFrame,
    });
    selectItem(item.id);
  }, []);

  const handleUpload = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (!file) return;

      if (!file.type.startsWith("image/")) {
        toast.error("Please select an image file");
        return;
      }
      if (file.size > 5 * 1024 * 1024) {
        toast.error("Image must be under 5MB");
        return;
      }

      setUploading(true);
      try {
        const supabase = createSupabaseBrowserClient();
        const {
          data: { user },
        } = await supabase.auth.getUser();
        if (!user) {
          toast.error("Not authenticated");
          return;
        }
        const fileName = `${user.id}/${Date.now()}-${file.name}`;
        const { error } = await supabase.storage
          .from("user-uploads")
          .upload(fileName, file);

        if (error) throw error;

        const {
          data: { publicUrl },
        } = supabase.storage.from("user-uploads").getPublicUrl(fileName);

        // Add to uploaded images list
        setUploadedImages((prev) => [
          { id: `upload-${Date.now()}`, url: publicUrl, name: file.name },
          ...prev,
        ]);

        // Insert immediately at playhead
        const currentFrame = player$.currentFrame.peek();
        const item = addImageItem({
          src: publicUrl,
          insertAtFrame: currentFrame,
        });
        selectItem(item.id);

        toast.success("Image uploaded and added to timeline");
      } catch {
        toast.error("Failed to upload image");
      } finally {
        setUploading(false);
        if (fileInputRef.current) fileInputRef.current.value = "";
      }
    },
    []
  );

  // Count images on timeline
  const tracks = editor$.tracks.get();
  const imageCount = tracks
    .flatMap((t) => t.items)
    .filter((i) => i.type === "image").length;

  return (
    <ScrollArea className="h-full">
      <div className="p-3 space-y-4">
        {/* Preloaded images */}
        <div className="space-y-2">
          <Label className="text-xs font-medium">Preloaded Images</Label>
          <div className="grid grid-cols-3 gap-2">
            {PRELOADED_IMAGES.map((img) => (
              <button
                key={img.id}
                onClick={() => handleInsertImage(img.url)}
                className="group rounded-md border border-border hover:border-primary/50 transition-colors overflow-hidden"
              >
                <div
                  className={`relative h-14 flex items-center justify-center ${img.bgClass} rounded-t-md`}
                >
                  <Image
                    src={img.url}
                    alt={img.label}
                    width={48}
                    height={48}
                    className="object-contain max-h-10"
                  />
                  <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity bg-black/30">
                    <Plus className="h-4 w-4 text-white" />
                  </div>
                </div>
                <div className="px-1.5 py-1 text-[10px] text-muted-foreground truncate text-center">
                  {img.label}
                </div>
              </button>
            ))}
          </div>
        </div>

        <Separator />

        {/* Upload section */}
        <div className="space-y-2">
          <Label className="text-xs font-medium">Custom Image</Label>
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
            className="w-full rounded-lg border-2 border-dashed border-border hover:border-primary/50 p-4 flex flex-col items-center gap-1.5 transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {uploading ? (
              <Loader2 className="h-5 w-5 text-muted-foreground animate-spin" />
            ) : (
              <Upload className="h-5 w-5 text-muted-foreground" />
            )}
            <span className="text-xs text-muted-foreground">
              {uploading ? "Uploading..." : "Upload image"}
            </span>
            <span className="text-[10px] text-muted-foreground/60">
              PNG, SVG, or JPEG, max 5MB
            </span>
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            onChange={handleUpload}
            className="hidden"
          />
        </div>

        {/* Uploaded images */}
        {uploadedImages.length > 0 && (
          <>
            <Separator />
            <div className="space-y-2">
              <Label className="text-xs font-medium">My Uploads</Label>
              <div className="grid grid-cols-3 gap-2">
                {uploadedImages.map((img) => (
                  <button
                    key={img.id}
                    onClick={() => handleInsertImage(img.url)}
                    className="group rounded-md border border-border hover:border-primary/50 transition-colors overflow-hidden"
                  >
                    <div className="relative h-14 flex items-center justify-center bg-muted rounded-t-md">
                      <Image
                        src={img.url}
                        alt={img.name}
                        width={48}
                        height={48}
                        className="object-contain max-h-10"
                      />
                      <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity bg-black/30">
                        <Plus className="h-4 w-4 text-white" />
                      </div>
                    </div>
                    <div className="px-1.5 py-1 text-[10px] text-muted-foreground truncate text-center">
                      {img.name}
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </>
        )}

        {/* Timeline info */}
        {imageCount > 0 && (
          <>
            <Separator />
            <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground">
              <ImageIcon className="h-3 w-3" />
              <span>
                {imageCount} image{imageCount !== 1 ? "s" : ""} on timeline
              </span>
            </div>
          </>
        )}
      </div>
    </ScrollArea>
  );
}

export const ImagesTab = observer(ImagesTabInner);
