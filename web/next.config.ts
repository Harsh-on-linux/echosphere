import path from 'node:path'
import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
  // Enable React strict mode
  reactStrictMode: true,
  turbopack: {
    root: path.resolve(__dirname, '..'),
  },

  // Optimize images
  images: {
    unoptimized: true,
  },

  async rewrites() {
    const backendUrl = process.env.AGENT_BACKEND_URL?.replace(/\/$/, '')
    if (!backendUrl) {
      return []
    }

    return [
      {
        source: '/api/get_config',
        destination: `${backendUrl}/get_config`,
      },
      {
        source: '/api/startAgent',
        destination: `${backendUrl}/startAgent`,
      },
      {
        source: '/api/stopAgent',
        destination: `${backendUrl}/stopAgent`,
      },
      {
        source: '/api/interruptAgent',
        destination: `${backendUrl}/interruptAgent`,
      },
      {
        source: '/api/agentHistory',
        destination: `${backendUrl}/agentHistory`,
      },
      {
        source: '/api/agentTurns',
        destination: `${backendUrl}/agentTurns`,
      },
      {
        source: '/api/cycloneMap',
        destination: `${backendUrl}/cycloneMap`,
      },
      {
        source: '/api/dial',
        destination: `${backendUrl}/dial`,
      },
      {
        source: '/api/hangup',
        destination: `${backendUrl}/hangup`,
      },
      {
        source: '/api/telephonyStatus',
        destination: `${backendUrl}/telephonyStatus`,
      },
      {
        source: '/api/token',
        destination: `${backendUrl}/api/token`,
      },
      {
        source: '/api/health',
        destination: `${backendUrl}/health`,
      },
      {
        source: '/health',
        destination: `${backendUrl}/health`,
      },
      {
        source: '/api/:path*',
        destination: `${backendUrl}/api/:path*`,
      },
    ]
  },
}

export default nextConfig
