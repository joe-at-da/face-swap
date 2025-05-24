/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/api/:path*',
      },
      {
        source: '/media/stream/:id',
        destination: 'http://localhost:8000/api/v1/media/stream/:id',
      },
      {
        source: '/api/videos/stream-with-token/:filename',
        destination: 'http://localhost:8000/api/v1/videos/stream-with-token/:filename',
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
