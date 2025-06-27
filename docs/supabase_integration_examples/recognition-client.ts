/**
 * Parliament TV Recognition Client for Supabase Integration
 * 
 * This TypeScript client provides functions to interact with the Parliament TV
 * recognition API from the Supabase frontend application.
 */

import axios from 'axios';

// Types for the recognition API responses
interface RecognitionResult {
  video_id: number;
  title: string;
  description: string;
  capture_date: string;
  duration: number;
  status: string;
  results: any; // Recognition results object
  audio_url: string;
  video_url: string;
  combined_av_url: string;
}

interface VideoListItem {
  video_id: number;
  title: string;
  description: string;
  capture_date: string;
  duration: number;
  status: string;
  has_results: boolean;
  audio_url: string;
  video_url: string;
  combined_av_url: string;
}

interface VideoListResponse {
  success: boolean;
  total: number;
  offset: number;
  limit: number;
  videos: VideoListItem[];
}

/**
 * Parliament TV Recognition Client
 * 
 * This client provides methods to interact with the Parliament TV
 * recognition API for the Supabase integration.
 */
export class ParliamentTVRecognitionClient {
  private baseUrl: string;
  private apiKey: string;

  /**
   * Create a new Parliament TV Recognition Client
   * 
   * @param baseUrl - Base URL of the Parliament TV API
   * @param apiKey - API key for authentication
   */
  constructor(baseUrl: string, apiKey: string) {
    this.baseUrl = baseUrl;
    this.apiKey = apiKey;
  }

  /**
   * Get the headers for API requests
   */
  private getHeaders() {
    return {
      'Authorization': `Bearer ${this.apiKey}`,
      'Content-Type': 'application/json',
    };
  }

  /**
   * Get recognition results for a specific video
   * 
   * @param videoId - ID of the video to get recognition results for
   * @returns Promise with recognition results
   */
  async getRecognitionResults(videoId: number): Promise<RecognitionResult> {
    try {
      const response = await axios.get(
        `${this.baseUrl}/api/v1/integration/recognition/${videoId}`,
        { headers: this.getHeaders() }
      );
      return response.data;
    } catch (error) {
      console.error('Error fetching recognition results:', error);
      throw error;
    }
  }

  /**
   * List videos with recognition data
   * 
   * @param limit - Maximum number of videos to return (default: 10)
   * @param offset - Offset for pagination (default: 0)
   * @param status - Filter by recognition status (optional)
   * @returns Promise with video list response
   */
  async listVideos(
    limit: number = 10,
    offset: number = 0,
    status?: string
  ): Promise<VideoListResponse> {
    try {
      let url = `${this.baseUrl}/api/v1/integration/videos?limit=${limit}&offset=${offset}`;
      if (status) {
        url += `&status=${status}`;
      }

      const response = await axios.get(url, { headers: this.getHeaders() });
      return response.data;
    } catch (error) {
      console.error('Error listing videos:', error);
      throw error;
    }
  }

  /**
   * Import recognition results into Supabase
   * 
   * @param videoId - ID of the video to import recognition results for
   * @param supabaseClient - Supabase client instance
   * @returns Promise with import results
   */
  async importRecognitionResults(videoId: number, supabaseClient: any): Promise<any> {
    try {
      // 1. Get recognition results from Parliament TV
      const recognitionResults = await this.getRecognitionResults(videoId);
      
      // 2. Store video metadata in Supabase
      const { data: videoData, error: videoError } = await supabaseClient
        .from('parliament_videos')
        .upsert({
          external_id: recognitionResults.video_id,
          title: recognitionResults.title,
          description: recognitionResults.description,
          capture_date: recognitionResults.capture_date,
          duration: recognitionResults.duration,
          combined_av_url: recognitionResults.combined_av_url,
          status: recognitionResults.status,
          imported_at: new Date().toISOString(),
        })
        .select();
      
      if (videoError) throw videoError;
      
      // 3. Store recognition results in Supabase
      if (recognitionResults.results) {
        // Process speaker data
        const speakers = recognitionResults.results.speakers || [];
        
        // Store speaker appearances
        for (const speaker of speakers) {
          const { data: speakerData, error: speakerError } = await supabaseClient
            .from('speaker_appearances')
            .upsert({
              video_id: videoData[0].id,
              parliament_id: speaker.parliament_id || null,
              name: speaker.name,
              confidence: speaker.confidence || 0,
              first_appearance: speaker.first_appearance || 0,
              last_appearance: speaker.last_appearance || 0,
              total_time: speaker.total_time || 0,
              appearances: speaker.appearances || [],
            });
          
          if (speakerError) throw speakerError;
        }
      }
      
      return {
        success: true,
        message: 'Recognition results imported successfully',
        video_id: videoData[0].id,
      };
    } catch (error) {
      console.error('Error importing recognition results:', error);
      throw error;
    }
  }
}

/**
 * Example usage:
 * 
 * ```typescript
 * import { ParliamentTVRecognitionClient } from './recognition-client';
 * import { createClient } from '@supabase/supabase-js';
 * 
 * // Initialize Supabase client
 * const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
 * const supabaseKey = process.env.SUPABASE_SERVICE_ROLE_KEY!;
 * const supabase = createClient(supabaseUrl, supabaseKey);
 * 
 * // Initialize Parliament TV Recognition Client
 * const parliamentTvUrl = process.env.PARLIAMENT_TV_API_URL!;
 * const parliamentTvApiKey = process.env.PARLIAMENT_TV_API_KEY!;
 * const recognitionClient = new ParliamentTVRecognitionClient(
 *   parliamentTvUrl,
 *   parliamentTvApiKey
 * );
 * 
 * // Get recognition results for a specific video
 * const videoId = 123;
 * recognitionClient.getRecognitionResults(videoId)
 *   .then(results => console.log('Recognition results:', results))
 *   .catch(error => console.error('Error:', error));
 * 
 * // List videos with recognition data
 * recognitionClient.listVideos(10, 0, 'completed')
 *   .then(response => console.log('Videos:', response.videos))
 *   .catch(error => console.error('Error:', error));
 * 
 * // Import recognition results into Supabase
 * recognitionClient.importRecognitionResults(videoId, supabase)
 *   .then(result => console.log('Import result:', result))
 *   .catch(error => console.error('Error:', error));
 * ```
 */
