import { NextApiRequest, NextApiResponse } from 'next';
import axios from 'axios';
import type { AxiosResponse } from 'axios';
import { IncomingMessage, ServerResponse } from 'http';
import { Readable } from 'stream';

export const config = {
  api: {
    responseLimit: false,
  },
};

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  const { id } = req.query;
  
  try {
    // Get the authorization header from cookies or headers
    const token = req.cookies.token || req.headers.authorization?.toString().replace('Bearer ', '');
    
    // Create the URL for the backend API
    const apiUrl = `http://app:8000/api/v1/media/stream/${id}`;
    
    // Make a request to the backend API with the token
    const response: AxiosResponse<Readable> = await axios({
      method: 'GET',
      url: apiUrl,
      responseType: 'stream',
      headers: {
        'Authorization': token ? `Bearer ${token}` : '',
      },
    });
    
    // Set the appropriate headers
    const contentType = response.headers['content-type'];
    if (contentType) {
      res.setHeader('Content-Type', contentType);
    }
    
    // Set cache control headers
    res.setHeader('Cache-Control', 'no-cache, no-store, must-revalidate');
    res.setHeader('Pragma', 'no-cache');
    res.setHeader('Expires', '0');
    
    // Stream the response
    response.data.pipe(res);
    
    // Handle the end of the stream
    response.data.on('end', () => {
      res.end();
    });
  } catch (error: any) {
    console.error('Error streaming media:', error);
    return res.status(error.response?.status || 500).json({
      error: 'Error streaming media',
      details: error.message || 'Unknown error',
    });
  }
}
