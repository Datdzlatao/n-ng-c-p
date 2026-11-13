/** @type {import('next').NextConfig} */
const backendUrl = (process.env.NEXT_PUBLIC_API_URL || 'https://dat-latitude-5590-2.tail2bda46.ts.net:8443').replace(/\/+$/, '');
const faceApiUrl = (process.env.NEXT_PUBLIC_FACE_API_URL || 'https://dat-latitude-5590-2.tail2bda46.ts.net:10000').replace(/\/+$/, '');

const nextConfig = {
  reactStrictMode: false,
  async rewrites() {
    return [
      {
        source: '/api/v1/:path*',
        destination: `${faceApiUrl}/api/v1/:path*`,
      },
      {
        source: '/api/:path*',
        destination: `${backendUrl}/api/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
