# LENA FastAPI Backend - Railway Deployment Guide

## Overview
This document describes how to deploy the LENA FastAPI backend to Railway.

## Files Created

### Core Deployment Files
1. **Dockerfile** - Docker container image definition
   - Python 3.11 slim base
   - Non-root user (appuser) for security
   - Health check built-in
   - Listens on PORT env var (Railway auto-injects this)

2. **.dockerignore** - Files excluded from Docker build
   - Excludes .env, venv/, __pycache__/, tests/, etc.
   - Keeps image lean and secure

3. **railway.toml** - Railway-specific configuration
   - Uses Dockerfile builder
   - Health check: GET /api/health
   - Restart policy: on-failure (max 5 retries)

4. **Procfile** - Process definition (backup/alternative)
   - Single web process running uvicorn
   - Uses PORT env var (Railway provides this)

5. **runtime.txt** - Python version specification
   - Python 3.11.10

## Configuration Updates

### app/core/config.py
Added Railway support:
- `app_port` now reads from PORT env var (Railway sets this)
- `railway_environment` field for Railway's RAILWAY_ENVIRONMENT var
- `is_production` property: checks if app_env == "production"
- `on_railway` property: checks if RAILWAY_ENVIRONMENT is set

### app/api/routes/health.py
Enhanced health check response:
- Added `environment` field (returns app_env value)
- Added `railway` field (returns True/False based on on_railway property)
- Helps verify deployment is working correctly

### .env.example
Added comments for Railway-specific env vars:
- PORT (auto-set by Railway)
- RAILWAY_ENVIRONMENT (auto-set by Railway)

## Deployment Steps

### 1. Prepare Railway Project
- Log in to https://railway.app
- Create a new project or use existing one
- Create a new service

### 2. Connect to GitHub
- Link your GitHub repository
- Select the LENA repo
- Choose the `backend/` directory as the root

### 3. Configure Environment Variables
In Railway dashboard, set these variables:
```
APP_ENV=production
APP_DEBUG=false
CORS_ORIGINS=https://your-frontend-domain.com
OPENAI_API_KEY=sk-...
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_ROLE_KEY=...
NCBI_API_KEY=...
NCBI_EMAIL=...
RATE_LIMIT_PER_MINUTE=60
```

Note: Do NOT set PORT or RAILWAY_ENVIRONMENT manually. Railway sets these automatically.

### 4. Deploy
- Railway will automatically detect the Dockerfile
- Build will start automatically
- Health check at /api/health will validate the service is running

### 5. Verify Deployment
After deployment, test these endpoints:
```
GET https://your-service.railway.app/
GET https://your-service.railway.app/api/health
GET https://your-service.railway.app/docs (API documentation)
```

## Health Check Endpoint Response

Example response from `/api/health`:
```json
{
  "status": "healthy",
  "service": "LENA API",
  "environment": "production",
  "railway": true
}
```

- `environment`: Shows app_env (development/production)
- `railway`: Shows if running on Railway infrastructure

## Docker Build Details

### Build Process
1. Installs system dependencies (gcc for some Python packages)
2. Installs Python dependencies from requirements.txt
3. Creates non-root user (appuser) for security
4. Copies application code
5. Exposes port 8000
6. Sets up health check

### Health Check
- Runs every 30 seconds
- 5 second startup grace period
- 3 retries before marking unhealthy
- Uses httpx to call /api/health endpoint

### Security
- Non-root user (UID 1000)
- No cache for pip install (keeps image size down)
- Minimal slim base image
- System dependencies cleaned up after install

## Environment Variables

### Railway Auto-Set
- `PORT` - Port to listen on (default 8000)
- `RAILWAY_ENVIRONMENT` - Set to "production" on Railway

### Required (Set in Railway Dashboard)
- `OPENAI_API_KEY`
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`
- `NCBI_API_KEY`
- `NCBI_EMAIL`

### Optional (Defaults Provided)
- `APP_ENV` - "production" recommended for Railway
- `APP_DEBUG` - false recommended for production
- `CORS_ORIGINS` - Add your frontend domain
- `RATE_LIMIT_PER_MINUTE` - Default 60

## Troubleshooting

### Port Binding Issues
The app listens on `0.0.0.0` on the PORT that Railway provides. If you see port errors, ensure:
- PORT env var is not hardcoded
- app_port reads from PORT env var (it does in updated config.py)

### Health Check Failures
If health check fails:
- Check the /api/health endpoint manually
- Ensure Supabase and OpenAI credentials are valid
- Check Railway logs for startup errors

### CORS Issues
If frontend gets CORS errors:
- Update CORS_ORIGINS in Railway environment
- Include your frontend domain (https://...)
- Don't use localhost in production

## Next Steps

1. Push code to GitHub
2. Create Railway project and link GitHub
3. Set environment variables in Railway dashboard
4. Monitor deployment in Railway dashboard
5. Test health endpoint after deployment
6. Configure frontend to call backend API

## Architecture Notes

This is a Docker-based deployment using Railway's container infrastructure.
- Frontend (Next.js) will be a separate Railway service
- Both services communicate via HTTP
- Database (Supabase) is external
- Third-party APIs (OpenAI, NCBI, etc.) are accessed via https
