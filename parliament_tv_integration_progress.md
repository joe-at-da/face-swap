# Parliament TV Integration Progress Tracker

## Overview
This document tracks the progress of implementing the Parliament TV recognition pipeline integration with Supabase.

## Current Status: In Progress

## Completed Tasks
- ✅ Fixed transcription parsing in `process_video_with_transcription` to handle Parliament TV format
- ✅ Added proper timestamp parsing for format `[HH:MM:SS - HH:MM:SS]`
- ✅ Implemented `get_recognition_results` method to retrieve recognition results from DB
- ✅ Fixed `get_recognition_status` method for proper DB querying and error handling
- ✅ Verified that the recognition pipeline can process real Parliament TV transcriptions
- ✅ Confirmed that the system correctly handles separate audio and video streams
- ✅ Implemented `/api/v1/parliament-tv/extract-url` endpoint that returns video_url, audio_url, event_id
- ✅ Implemented `/api/v1/recognition/combined-recognition` endpoint for processing videos
- ✅ Implemented `/api/v1/integration/recognition/{video_id}` endpoint for retrieving results
- ✅ Created `export_recognition_results` function for exporting to Supabase format
- ✅ Implemented combined timeline and speaker-attributed transcripts generation

## In Progress Tasks
- 🔄 Implementing the end-to-end workflow for Parliament TV integration with Supabase
- 🔄 Creating the Supabase client integration for uploading videos and clips

## Pending Tasks

1. **End-to-End Integration Flow**
   - [ ] Create a script/endpoint that orchestrates the entire process from URL to Supabase
   - [ ] Implement proper error handling and status tracking throughout the flow

2. **Supabase Integration**
   - [ ] Set up connection to Supabase using SUPABASE_SERVICE_ROLE_KEY
   - [ ] Implement video upload to Supabase storage bucket 'full_videos'
   - [ ] Create functionality to add clips to `parliament_member_clips` table

3. **Speaker Identification and Clip Generation**
   - [ ] Implement logic to identify when MPs start and stop speaking
   - [ ] Create clips based on speaking segments
   - [ ] Handle 60-second pause rule for clip boundaries
   - [ ] Match recognized faces with MP IDs from Supabase

4. **Data Population**
   - [ ] Extract transcript text for each clip using start/end timestamps
   - [ ] Generate proper start/end timestamps in the required format
   - [ ] Calculate duration_seconds for each clip
   - [ ] Set appropriate session metadata (session_date, session_type, etc.)

## Implementation Plan

### Step 1: Create Supabase Client Integration
- Implement a Python module for Supabase integration using the Supabase Python library
- Set up authentication with SUPABASE_SERVICE_ROLE_KEY
- Create functions for uploading videos to the 'full_videos' bucket
- Create functions for adding clip data to the parliament_member_clips table

### Step 2: Implement Speaker Segmentation Logic
- Create a function to process recognition results and transcription data
- Identify speaking segments based on face recognition and transcription
- Apply the 60-second pause rule to determine clip boundaries
- Generate clip metadata including start/end timestamps and transcript text

### Step 3: Create End-to-End Integration Flow
- Implement a function that orchestrates the entire process:
  1. Extract URLs from Parliament TV page using `/api/v1/parliament-tv/extract-url`
  2. Capture video using original URL
  3. Trigger recognition process using `/api/v1/recognition/combined-recognition`
  4. Wait for recognition to complete
  5. Retrieve recognition results using `/api/v1/integration/recognition/{video_id}`
  6. Process results to identify speaking segments
  7. Upload full video to Supabase
  8. Add clips to parliament_member_clips table

### Step 4: Testing and Validation
- Test end-to-end flow with real Parliament TV URLs
- Verify clips are correctly identified and uploaded
- Validate data in Supabase

## Required Fields for parliament_member_clips Table
- **member_id**: integer (required) - ID of the MP speaking
- **transcript**: text (required) - Text for the MP speaking
- **full_video_path**: text (required) - Path to the full video with audio
- **start_timestamp**: text (required) - When MP starts speaking (e.g., "00:10:53")
- **end_timestamp**: text (required) - When MP stops speaking (e.g., "00:11:43")
- **duration_seconds**: numeric (optional) - Can be calculated from start/end timestamps
- **session_date**: date (optional) - Date of the parliamentary session
- **session_type**: text (optional) - Type of parliamentary session
- **debate_topic**: text (optional) - Topic of debate
- **status**: parliament_clip_status (default: 'pending_review') - Status of the clip

## Integration Flow Diagram

```
1. Extract URLs from Parliament TV
   |  
   v
2. Capture video using original URL
   |  
   v
3. Run combined recognition
   |  
   v
4. Retrieve recognition results
   |  
   v
5. Process results to identify speaking segments
   |  
   v
6. Upload full video to Supabase
   |  
   v
7. Add clips to parliament_member_clips table
```
