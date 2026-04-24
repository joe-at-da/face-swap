-- Create user-uploads storage bucket for editor image overlays
-- Public reads (needed for Remotion/RunPod rendering), user-folder write isolation via RLS

-- Create the bucket
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
SELECT
  'user-uploads',
  'user-uploads',
  true,
  5242880, -- 5MB
  ARRAY['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp', 'image/svg+xml']
WHERE NOT EXISTS (SELECT 1 FROM storage.buckets WHERE id = 'user-uploads');

-- RLS: Anyone can view (needed for Remotion rendering + export)
CREATE POLICY "Public can view user uploads"
ON storage.objects FOR SELECT
USING (bucket_id = 'user-uploads');

-- RLS: Users can only upload to their own folder ({userId}/...)
CREATE POLICY "Users can upload to own folder"
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (
  bucket_id = 'user-uploads'
  AND auth.uid()::text = (storage.foldername(name))[1]
);

-- RLS: Users can only update their own files
CREATE POLICY "Users can update own uploads"
ON storage.objects FOR UPDATE
TO authenticated
USING (
  bucket_id = 'user-uploads'
  AND auth.uid()::text = (storage.foldername(name))[1]
);

-- RLS: Users can only delete their own files
CREATE POLICY "Users can delete own uploads"
ON storage.objects FOR DELETE
TO authenticated
USING (
  bucket_id = 'user-uploads'
  AND auth.uid()::text = (storage.foldername(name))[1]
);
