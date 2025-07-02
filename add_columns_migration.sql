-- Add image_url and face_embedding columns to parliament_members table
ALTER TABLE public.parliament_members ADD COLUMN IF NOT EXISTS image_url TEXT;
ALTER TABLE public.parliament_members ADD COLUMN IF NOT EXISTS face_embedding JSONB;
