import { apiClient } from './apiClient';

interface ExtractAudioResponse {
  success: boolean;
  message: string;
  error?: string;
  output_file?: string;
}

/**
 * Extract audio for a specific capture ID
 * @param captureId The ID of the capture to extract audio for
 * @returns Promise that resolves with the extraction result
 */
export const extractAudioForCapture = async (captureId: number): Promise<ExtractAudioResponse> => {
  try {
    const response = await apiClient.post<ExtractAudioResponse>(`/parliament-tv/audio-extraction/${captureId}`);
    console.log('Audio extraction response:', response.data);
    return response.data;
  } catch (error: any) {
    console.error('Error extracting audio:', error);
    
    // Try to extract error information from the response if available
    let errorMessage = 'Failed to extract audio';
    if (error.response && error.response.data) {
      if (error.response.data.error) {
        errorMessage = error.response.data.error;
      } else if (error.response.data.detail) {
        errorMessage = error.response.data.detail;
      }
    }
    
    return {
      success: false,
      message: errorMessage,
      error: errorMessage
    };
  }
};
