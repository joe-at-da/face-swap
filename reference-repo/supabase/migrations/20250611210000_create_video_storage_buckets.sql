-- Create Video Storage Buckets Migration
-- Migration to create storage buckets for video content:
-- 1. full_videos: Private bucket for original/source video files
-- 2. clips: Public bucket for processed video clips



-- Create full_videos bucket (private, no restrictions)
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
SELECT 
  'full_videos',
  'full_videos',
  false, -- Private bucket
  NULL,  -- No file size limit (allow any size)
  NULL   -- No MIME type restrictions (allow any video format)
WHERE NOT EXISTS (
  SELECT 1 FROM storage.buckets WHERE id = 'full_videos'
);

-- Create clips bucket (public, no restrictions)
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
SELECT 
  'clips',
  'clips',
  true,  -- Public bucket
  NULL,  -- No file size limit (allow any size)
  NULL   -- No MIME type restrictions (allow any video format)
WHERE NOT EXISTS (
  SELECT 1 FROM storage.buckets WHERE id = 'clips'
);

-- RLS Policies for full_videos bucket (private)
-- Only authenticated users can view their own videos in full_videos
CREATE POLICY "Users can view their own full videos" 
ON storage.objects FOR SELECT
USING (
  bucket_id = 'full_videos' 
  AND auth.uid()::text = (storage.foldername(name))[1]
);

-- Only authenticated users can upload to full_videos (in their own folder)
CREATE POLICY "Users can upload their own full videos" 
ON storage.objects FOR INSERT
WITH CHECK (
  bucket_id = 'full_videos'
  AND auth.uid()::text = (storage.foldername(name))[1]
);

-- Only authenticated users can update their own videos in full_videos
CREATE POLICY "Users can update their own full videos" 
ON storage.objects FOR UPDATE
USING (
  bucket_id = 'full_videos'
  AND auth.uid()::text = (storage.foldername(name))[1]
);

-- Only authenticated users can delete their own videos in full_videos
CREATE POLICY "Users can delete their own full videos" 
ON storage.objects FOR DELETE
USING (
  bucket_id = 'full_videos'
  AND auth.uid()::text = (storage.foldername(name))[1]
);

-- RLS Policies for clips bucket (public viewing, authenticated upload)
-- Anyone can view clips (public bucket)
CREATE POLICY "Public can view all clips" 
ON storage.objects FOR SELECT
USING (bucket_id = 'clips');

-- Only authenticated users can upload clips
CREATE POLICY "Authenticated users can upload clips" 
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (bucket_id = 'clips');

-- Only authenticated users can update clips they own
CREATE POLICY "Users can update their own clips" 
ON storage.objects FOR UPDATE
TO authenticated
USING (
  bucket_id = 'clips'
  AND auth.uid()::text = (storage.foldername(name))[1]
);

-- Only authenticated users can delete clips they own
CREATE POLICY "Users can delete their own clips" 
ON storage.objects FOR DELETE
TO authenticated
USING (
  bucket_id = 'clips'
  AND auth.uid()::text = (storage.foldername(name))[1]
);

-- Log bucket creation for documentation
DO $$
BEGIN
  RAISE NOTICE 'Created video storage buckets:';
  RAISE NOTICE '- full_videos: Private bucket for original/source video files (no size/type limits)';
  RAISE NOTICE '- clips: Public bucket for processed video clips (no size/type limits)';
  RAISE NOTICE 'RLS policies have been configured for both buckets';
END $$; 