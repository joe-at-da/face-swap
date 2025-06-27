# Parliament TV and MPAI-NextJS-Supabase Integration Plan

This document outlines a phased approach to integrate the Parliament TV system with the MPAI NextJS Supabase project.

## Current Architecture

### Parliament TV Project (the-mp)
- **Backend**: FastAPI (Python)
- **Frontend**: Next.js
- **Database**: PostgreSQL
- **Background Processing**: Celery with Redis
- **Key Features**: 
  - Parliament TV video capture
  - Face detection and speaker identification
  - Audio transcription
  - Separate handling of audio and video streams

### MPAI NextJS Supabase Project
- **Frontend**: Next.js
- **Backend**: Supabase
- **Key Features**:
  - Integration with official Parliament API
  - Member data synchronization
  - Voting history tracking

## Phase 1: Independent Operation (Current)

In this phase, both systems operate independently while we prepare for future integration.

### Data Exchange Strategy

1. **File-Based Exchange**:
   - Parliament TV system exports recognition results to JSON files
   - MPAI Supabase system imports these files manually or via scheduled tasks
   - Shared file storage location accessible to both systems

2. **Manual Data Transfer**:
   - Export data from Parliament TV system database
   - Import into Supabase using Supabase's import tools

### Configuration Requirements

1. **Parliament TV System**:
   - Add export functionality to generate standardized JSON output files
   - Create data export endpoints (optional)
   - Document data schemas for recognition results
   - Configure environment variables to access Supabase in future phases:
     ```
     # For Phase 2 and beyond - not required for Phase 1
     SUPABASE_URL=http://127.0.0.1:54321  # Local development
     SUPABASE_API_KEY=your-api-key-here
     ```

2. **MPAI Supabase System**:
   - Create import functionality for Parliament TV data
   - Define Supabase tables to store Parliament TV data
   - Add data transformation logic to map between systems
   - Current configuration example:
     ```
     NEXT_PUBLIC_BASE_URL=http://127.0.0.1:3001
     
     #supabase
     NEXT_PUBLIC_SUPABASE_URL=http://127.0.0.1:54321
     NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
     SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
     ```

## Phase 2: Loose Coupling

In this phase, we establish lightweight integration points without tight coupling.

### Key Differences Between Systems

1. **Data Structure**:
   - Parliament TV: Uses a relational database with complex relationships
   - MPAI Supabase: Uses a simpler document-based structure

2. **Media Handling**:
   - Parliament TV: Works with separate audio and video streams from Parliament TV site
   - MPAI Supabase: Requires unified audio-video files for processing

3. **Stream Management**:
   - Parliament TV: Maintains separation of audio and video streams for flexibility
   - MPAI Supabase: Expects combined audio-video content for simplified processing

### Integration Approach

1. **REST API Integration**:
   - Parliament TV system exposes REST API endpoints
   - MPAI Supabase consumes these endpoints
   - Authentication via API keys

2. **Webhook Notifications**:
   - Parliament TV system sends webhook notifications on events
   - MPAI Supabase system listens for these notifications
   - Triggers data pulls when needed

### Implementation Steps

1. **Parliament TV System**:
   ```python
   # backend/api/v1/endpoints/integration.py
   from fastapi import APIRouter, Depends, HTTPException, Security
   from backend.db.models import RecognitionProcess
   from backend.db.session import get_db
   from backend.core.security import get_api_key
   
   router = APIRouter()
   
   @router.get("/integration/recognition/{video_id}", dependencies=[Security(get_api_key)])
   def get_recognition_results(video_id: int, db = Depends(get_db)):
       """Get recognition results for integration with other systems"""
       process = db.query(RecognitionProcess).filter(
           RecognitionProcess.video_id == video_id
       ).first()
       
       if not process:
           raise HTTPException(status_code=404, detail="Recognition process not found")
           
       return {
           "success": True,
           "video_id": video_id,
           "results": process.results
       }
   ```

2. **MPAI Supabase System**:
   ```typescript
   // services/parliament-tv/parliament-tv-api.ts
   import { createClient } from '@supabase/supabase-js'

   const supabase = createClient(
     process.env.NEXT_PUBLIC_SUPABASE_URL!,
     process.env.SUPABASE_SERVICE_ROLE_KEY!
   )

   export async function fetchRecognitionResults(videoId: number) {
     const response = await fetch(
       `${process.env.PARLIAMENT_TV_API_URL}/integration/recognition/${videoId}`,
       {
         headers: {
           'Authorization': `Bearer ${process.env.PARLIAMENT_TV_API_KEY}`
         }
       }
     )
     
     if (!response.ok) {
       throw new Error(`Failed to fetch recognition results: ${response.statusText}`)
     }
     
     const data = await response.json()
     
     // Store in Supabase
     await supabase
       .from('parliament_tv_recognition')
       .upsert({
         external_video_id: videoId,
         recognition_data: data.results,
         updated_at: new Date().toISOString()
       })
     
     return data
   }
   ```

## Phase 3: Full Integration

In the final phase, we implement a more robust integration strategy.

### Integration Options

1. **Queue-Based Integration**:
   - Shared Redis instance for message passing
   - Producer/consumer pattern for asynchronous processing
   - Reliable delivery with acknowledgments

2. **Combined Docker Deployment**:
   - Single Docker Compose configuration
   - Shared networks between containers
   - Centralized logging and monitoring

3. **Database Integration**:
   - Foreign key relationships between systems
   - Database views for cross-system queries
   - Potential migration to a unified database

### Technical Considerations

1. **Authentication & Security**:
   - Shared authentication mechanism
   - API key rotation and management
   - Rate limiting and monitoring

2. **Error Handling**:
   - Retry mechanisms for failed operations
   - Dead letter queues for unprocessable messages
   - Alerting for integration failures

3. **Data Consistency**:
   - Idempotent operations to prevent duplicates
   - Transaction boundaries across systems
   - Conflict resolution strategies

## Implementation Timeline

| Phase | Timeframe | Key Deliverables |
|-------|-----------|------------------|
| Phase 1 | Current | Data export/import functionality, Documentation |
| Phase 2 | Q3 2025 | REST API endpoints, Webhook notifications |
| Phase 3 | Q4 2025 | Queue-based integration, Combined deployment |

## How to Use This Integration

### For Parliament TV System Developers

1. **Exporting Recognition Results**:
   - After facial recognition processing completes, the system automatically exports data to the `{video_name}_supabase_export` directory
   - Two files are generated: `{video_id}_video.json` and `{video_id}_clips.json`
   - These files contain the formatted data ready for Supabase queue ingestion
   - No manual action is required as the export is integrated into the recognition pipeline
   - The system automatically combines separate audio and video streams into a unified file for Supabase

2. **Accessing Exported Files**:
   - Files are stored in the same directory as the processed video
   - The path to exported files is included in the recognition results under the `supabase_export` key
   - Example: `/app/data/videos/parliament_20250626_supabase_export/parliament_20250626_video.json`
   - Combined audio-video files are stored in `/app/data/media/combined/{video_id}_combined.mp4`

3. **Media Handling**:
   - Parliament TV continues to work with separate audio and video streams internally
   - For Supabase integration, the system automatically combines audio and video using FFmpeg
   - The combined file URL is provided in the exported JSON data
   - Original separate URLs are preserved in the metadata

4. **Troubleshooting**:
   - Check the application logs for any export errors
   - Verify that the `backend/services/integration/supabase_export.py` module is correctly imported
   - Ensure the video metadata can be retrieved from the database
   - If audio-video combination fails, check FFmpeg installation and file permissions

### For Supabase System Developers

1. **Importing Recognition Data**:
   - Access the exported JSON files from the Parliament TV system
   - Use the Supabase client to insert data into the appropriate tables or queues
   - Example:
     ```typescript
     import { createClient } from '@supabase/supabase-js'
     import fs from 'fs'
     
     const supabase = createClient(
       process.env.NEXT_PUBLIC_SUPABASE_URL!,
       process.env.SUPABASE_SERVICE_ROLE_KEY!
     )
     
     // Import video data
     const videoData = JSON.parse(fs.readFileSync('path/to/video.json', 'utf8'))
     await supabase.from('videos').upsert(videoData)
     
     // Import clips data
     const clipsData = JSON.parse(fs.readFileSync('path/to/clips.json', 'utf8'))
     await supabase.from('clips').upsert(clipsData.clips)
     ```

2. **Media Access**:
   - The video_url field in the imported data now points to a combined audio-video file
   - No separate handling of audio and video streams is required
   - Original separate URLs are preserved in the metadata if needed
   - The combined file is in MP4 format with AAC audio codec for maximum compatibility

3. **Queue Processing**:
   - Once data is imported, it can be processed by the existing Supabase queue workers
   - No changes to queue processing logic are needed if the data format matches expectations

## Next Steps

1. ✅ Document data schemas for Parliament TV recognition results
2. ✅ Create export functionality in Parliament TV system
3. Define Supabase tables for Parliament TV data
4. Implement basic import functionality in MPAI Supabase
5. Test end-to-end integration with real Parliament TV data
