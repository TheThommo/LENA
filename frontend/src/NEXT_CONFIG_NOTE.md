# Next.js Configuration Notes for Railway Deployment

## Required Configuration

The `next.config.js` file needs to be updated with the following configuration for Docker/Railway deployment:

### 1. Add `output: 'standalone'` setting

This is required for the Docker multi-stage build to work properly. The Dockerfile expects the Next.js build output to be in standalone mode, which creates a minimal production build that can run without the full node_modules directory.

```javascript
const nextConfig = {
  output: 'standalone',
  // ... rest of config
};
```

### 2. API Proxy Strategy

Currently, `next.config.js` includes rewrites that proxy `/api/*` to `http://localhost:8000/api/*` for local development:

```javascript
async rewrites() {
  return [
    {
      source: '/api/:path*',
      destination: 'http://localhost:8000/api/:path*',
    },
  ];
}
```

**Development mode**: This works fine for local testing.

**Production (Railway)**: This rewrite should either be:
- Removed (recommended), or
- Conditionally applied only in development

In production, the frontend should communicate directly with the backend service URL provided via the `NEXT_PUBLIC_API_URL` environment variable. The Railway backend service will have its own public URL or internal service URL.

### Environment Variables for Railway

Set these in the Railway deployment:
- `NEXT_PUBLIC_API_URL`: The full URL to the FastAPI backend (e.g., `https://lena-backend.up.railway.app/api` or internal Railway service URL)
- `NEXT_PUBLIC_APP_ENV`: Set to `production`

### Conditional Rewrites Pattern (Optional)

If you want to keep rewrites only for development:

```javascript
const nextConfig = {
  output: 'standalone',
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
```

See `src/lib/config.ts` for helper functions to check the current environment and retrieve API URLs.
