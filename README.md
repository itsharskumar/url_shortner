# FastAPI URL Shortener

A beginner-friendly, resume-ready URL shortener project built with FastAPI, MongoDB, JWT auth, and a simple Jinja2 frontend.

## 1) Project Structure

- app.py
- database.py
- models.py
- routes/
- templates/
- static/

## 2) Install Dependencies

Create and activate a virtual environment, then install packages:

Windows PowerShell:

python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

## 3) Run Server

Create a .env file (or export env vars) with:

- SECRET_KEY
- MONGODB_URI
- MONGODB_DB

uvicorn app:app --reload

Open:

- Home: http://127.0.0.1:8000/
- Dashboard: http://127.0.0.1:8000/dashboard
- Swagger docs: http://127.0.0.1:8000/docs

## 4) API Endpoints

- POST /auth/register
- POST /auth/login
- POST /shorten
- GET /{short_code}
- GET /urls
- DELETE /urls/{id}
- GET /urls/top?limit=5
- GET /analytics/summary
- GET /analytics/top?limit=5
- GET /analytics/daily

## 5) MongoDB Collections + Fields

Two collections are used:

1. users
- email: string (unique)
- password_hash: string
- created_at: datetime (UTC)

2. urls
- original_url: string
- short_code: string (unique)
- clicks: number
- created_at: datetime (UTC)
- user_id: string (user _id as string)
- expires_at: datetime | null

## 6) Browser + Swagger Testing

Authentication testing:

1. Open /auth.
2. Register with email + password.
3. Login and verify token-based access works.

Home page testing:

1. Open home page.
2. Enter URL like https://www.python.org.
3. (Optional) Enter custom short code.
4. (Optional) Set expiry date/time.
5. Click Shorten URL.
6. Open generated short URL and verify redirect works.

Dashboard testing:

1. Open dashboard.
2. Verify only your URLs are visible.
3. Verify expiry status column shows Active/Expired.
4. Verify analytics cards show totals, top URLs, and links/day.
3. Click short URL multiple times and refresh dashboard to verify click increments.
4. Test delete button.

Swagger testing:

1. Open /docs.
2. Test POST /auth/register, then /auth/login and copy access_token.
3. Click Authorize and paste: Bearer <token>
4. Test POST /shorten with body:
{
   "original_url": "https://fastapi.tiangolo.com",
   "custom_code": "my-fastapi-link",
   "expires_at": "2030-12-31T23:59:59"
}
5. Test GET /urls.
6. Test DELETE /urls/{id}.
7. Test GET /analytics/summary, /analytics/top, /analytics/daily.

## 7) Render Deployment (Step-by-Step)

Option A (recommended): One-click blueprint deploy using render.yaml

1. Keep render.yaml in project root.
2. Push code to GitHub.
3. In Render, click New + > Blueprint.
4. Select this repository.
5. Render will auto-read render.yaml and create service + disk + env vars.

Option B: Manual web service setup

1. Push this project to GitHub.
2. Sign in to Render and click New + > Web Service.
3. Connect your GitHub repo.
4. Use these settings:
   - Environment: Python
   - Build Command: pip install -r requirements.txt
   - Start Command: uvicorn app:app --host 0.0.0.0 --port 10000
5. Add environment variable (required for MongoDB):
   - PYTHON_VERSION = 3.11.9
   - SECRET_KEY = your-long-random-secret
   - MONGODB_URI = mongodb://user:password@host:27017
   - MONGODB_DB = shortener
6. Click Create Web Service.
7. After deploy completes, open the Render URL and test:
   - /
   - /dashboard
   - /docs

Note: This project now supports MongoDB via MONGODB_URI and MONGODB_DB.

## 8) Session Expiry Behavior

- Frontend now checks JWT expiry on every protected action.
- If token is expired, user is logged out automatically and redirected to /auth.
- If API returns 401, session is cleared and user is redirected to login.
