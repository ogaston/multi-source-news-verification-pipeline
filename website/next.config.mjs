const apiBase = (process.env.WEBSITE_API_URL || 'http://localhost:7002').replace(
  /\/$/,
  ''
)

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  images: {
    // Cover images may still use absolute localhost/API URLs in local/dev.
    // Next.js 16 blocks optimizing private IPs unless this is enabled.
    dangerouslyAllowLocalIP: true,
    remotePatterns: [
      { protocol: 'https', hostname: '**' },
      { protocol: 'http', hostname: '**' },
      { protocol: 'http', hostname: 'localhost', port: '7002', pathname: '/media/**' },
      { protocol: 'http', hostname: '127.0.0.1', port: '7002', pathname: '/media/**' },
      { protocol: 'http', hostname: 'api', port: '7002', pathname: '/media/**' },
    ],
    minimumCacheTTL: 3600,
  },
  async rewrites() {
    return [
      {
        source: '/media/:path*',
        destination: `${apiBase}/media/:path*`,
      },
    ]
  },
}

export default nextConfig
