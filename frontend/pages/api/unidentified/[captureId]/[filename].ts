import type { NextApiRequest, NextApiResponse } from 'next';
import axios from 'axios';

/**
 * API route to proxy unidentified face images from the backend
 * This helps avoid CORS issues and provides a more reliable way to access the images
 */
export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  const { captureId, filename } = req.query;
  
  if (!captureId || !filename) {
    return res.status(400).json({ error: 'Missing required parameters' });
  }
  
  // Get the API base URL from environment or use default
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
  
  try {
    // Construct the backend URL
    const backendUrl = `${apiBaseUrl}/recognition/unidentified/${captureId}/${filename}`;
    console.log(`Proxying request to: ${backendUrl}`);
    
    // Make request to backend with responseType 'arraybuffer' to handle binary data
    const response = await axios.get(backendUrl, {
      responseType: 'arraybuffer',
      headers: {
        // Forward authorization header if present
        ...(req.headers.authorization ? { Authorization: req.headers.authorization } : {})
      }
    });
    
    // Set the correct content type
    const contentType = response.headers['content-type'] || 'image/jpeg';
    res.setHeader('Content-Type', contentType);
    
    // Return the image data
    return res.status(200).send(response.data);
  } catch (error) {
    console.error('Error proxying unidentified face image:', error);
    
    // Try alternative URL formats if the main one fails
    try {
      // Try with leading zeros in the capture ID
      const paddedCaptureId = String(captureId).padStart(4, '0');
      const alternativeUrl = `${apiBaseUrl}/recognition/unidentified/${paddedCaptureId}/${filename}`;
      console.log(`Trying alternative URL: ${alternativeUrl}`);
      
      const response = await axios.get(alternativeUrl, {
        responseType: 'arraybuffer',
        headers: {
          ...(req.headers.authorization ? { Authorization: req.headers.authorization } : {})
        }
      });
      
      const contentType = response.headers['content-type'] || 'image/jpeg';
      res.setHeader('Content-Type', contentType);
      return res.status(200).send(response.data);
    } catch (alternativeError) {
      console.error('Error with alternative URL:', alternativeError);
      
      // If all attempts fail, return a 404
      return res.status(404).json({ error: 'Image not found' });
    }
  }
}
