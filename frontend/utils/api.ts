/**
 * API client for communicating with the backend
 */

// Determine the correct API URL based on environment
let API_BASE_URL = 'http://localhost:8000/api/v1';

// Always use localhost when running in browser
if (typeof window !== 'undefined') {
  API_BASE_URL = 'http://localhost:8000/api/v1';
}

console.log('API Base URL:', API_BASE_URL);

class ApiClient {
  private token: string | null = null;

  constructor() {
    // Initialize token from storage when the client is created
    if (typeof window !== 'undefined') {
      const storedToken = localStorage.getItem('token') || sessionStorage.getItem('token');
      if (storedToken) {
        this.token = storedToken;
        console.log('API token initialized from storage');
      }
    }
  }
  
  /**
   * Get the current authentication token
   */
  getToken(): string | null {
    return this.token;
  }

  /**
   * Set the authentication token for API requests
   */
  setAuthToken(token: string | null) {
    this.token = token;
    console.log('API token set:', token ? 'Present' : 'None');
  }

  /**
   * Get the authentication headers
   */
  private getHeaders(): HeadersInit {
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    return headers;
  }

  /**
   * Handle API response
   */
  private async handleResponse(response: Response) {
    // Log all responses for debugging
    console.log(`API response: ${response.status} for ${response.url}`);
    
    if (!response.ok) {
      console.warn(`API error: ${response.status} for ${response.url}`);
      
      // Handle 401 Unauthorized - could be expired token
      if (response.status === 401) {
        // Check if this is a non-critical endpoint that shouldn't trigger logout
        const url = new URL(response.url);
        const isNonCriticalEndpoint = 
          url.pathname.includes('/clips') || 
          url.pathname.includes('/social-media') ||
          url.pathname.includes('/capture') ||
          url.pathname.includes('/social') ||
          url.pathname.includes('/admin');
        
        // If we're not on the login page, we might need to refresh the token or redirect to login
        if (typeof window !== 'undefined' && window.location.pathname !== '/login') {
          console.warn('Authentication error: Token may be expired');
          
          // For non-critical endpoints, don't clear token or redirect
          if (isNonCriticalEndpoint) {
            console.log('Non-critical endpoint 401 error, not clearing token');
            // Just return null for this endpoint
            return null;
          }
          
          // Only clear token and redirect if we're not in the process of logging in
          // and if we haven't suppressed auth redirects
          if (!sessionStorage.getItem('loggingIn') && !sessionStorage.getItem('suppressAuthRedirect')) {
            console.log('Clearing token due to 401 error');
            // Clear token and redirect to login
            localStorage.removeItem('token');
            this.token = null;
            
            // Redirect to login page
            window.location.href = '/login';
            return null; // Return early
          } else if (sessionStorage.getItem('suppressAuthRedirect')) {
            console.log('Auth redirect suppressed for this request');
            // Clear the flag after using it
            sessionStorage.removeItem('suppressAuthRedirect');
          }
        }
      }
      
      // Try to parse error response
      try {
        // First try to get the response as text
        const responseText = await response.text();
        
        // Then try to parse as JSON if possible
        try {
          const errorData = JSON.parse(responseText);
          console.error('API error details:', errorData);
          throw new Error(errorData.detail || `API error: ${response.status}`);
        } catch (parseError) {
          // If not JSON, use the raw text
          console.error('API error response:', responseText);
          throw new Error(responseText || `API error: ${response.status}`);
        }
      } catch (error) {
        console.error('Failed to parse error response:', error);
        throw new Error(`API error: ${response.status}`);
      }
    }

    // Check if response is empty
    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      return await response.json();
    }

    return null;
  }

  /**
   * Make a GET request
   */
  async get(endpoint: string, params?: Record<string, any>) {
    const url = new URL(`${API_BASE_URL}${endpoint}`);
    
    // Add query parameters
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          url.searchParams.append(key, String(value));
        }
      });
    }

    try {
      console.log(`Fetching ${url.toString()} with token:`, this.token ? 'Present' : 'None');
      
      // Add special debug logging for capture endpoints
      if (endpoint.includes('/capture')) {
        console.log(`[CAPTURE DEBUG] Fetching capture endpoint: ${endpoint}`);
      }
      
      const response = await fetch(url.toString(), {
        method: 'GET',
        headers: this.getHeaders(),
        // Don't include credentials when using wildcard origins
        // credentials: 'include',
      });

      console.log(`Response for ${endpoint}:`, response.status);
      
      // Add special debug logging for capture endpoints
      if (endpoint.includes('/capture')) {
        console.log(`[CAPTURE DEBUG] Response status for ${endpoint}: ${response.status}`);
      }
      
      const result = await this.handleResponse(response);
      
      // Add special debug logging for capture endpoints
      if (endpoint.includes('/capture')) {
        console.log(`[CAPTURE DEBUG] Response data for ${endpoint}:`, result);
      }
      
      return result;
    } catch (error) {
      console.error(`Network error fetching ${endpoint}:`, error);
      
      // Add special debug logging for capture endpoints
      if (endpoint.includes('/capture')) {
        console.error(`[CAPTURE DEBUG] Error fetching ${endpoint}:`, error);
      }
      
      throw error;
    }
  }

  /**
   * Make a POST request
   */
  async post(endpoint: string, data?: any) {
    // Add special debug logging for capture endpoints
    if (endpoint.includes('/capture')) {
      console.log(`[CAPTURE DEBUG] POST request to ${endpoint}`, data ? 'with data' : 'without data');
      if (data) {
        console.log(`[CAPTURE DEBUG] POST data:`, data);
      }
    }
    
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: data ? JSON.stringify(data) : undefined,
      // Don't include credentials when using wildcard origins
      // credentials: 'include',
    });

    // Add special debug logging for capture endpoints
    if (endpoint.includes('/capture')) {
      console.log(`[CAPTURE DEBUG] POST response status for ${endpoint}: ${response.status}`);
    }
    
    const result = await this.handleResponse(response);
    
    // Add special debug logging for capture endpoints
    if (endpoint.includes('/capture')) {
      console.log(`[CAPTURE DEBUG] POST response data for ${endpoint}:`, result);
    }
    
    return result;
  }

  /**
   * Make a PUT request
   */
  async put(endpoint: string, data?: any) {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method: 'PUT',
      headers: this.getHeaders(),
      body: data ? JSON.stringify(data) : undefined,
      // Don't include credentials when using wildcard origins
      // credentials: 'include',
    });

    return this.handleResponse(response);
  }

  /**
   * Make a PATCH request
   */
  async patch(endpoint: string, data?: any) {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method: 'PATCH',
      headers: this.getHeaders(),
      body: data ? JSON.stringify(data) : undefined,
      // Don't include credentials when using wildcard origins
      // credentials: 'include',
    });

    return this.handleResponse(response);
  }

  /**
   * Make a DELETE request
   */
  async delete(endpoint: string) {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method: 'DELETE',
      headers: this.getHeaders(),
      // Don't include credentials when using wildcard origins
      // credentials: 'include',
    });

    return this.handleResponse(response);
  }

  /**
   * Upload a file
   */
  async uploadFile(endpoint: string, file: File, additionalData?: Record<string, any>) {
    const formData = new FormData();
    formData.append('file', file);

    // Add additional data
    if (additionalData) {
      Object.entries(additionalData).forEach(([key, value]) => {
        formData.append(key, String(value));
      });
    }

    const headers: HeadersInit = {};
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method: 'POST',
      headers,
      body: formData,
      // Don't include credentials when using wildcard origins
      // credentials: 'include',
    });

    return this.handleResponse(response);
  }
}

// Create and export API client instance
export const api = new ApiClient();
