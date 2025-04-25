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
    // When running in Docker, we need to use the correct service name
    // and localhost when running locally
    let backendUrl;
    
    // Check if we're running in a Docker container
    if (process.env.NODE_ENV === 'production') {
      // In production or Docker, use the service name
      backendUrl = 'http://app:8000';
    } else {
      // In development outside Docker, use localhost
      backendUrl = 'http://localhost:8000';
    }
    
    console.log('Backend URL for proxy:', backendUrl);
    const url = `${backendUrl}/api/v1/${Array.isArray(path) ? path.join('/') : path}`;
    
    console.log('Proxying request to:', url, 'Method:', req.method);
    
    try {
      // Handle form data for login requests
      let body: string | URLSearchParams | undefined;
      const headers: Record<string, string> = {};
      
      // Add authorization header if present
      if (req.headers.authorization) {
        headers['Authorization'] = req.headers.authorization as string;
      }
      
      // Special handling for different content types
      if (req.headers['content-type']?.includes('application/json')) {
        headers['Content-Type'] = 'application/json';
        body = req.method !== 'GET' && req.method !== 'HEAD' ? JSON.stringify(req.body) : undefined;
      } else if (req.headers['content-type']?.includes('application/x-www-form-urlencoded')) {
        headers['Content-Type'] = 'application/x-www-form-urlencoded';
        // Convert body to URLSearchParams
        if (req.method !== 'GET' && req.method !== 'HEAD' && req.body) {
          const formData = new URLSearchParams();
          Object.entries(req.body).forEach(([key, value]) => {
            formData.append(key, value as string);
          });
          body = formData;
        }
      } else {
        // Default to JSON
        headers['Content-Type'] = req.headers['content-type'] as string || 'application/json';
        body = req.method !== 'GET' && req.method !== 'HEAD' ? JSON.stringify(req.body) : undefined;
      }
      
      // Forward the request to the backend
      const response = await fetch(url, {
        method: req.method,
        headers,
        body,
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
      res.status(500).json({ 
        error: 'Error connecting to backend service', 
        details: error instanceof Error ? error.message : 'Unknown error' 
      });
    }
  } catch (error) {
    console.error('API proxy error:', error);
    res.status(500).json({ error: 'Internal Server Error' });
  }
}
