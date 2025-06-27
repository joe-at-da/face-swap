# Parliament TV - Supabase Integration

This document provides implementation details and usage instructions for the integration between Parliament TV and Supabase. The integration allows Supabase to access facial recognition results from Parliament TV while maintaining separate audio and video streams internally.

## Architecture Overview

The integration follows a phased approach:

1. **Phase 1 (Current)**: File-based exchange with combined audio-video files for Supabase
2. **Phase 2 (Implemented)**: REST API integration with API key authentication
3. **Phase 3 (Future)**: Queue-based messaging and tighter integration

## Key Components

### Parliament TV Backend

1. **Security Module (`security.py`)**
   - API key authentication for secure external access
   - API key for external integrations like Supabase
   - Uses `INTEGRATION_API_KEY` environment variable

2. **Integration Endpoints (`integration.py`)**
   - `/api/v1/integration/recognition/{video_id}` - Get recognition results for a specific video
   - `/api/v1/integration/videos` - List videos with recognition data

3. **Export Functionality (`supabase_export.py`)**
   - Creates combined audio-video files for Supabase
   - Exports recognition results in a compatible format

4. **AV Combiner (`av_combiner.py`)**
   - Combines separate audio and video streams into a single file
   - Maintains quality by avoiding re-encoding where possible

### Supabase Frontend

1. **Recognition Client (`recognition-client.ts`)**
   - TypeScript client for interacting with Parliament TV API
   - Methods for fetching and importing recognition results

2. **Database Schema (`database_schema.sql`)**
   - Tables for storing Parliament TV videos and speaker appearances
   - Indexes and security policies for efficient and secure access

## Setup Instructions

### Parliament TV Backend

1. **Configure Environment Variables**

   Add the following to your `.env` file:
   ```
   # API key for external integrations like Supabase
   INTEGRATION_API_KEY=your_secure_api_key_here
   ```

2. **Verify API Endpoints**

   After starting the Parliament TV backend, verify the integration endpoints:
   ```
   curl -H "Authorization: Bearer your_api_key" http://localhost:8000/api/v1/integration/videos
   ```

### Supabase Frontend

1. **Configure Environment Variables**

   Add the following to your `.env.local` file:
   ```
   PARLIAMENT_TV_API_URL=http://parliament-tv-backend-url
   PARLIAMENT_TV_API_KEY=your_secure_api_key_here
   ```

2. **Set Up Database Tables**

   Run the SQL commands in `database_schema.sql` in your Supabase SQL editor.

3. **Implement the Recognition Client**

   Use the provided `recognition-client.ts` as a reference for implementing the client in your application.

## Usage Examples

### Fetching Recognition Results

```typescript
import { ParliamentTVRecognitionClient } from './lib/recognition-client';

const client = new ParliamentTVRecognitionClient(
  process.env.PARLIAMENT_TV_API_URL!,
  process.env.PARLIAMENT_TV_API_KEY!
);

// Get recognition results for video ID 123
const results = await client.getRecognitionResults(123);
console.log(results);
```

### Importing Results into Supabase

```typescript
import { ParliamentTVRecognitionClient } from './lib/recognition-client';
import { createClient } from '@supabase/supabase-js';

// Initialize Supabase client
const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!
);

// Initialize Parliament TV client
const client = new ParliamentTVRecognitionClient(
  process.env.PARLIAMENT_TV_API_URL!,
  process.env.PARLIAMENT_TV_API_KEY!
);

// Import recognition results
const importResult = await client.importRecognitionResults(123, supabase);
console.log(importResult);
```

## Important Implementation Notes

1. **Audio and Video Streams**
   - Parliament TV maintains separate audio and video streams internally
   - Combined audio-video files are created only for Supabase integration
   - Audio files are named `capture_XXXX.audio.mp3` and video files are named `capture_XXXX.mp4`

2. **API Authentication**
   - All integration endpoints require API key authentication
   - The API key must be provided in the `Authorization` header as `Bearer your_api_key`

3. **Error Handling**
   - The Parliament TV API includes proper error responses with status codes and messages
   - The Recognition Client includes error handling for common issues

## Troubleshooting

### Common Issues

1. **Authentication Errors**
   - Verify that the correct API key is being used
   - Check that the API key is being sent in the correct format (`Bearer your_api_key`)

2. **Missing Combined AV Files**
   - Check that FFmpeg is installed and working correctly
   - Verify that both audio and video files exist for the video ID

3. **Database Import Errors**
   - Ensure that the database schema has been set up correctly
   - Check that the Supabase service role key has the necessary permissions

### Debugging

1. **Parliament TV Backend Logs**
   ```bash
   docker-compose -f docker-compose.dev.yml logs --tail=100 app | grep -i integration
   ```

2. **Supabase Database Queries**
   ```sql
   SELECT * FROM parliament_videos ORDER BY imported_at DESC LIMIT 10;
   ```

## Next Steps (Phase 3)

1. **Webhook Notifications**
   - Implement webhook notifications from Parliament TV to Supabase when new recognition results are available

2. **Real-time Updates**
   - Use Supabase real-time features to update the UI when new data is available

3. **Combined Deployment**
   - Explore options for deploying both systems together for tighter integration

## Contact Information

For questions or issues related to this integration:
- Parliament TV Team: [contact@parliament-tv.example.com](mailto:contact@parliament-tv.example.com)
- Supabase Team: [contact@supabase-team.example.com](mailto:contact@supabase-team.example.com)
