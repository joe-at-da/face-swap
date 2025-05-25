/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    // Use Docker container name 'app' instead of 'localhost' for proper Docker networking
    return [
      {
        source: '/api/:path*',
        destination: 'http://app:8000/api/:path*',
      },
      {
        // Use our API route for media streaming to properly handle authentication
        source: '/media/stream/:id',
        destination: '/api/media/stream/:id',
      },
      {
        source: '/api/videos/stream-with-token/:filename',
        destination: 'http://app:8000/api/v1/videos/stream-with-token/:filename',
      },
    ];
  },
  // Add proper handling for Docker container paths
  async headers() {
    return [
      {
        source: '/media/stream/:id',
        headers: [
          {
            key: 'Cache-Control',
            value: 'no-cache, no-store, must-revalidate',
          },
        ],
      },
    ];
  },
};

module.exports = nextConfig;
