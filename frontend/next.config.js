/** @type {import('next').NextConfig} */
const nextConfig = {
  // Required for Docker/Railway deployment
  output: 'standalone',

  // Proxy API calls to FastAPI backend during development
  // In production, NEXT_PUBLIC_API_URL points to the backend service
  async rewrites() {
    if (process.env.NODE_ENV === 'development') {
      return [
        {
          source: '/api/:path*',
          destination: 'http://localhost:8000/api/:path*',
        },
      ];
    }
    return [];
  },
};

module.exports = nextConfig;
