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
    // When running in Docker, use the service name 'app'
    const backendUrl = process.env.BACKEND_URL || 'http://app:8000';
    const url = `${backendUrl}/api/v1/auth/login`;

    // Forward the request to the backend
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: formData,
    });

    // Get the response data
    const data = await response.json().catch(() => ({}));

    // Set the response status code
    res.status(response.status);

    // Send the response
    res.json(data);
  } catch (error) {
    console.error('Login proxy error:', error);
    res.status(500).json({ error: 'Internal Server Error' });
  }
}
