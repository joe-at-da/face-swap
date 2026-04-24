-- Remove SVG from allowed MIME types in user-uploads bucket to prevent XSS attacks.
-- SVG files can contain embedded JavaScript that executes when rendered in a browser.
UPDATE storage.buckets
SET allowed_mime_types = ARRAY['image/jpeg','image/jpg','image/png','image/gif','image/webp']
WHERE id = 'user-uploads';
