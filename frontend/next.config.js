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
        source: '/api/v1/media/stream/:id',
        destination: 'http://localhost:8000/api/v1/media/stream/:id',
      },
    ];
  },
};

module.exports = nextConfig;
