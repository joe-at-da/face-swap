import { apiClient } from './apiClient';

interface ExtractAudioResponse {
  success: boolean;
  message: string;
}

/**
 * Extract audio for a specific capture ID
 * @param captureId The ID of the capture to extract audio for
 * @returns Promise that resolves when the audio extraction has started
 */
export const extractAudioForCapture = async (captureId: number): Promise<boolean> => {
  try {
    const response = await apiClient.post<ExtractAudioResponse>(`/extract-audio/${captureId}`);
    return response.data.success;
  } catch (error) {
    console.error('Error extracting audio:', error);
    return false;
  }
};
