import { NextApiRequest, NextApiResponse } from 'next';

/**
 * API proxy for clips endpoint
 * This avoids CORS issues by proxying requests through Next.js
 */
export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  const token = req.headers.authorization || '';
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
  
  console.log('API Proxy: Forwarding request to clips endpoint');
  console.log('Request method:', req.method);
  console.log('Request body:', JSON.stringify(req.body));
  
  try {
    // Forward the request to the backend API
    const backendUrl = `${apiUrl}/clips`;
    console.log('Forwarding to backend URL:', backendUrl);
    
    const response = await fetch(backendUrl, {
      method: req.method,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': token
      },
      body: req.method !== 'GET' ? JSON.stringify(req.body) : undefined,
    });
    
    console.log('Backend response status:', response.status);
    
    // Get the response data
    let data;
    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      data = await response.json();
      console.log('Backend response data:', JSON.stringify(data));
    } else {
      const text = await response.text();
      console.log('Backend response text:', text);
      data = { message: text };
    }
    
    // Forward the status code and data back to the client
    res.status(response.status).json(data);
  } catch (error: any) {
    console.error('API proxy error:', error);
    res.status(500).json({ 
      error: 'Failed to proxy request to API', 
      details: error.message 
    });
  }
}
