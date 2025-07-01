# Postman Collections Guide for Parliament Video Clip Manager

This guide explains how to set up and use the Postman collections for testing the Parliament Video Clip Manager API, including the Supabase integration endpoints.

## Available Collections

The project includes two Postman collections:

1. **Main Collection**: `Parliament_Video_Clip_Manager.postman_collection.json`
   - Comprehensive collection with all API endpoints
   - Includes authentication, Parliament TV, recognition, transcription, and Supabase integration endpoints
   - Uses JWT authentication for user endpoints and API key authentication for integration endpoints

2. **Integration Collection**: `integration_endpoints.postman_collection.json`
   - Focused collection specifically for integration endpoints
   - Designed for external systems that need to integrate with the application
   - Uses API key authentication

## Which Collection to Use?

- **For development and testing all features**: Use the main collection
- **For integration partners or when focusing only on integration endpoints**: Use the integration collection

## Setup Instructions

### Setting Up the Main Collection

1. Open Postman
2. Click on "Import" in the top left corner
3. Select the file: `docs/Parliament_Video_Clip_Manager.postman_collection.json`
4. Create a new Environment in Postman with these variables:
   - `base_url`: `http://localhost:8000/api/v1` (or your deployed API URL)
   - `email`: Your login email
   - `password`: Your login password
   - `integration_api_key`: Your API key for integration endpoints (from `INTEGRATION_API_KEY` env var)
   - `video_id`: ID of a video you want to test with

5. The collection includes a pre-request script that automatically handles authentication for endpoints requiring JWT tokens

### Setting Up the Integration Collection

1. Open Postman
2. Click on "Import" in the top left corner
3. Select the file: `docs/integration_endpoints.postman_collection.json`
4. Create or use the same Environment with these variables:
   - `base_url`: `http://localhost:8000` (note: no `/api/v1` suffix for this collection)
   - `integration_api_key`: Your API key for integration endpoints
   - `video_id`: ID of a video to test with
   - `file_path`: Path to a media file to download (when testing file endpoints)

## Authentication Methods

The collections use two different authentication methods:

1. **JWT Authentication** (Main collection): 
   - Used for user-facing endpoints
   - The pre-request script handles this automatically

2. **API Key Authentication** (Both collections):
   - Used for integration endpoints including all Supabase endpoints
   - Requires the `X-API-Key` header with your `integration_api_key` value
   - This is pre-configured in the requests

## Testing the Supabase Integration Endpoints

The Supabase integration endpoints are organized in three folders:

1. **Supabase Integration**:
   - `Export to Supabase`: Export recognition and transcription data to Supabase format
   - `Get Supabase Integration Status`: Check the status of Supabase integration for a video

2. **Supabase Automation**:
   - `Process Parliament TV`: Automated workflow to capture Parliament TV, run recognition, and export to Supabase

3. **Supabase Webhooks**:
   - `Process Video Webhook`: Trigger video processing from Supabase
   - `Transcription Status Webhook`: Receive transcription status updates from Supabase

To test these endpoints:

1. Ensure your `INTEGRATION_API_KEY` is set in your environment variables
2. In Postman, select the environment you created
3. Navigate to the "Supabase Integration" or "Supabase Webhooks" folder
4. Set a valid `video_id` in your environment variables
5. Send the requests to test the endpoints

## Important Notes

- The Parliament TV system handles audio and video streams separately. When testing endpoints that process media, ensure you're using the correct audio URLs directly rather than trying to derive them from video URLs.
- All Supabase integration endpoints require API key authentication via the `X-API-Key` header.
- The API key must match the `INTEGRATION_API_KEY` environment variable set in your backend.

## Example API Calls

### Process Parliament TV (Automated Workflow)

```bash
curl -X POST "http://localhost:8000/api/v1/supabase-automation/process-parliament-tv" \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://parliamentlive.tv/event/index/97c409d6-cd51-4596-9921-96e0bfeb7677", 
    "title": "Test Capture", 
    "description": "Test description", 
    "duration": 90
  }'
```

This endpoint combines Parliament TV capture, recognition, and Supabase export into a single workflow:

- **Parameters**:
  - `url` (required): URL of the Parliament TV event to process
  - `title` (required): Title for the capture
  - `description` (optional): Description of the capture
  - `duration` (optional): Maximum duration to capture in seconds

- **Response**:
  ```json
  {
    "success": true,
    "message": "Parliament TV processing started",
    "capture_id": 123,
    "recognition_id": 456,
    "export_id": 789
  }
  ```
