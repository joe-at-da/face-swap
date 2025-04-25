import { NextApiRequest, NextApiResponse } from 'next';

/**
 * API proxy specifically for the login endpoint
 * This handles the OAuth2 form data format correctly
 */
export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  try {
    if (req.method !== 'POST') {
      return res.status(405).json({ error: 'Method not allowed' });
    }

    // Get the credentials from the request body
    const { email, password } = req.body;

    // Create form data for OAuth2 login
    const formData = new URLSearchParams();
    formData.append('username', email); // OAuth2 expects 'username' even though we're using email
    formData.append('password', password);

    // Construct the backend URL
    // When running in Docker, we need to use the correct service name
    // This is a critical part - we need to use the Docker service name when inside Docker
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
    
    console.log('Backend URL:', backendUrl);
    const url = `${backendUrl}/api/v1/auth/login`;

    console.log('Sending request to:', url);
    
    try {
      // Forward the request to the backend
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: formData,
      });
      
      console.log('Response status:', response.status);
      
      // Get the response data
      const data = await response.json().catch(e => {
        console.error('Error parsing JSON response:', e);
        return { error: 'Invalid JSON response' };
      });
      
      console.log('Response data:', data);
      
      // Set the response status code
      res.status(response.status);
      
      // Send the response
      return res.json(data);
    } catch (error) {
      console.error('Fetch error:', error);
      return res.status(500).json({ 
        error: 'Error connecting to backend service', 
        details: error instanceof Error ? error.message : 'Unknown error' 
      });
    }

    // This code won't be reached due to the return statement in the try block
  } catch (error) {
    console.error('Login proxy error:', error);
    res.status(500).json({ error: 'Internal Server Error' });
  }
}
