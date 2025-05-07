import { apiClient } from './apiClient';

interface CaptureStatusResponse {
  success: boolean;
  status: string;
  error?: string;
}

interface AudioStatusResponse {
  success: boolean;
  has_audio: boolean;
  audio_exists: boolean;
  audio_path: string | null;
  capture_status: string;
}

export interface CombinedStatus {
  captureId: number;
  videoReady: boolean;
  audioReady: boolean;
  status: string;
  audioPath?: string;
  videoPath?: string;
}

/**
 * Check the status of a capture, including both video and audio
 * @param captureId The ID of the capture to check
 * @returns Promise that resolves with the combined status
 */
export const checkCaptureStatus = async (captureId: number): Promise<CombinedStatus> => {
  try {
    // Create a timeout promise that will reject after 3 seconds
    const timeout = (ms: number) => new Promise((_, reject) => 
      setTimeout(() => reject(new Error('Request timeout')), ms)
    );

    // Make both API calls in parallel with timeouts
    const [videoResponse, audioResponse] = await Promise.all([
      Promise.race([
        apiClient.get<CaptureStatusResponse>(`/parliament-tv/${captureId}/status`),
        timeout(3000) // 3 second timeout
      ]) as Promise<{ data: CaptureStatusResponse }>,
      Promise.race([
        apiClient.get<AudioStatusResponse>(`/parliament-tv/audio-extraction/${captureId}/status`),
        timeout(3000) // 3 second timeout
      ]) as Promise<{ data: AudioStatusResponse }>
    ]).catch(error => {
      console.error('Error fetching capture status:', error);
      throw error;
    });
    
    // Determine if video is ready
    const videoReady = videoResponse.data.success && 
                       videoResponse.data.status === 'completed';
    
    // Determine if audio is ready
    const audioReady = audioResponse.data.success && 
                       audioResponse.data.audio_exists;
    
    return {
      captureId,
      videoReady,
      audioReady,
      status: videoResponse.data.status,
      audioPath: audioResponse.data.audio_path || undefined,
      videoPath: undefined // Add this if you have a way to get the video path
    };
  } catch (error) {
    console.error('Error checking capture status:', error);
    return {
      captureId,
      videoReady: false,
      audioReady: false,
      status: 'error'
    };
  }
};
