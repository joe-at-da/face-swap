// Next.js API route support: https://nextjs.org/docs/api-routes/introduction

export default async function handler(req, res) {
  try {
    // Log the request details
    console.log('Debug API route called');
    console.log('Method:', req.method);
    console.log('URL:', req.url);
    console.log('Headers:', req.headers);
    
    // Try to make a direct request to the backend
    const response = await fetch('http://localhost:8000/api/v1/health');
    const data = await response.json();
    
    // Return the response
    res.status(200).json({
      message: 'Debug API route',
      backendResponse: data,
      requestDetails: {
        method: req.method,
        url: req.url,
        headers: req.headers,
      }
    });
  } catch (error) {
    console.error('Error in debug API route:', error);
    res.status(500).json({ 
      error: error.message,
      stack: error.stack
    });
  }
}
