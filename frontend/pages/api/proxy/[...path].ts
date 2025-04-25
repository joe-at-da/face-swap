import { NextApiRequest, NextApiResponse } from 'next';

/**
 * API proxy to forward requests to the backend
 * This helps avoid CORS issues when running in Docker
 */
export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  try {
    // Get the path from the request
    const { path } = req.query;
    
    // Construct the backend URL
    // When running in Docker, use the service name 'app'
    const backendUrl = process.env.BACKEND_URL || 'http://app:8000';
    const url = `${backendUrl}/api/v1/${Array.isArray(path) ? path.join('/') : path}`;
    
    // Forward the request to the backend
    const response = await fetch(url, {
      method: req.method,
      headers: {
        'Content-Type': req.headers['content-type'] || 'application/json',
        ...(req.headers.authorization ? { 'Authorization': req.headers.authorization as string } : {})
      },
      body: req.method !== 'GET' && req.method !== 'HEAD' ? JSON.stringify(req.body) : undefined,
    });
    
    // Get the response data
    const data = await response.text();
    
    // Set the response status code
    res.status(response.status);
    
    // Set the response headers
    response.headers.forEach((value, key) => {
      res.setHeader(key, value);
    });
    
    // Send the response
    try {
      // Try to parse as JSON
      const jsonData = JSON.parse(data);
      res.json(jsonData);
    } catch (e) {
      // If not JSON, send as text
      res.send(data);
    }
  } catch (error) {
    console.error('API proxy error:', error);
    res.status(500).json({ error: 'Internal Server Error' });
  }
}
