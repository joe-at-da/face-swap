-- Debug script to check the clip that's failing
-- Run this in your Supabase SQL editor

-- Check if the clip exists at all
SELECT 
    id,
    transcript IS NOT NULL as has_transcript,
    transcript_embedding IS NOT NULL as has_embedding,
    is_deleted,
    length(transcript) as transcript_length
FROM parliament_member_clips 
WHERE id = '9be356d1-f1e3-492d-8b25-87026db88ad0';

-- Check the exact query the API is running
SELECT id, transcript, transcript_embedding
FROM parliament_member_clips
WHERE id = '9be356d1-f1e3-492d-8b25-87026db88ad0'
AND is_deleted = false;

-- Check if there are any clips with transcripts but no embeddings
SELECT 
    id,
    transcript IS NOT NULL as has_transcript,
    transcript_embedding IS NOT NULL as has_embedding,
    is_deleted,
    length(transcript) as transcript_length
FROM parliament_member_clips 
WHERE transcript IS NOT NULL 
AND transcript_embedding IS NULL
AND is_deleted = false
LIMIT 5;

-- Check recent embedding logs
SELECT * FROM transcript_embedding_logs 
ORDER BY created_at DESC 
LIMIT 10;