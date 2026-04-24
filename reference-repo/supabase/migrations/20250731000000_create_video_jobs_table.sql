-- Create video_jobs table for persistent job tracking
CREATE TABLE video_jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  job_id TEXT UNIQUE NOT NULL,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  user_clip_id UUID REFERENCES user_clips(id) ON DELETE CASCADE,
  stage TEXT NOT NULL CHECK (stage IN (
    'initializing',
    'creating_user_clip', 
    'extracting_segment',
    'generating_horizontal',
    'generating_vertical',
    'uploading',
    'completed',
    'failed'
  )),
  progress INTEGER NOT NULL DEFAULT 0 CHECK (progress >= 0 AND progress <= 100),
  message TEXT NOT NULL DEFAULT '',
  horizontal_video_url TEXT,
  vertical_video_url TEXT,
  error_message TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index for faster job lookups
CREATE INDEX idx_video_jobs_job_id ON video_jobs(job_id);
CREATE INDEX idx_video_jobs_user_id ON video_jobs(user_id);
CREATE INDEX idx_video_jobs_created_at ON video_jobs(created_at);

-- Create RLS policies
ALTER TABLE video_jobs ENABLE ROW LEVEL SECURITY;

-- Users can only see their own video jobs
CREATE POLICY "Users can view their own video jobs" ON video_jobs
  FOR SELECT USING (auth.uid() = user_id);

-- Users can only insert their own video jobs  
CREATE POLICY "Users can insert their own video jobs" ON video_jobs
  FOR INSERT WITH CHECK (auth.uid() = user_id);

-- Users can only update their own video jobs
CREATE POLICY "Users can update their own video jobs" ON video_jobs
  FOR UPDATE USING (auth.uid() = user_id);

-- Create function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_video_jobs_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to automatically update updated_at
CREATE TRIGGER trigger_update_video_jobs_updated_at
  BEFORE UPDATE ON video_jobs
  FOR EACH ROW
  EXECUTE FUNCTION update_video_jobs_updated_at();

-- Clean up old completed/failed jobs (older than 24 hours)
CREATE OR REPLACE FUNCTION cleanup_old_video_jobs()
RETURNS void AS $$
BEGIN
  DELETE FROM video_jobs 
  WHERE (stage IN ('completed', 'failed')) 
    AND created_at < NOW() - INTERVAL '24 hours';
END;
$$ LANGUAGE plpgsql; 