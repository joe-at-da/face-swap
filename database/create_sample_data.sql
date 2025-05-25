-- Sample data for Parliament Video Clip Manager
-- This script adds sample data to the database for testing and development

-- Sample users (password is 'password' for all users)
INSERT INTO users (email, hashed_password, full_name, role, is_active, created_at, updated_at)
VALUES
  ('admin@example.com', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', 'Admin User', 'ADMIN', true, NOW(), NOW()),
  ('user@example.com', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', 'Regular User', 'USER', true, NOW(), NOW()),
  ('editor@example.com', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', 'Editor User', 'EDITOR', true, NOW(), NOW())
ON CONFLICT (email) DO NOTHING;

-- Sample MPs
INSERT INTO mps (name, party, constituency, photo_url, created_at, updated_at)
VALUES
  ('John Smith', 'Labour', 'Manchester Central', '/data/mp_photos/john_smith.jpg', NOW(), NOW()),
  ('Sarah Johnson', 'Conservative', 'Surrey Heath', '/data/mp_photos/sarah_johnson.jpg', NOW(), NOW()),
  ('David Williams', 'Liberal Democrat', 'Oxford West', '/data/mp_photos/david_williams.jpg', NOW(), NOW()),
  ('Emma Brown', 'Green', 'Brighton Pavilion', '/data/mp_photos/emma_brown.jpg', NOW(), NOW()),
  ('Robert Wilson', 'SNP', 'Glasgow South', '/data/mp_photos/robert_wilson.jpg', NOW(), NOW())
ON CONFLICT (name) DO NOTHING;

-- Sample capture sessions
INSERT INTO capture_sessions (title, description, stream_url, start_time, end_time, status, created_by_id, created_at, updated_at)
VALUES
  ('Morning Session', 'Parliamentary morning debate on healthcare', 'https://example.com/stream1.m3u8', NOW() - INTERVAL '2 hours', NOW() - INTERVAL '1 hour', 'COMPLETED', 1, NOW(), NOW()),
  ('Afternoon Session', 'Budget discussion', 'https://example.com/stream2.m3u8', NOW() - INTERVAL '5 hours', NOW() - INTERVAL '3 hours', 'COMPLETED', 1, NOW(), NOW()),
  ('Evening Session', 'Foreign policy debate', 'https://example.com/stream3.m3u8', NOW() - INTERVAL '8 hours', NOW() - INTERVAL '6 hours', 'COMPLETED', 1, NOW(), NOW()),
  ('Special Committee', 'Education committee meeting', 'https://example.com/stream4.m3u8', NOW() - INTERVAL '1 day', NOW() - INTERVAL '22 hours', 'COMPLETED', 2, NOW(), NOW()),
  ('Current Session', 'Live parliamentary session', 'https://example.com/stream5.m3u8', NOW() - INTERVAL '30 minutes', NULL, 'ACTIVE', 1, NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Sample video clips
INSERT INTO video_clips (title, description, file_path, thumbnail_path, start_time, end_time, duration_seconds, status, capture_session_id, created_by_id, created_at, updated_at)
VALUES
  ('Healthcare Statement', 'Minister of Health statement on NHS funding', '/data/media/clips/clip1.mp4', '/data/media/thumbnails/thumb1.jpg', NOW() - INTERVAL '1 hour 45 minutes', NOW() - INTERVAL '1 hour 43 minutes', 120, 'READY', 1, 1, NOW(), NOW()),
  ('Budget Announcement', 'Chancellor announcing new budget measures', '/data/media/clips/clip2.mp4', '/data/media/thumbnails/thumb2.jpg', NOW() - INTERVAL '4 hours 30 minutes', NOW() - INTERVAL '4 hours 27 minutes', 180, 'READY', 2, 1, NOW(), NOW()),
  ('Foreign Policy Question', 'PM answering question on foreign policy', '/data/media/clips/clip3.mp4', '/data/media/thumbnails/thumb3.jpg', NOW() - INTERVAL '7 hours 15 minutes', NOW() - INTERVAL '7 hours 13 minutes', 120, 'READY', 3, 1, NOW(), NOW()),
  ('Education Funding', 'Discussion on education funding', '/data/media/clips/clip4.mp4', '/data/media/thumbnails/thumb4.jpg', NOW() - INTERVAL '23 hours 30 minutes', NOW() - INTERVAL '23 hours 28 minutes', 120, 'READY', 4, 2, NOW(), NOW()),
  ('Current Debate', 'Ongoing debate clip being processed', '/data/media/clips/clip5.mp4', '/data/media/thumbnails/thumb5.jpg', NOW() - INTERVAL '15 minutes', NOW() - INTERVAL '14 minutes', 60, 'PROCESSING', 5, 1, NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Sample MP appearances in clips
INSERT INTO mp_appearances (mp_id, video_clip_id, appearance_time, confidence_score, created_at, updated_at)
VALUES
  (1, 1, NOW() - INTERVAL '1 hour 44 minutes', 0.92, NOW(), NOW()),
  (2, 2, NOW() - INTERVAL '4 hours 28 minutes', 0.88, NOW(), NOW()),
  (3, 3, NOW() - INTERVAL '7 hours 14 minutes', 0.95, NOW(), NOW()),
  (4, 4, NOW() - INTERVAL '23 hours 29 minutes', 0.91, NOW(), NOW()),
  (5, 5, NOW() - INTERVAL '14 minutes 30 seconds', 0.85, NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Sample transcriptions
INSERT INTO transcriptions (video_clip_id, text, start_time, end_time, speaker, confidence_score, created_at, updated_at)
VALUES
  (1, 'We are increasing NHS funding by 10 billion pounds over the next five years.', NOW() - INTERVAL '1 hour 44 minutes 30 seconds', NOW() - INTERVAL '1 hour 44 minutes', 'John Smith', 0.89, NOW(), NOW()),
  (2, 'The new budget will focus on sustainable growth and supporting small businesses.', NOW() - INTERVAL '4 hours 29 minutes', NOW() - INTERVAL '4 hours 28 minutes 30 seconds', 'Sarah Johnson', 0.92, NOW(), NOW()),
  (3, 'Our foreign policy remains committed to international cooperation and security.', NOW() - INTERVAL '7 hours 14 minutes 30 seconds', NOW() - INTERVAL '7 hours 14 minutes', 'David Williams', 0.88, NOW(), NOW()),
  (4, 'Education funding will be increased by 5% in real terms over the next year.', NOW() - INTERVAL '23 hours 29 minutes 30 seconds', NOW() - INTERVAL '23 hours 29 minutes', 'Emma Brown', 0.90, NOW(), NOW()),
  (5, 'We must address climate change with concrete actions, not just words.', NOW() - INTERVAL '14 minutes 45 seconds', NOW() - INTERVAL '14 minutes 15 seconds', 'Robert Wilson', 0.87, NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Sample social posts
INSERT INTO social_posts (platform, content, status, scheduled_time, posted_time, video_clip_id, created_by_id, created_at, updated_at)
VALUES
  ('TWITTER', 'Minister announces £10 billion NHS funding increase #Parliament #Healthcare', 'POSTED', NOW() - INTERVAL '1 hour 30 minutes', NOW() - INTERVAL '1 hour 30 minutes', 1, 1, NOW(), NOW()),
  ('FACEBOOK', 'Chancellor reveals new budget focusing on small businesses and sustainable growth. Watch the full statement here.', 'POSTED', NOW() - INTERVAL '4 hours', NOW() - INTERVAL '4 hours', 2, 1, NOW(), NOW()),
  ('TWITTER', 'Foreign policy update from today''s parliamentary session #ForeignPolicy #Parliament', 'SCHEDULED', NOW() + INTERVAL '1 hour', NULL, 3, 1, NOW(), NOW()),
  ('FACEBOOK', 'Education funding to increase by 5% in real terms. Great news for schools! #Education #Budget', 'DRAFT', NULL, NULL, 4, 2, NOW(), NOW()),
  ('TWITTER', 'Important statement on climate action from today''s debate #ClimateAction #Parliament', 'SCHEDULED', NOW() + INTERVAL '2 hours', NULL, 5, 1, NOW(), NOW())
ON CONFLICT DO NOTHING;

-- Sample tags
INSERT INTO tags (name, created_at, updated_at)
VALUES
  ('Healthcare', NOW(), NOW()),
  ('Budget', NOW(), NOW()),
  ('Foreign Policy', NOW(), NOW()),
  ('Education', NOW(), NOW()),
  ('Climate Change', NOW(), NOW())
ON CONFLICT (name) DO NOTHING;

-- Sample clip tags
INSERT INTO clip_tags (video_clip_id, tag_id, created_at, updated_at)
VALUES
  (1, 1, NOW(), NOW()),
  (2, 2, NOW(), NOW()),
  (3, 3, NOW(), NOW()),
  (4, 4, NOW(), NOW()),
  (5, 5, NOW(), NOW())
ON CONFLICT DO NOTHING;
