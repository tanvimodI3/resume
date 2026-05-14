# Deployment Options & Preparation Plan

This document outlines the best options to deploy your Full-Stack ATS application (Vite/React frontend + FastAPI/PostgreSQL/Redis backend) and the necessary code changes required to make it production-ready.

## User Review Required

> [!IMPORTANT]
> Please review the deployment options below and let me know which path you prefer. 
> Once you approve, I will proceed with making the necessary code changes to prepare your repository for deployment.

### Option 1: Managed Platform (Recommended for ease of use)
- **Frontend:** Vercel or Netlify (Free, fast global edge network, automatic GitHub deployments).
- **Backend:** Render (Easy Python deployments).
- **Database & Cache:** Render or Railway (Managed PostgreSQL and Redis).
**Pros:** Easy setup, automatic SSL/HTTPS, CI/CD out of the box.
**Cons:** Can become expensive if traffic scales, separate dashboards to manage.

### Option 2: Single Virtual Private Server (VPS) with Docker
- **Host:** AWS EC2, DigitalOcean Droplet, Hetzner, or Linode.
- **Method:** We update your existing `docker-compose.yml` to include the frontend (served via Nginx) and the FastAPI backend.
**Pros:** Very cost-effective (run everything on a $5-$10/mo server), full control, single deployment command.
**Cons:** Requires manual server setup and SSL configuration (using Traefik or Certbot).

## Proposed Changes
To get the code ready for *any* of the above deployment options, we need to remove hardcoded `localhost` references and make the application configurable via Environment Variables.

### Frontend

#### [MODIFY] `frontend/src/components/*.jsx`
- Replace hardcoded backend API URLs (e.g., `http://localhost:8000`) with a dynamic environment variable `import.meta.env.VITE_API_URL`.

#### [NEW] `frontend/.env`
- Add default local fallback: `VITE_API_URL=http://localhost:8000`.

### Backend

#### [MODIFY] `backend/main.py`
- Update `CORSMiddleware` to read allowed origins from the `FRONTEND_URL` environment variable, rather than hardcoding `http://localhost:5173`. This ensures your backend will accept requests from your production frontend URL.

#### [MODIFY] `backend/redis_client.py`
- Change `host="localhost"` to use `os.getenv("REDIS_HOST", "localhost")` and `os.getenv("REDIS_PORT", 6379)` so it can connect to Redis in a Docker or production environment.

## Verification Plan

### Manual Verification
1. I will write the necessary code changes to use environment variables.
2. I will instruct you on how to start the app locally using the new `.env` setup to verify that authentication, API calls, and the Redis cache still work perfectly.
3. Once verified, the codebase will be ready for you to deploy to your chosen platform!
