# FastAPI URL Shortener

A beginner-friendly, resume-ready URL shortener project built with FastAPI, SQLite, SQL-focused queries, JWT auth, and a simple Jinja2 frontend.

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

## 5) SQL Queries Used (Core Focus)

1. Register user:

INSERT INTO users (email, password_hash)
VALUES (:email, :password_hash)

Purpose: creates an account and stores password hash.

2. Insert URL for a specific user:

INSERT INTO urls (original_url, short_code, clicks, user_id, expires_at)
VALUES (:original_url, :short_code, 0, :user_id, :expires_at)

Purpose: saves a URL owned by one user with optional expiry.

3. Update click count:

UPDATE urls SET clicks = clicks + 1 WHERE id = :id

Purpose: increments clicks every time someone opens a short URL.

4. Fetch only current user's URLs:

SELECT id, original_url, short_code, clicks, created_at, expires_at
FROM urls
WHERE user_id = :user_id
ORDER BY created_at DESC

Purpose: dashboard shows only the logged-in user's links.

5. Top 5 most clicked URLs (analytics):

SELECT short_code, original_url, clicks
FROM urls
WHERE user_id = :user_id
ORDER BY clicks DESC, created_at DESC
LIMIT :limit

Purpose: shows best performing links for one user.

6. Links created per day (GROUP BY analytics):

SELECT DATE(created_at) AS day, COUNT(*) AS links_created
FROM urls
WHERE user_id = :user_id
GROUP BY DATE(created_at)
ORDER BY day DESC

Purpose: daily creation trend for dashboard analytics.

7. Expiry check during redirect:

SELECT CASE
   WHEN expires_at IS NOT NULL AND expires_at <= CURRENT_TIMESTAMP THEN 1
   ELSE 0
END AS is_expired
FROM urls
WHERE id = :id

Purpose: block redirect if link has expired.

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
5. Add environment variable (optional):
   - PYTHON_VERSION = 3.11.9
   - SECRET_KEY = your-long-random-secret
   - DATABASE_URL = sqlite:////opt/render/project/src/data/shortener.db
6. Add a Persistent Disk:
   - Name: shortener-data
   - Mount Path: /opt/render/project/src/data
   - Size: 1 GB
6. Click Create Web Service.
7. After deploy completes, open the Render URL and test:
   - /
   - /dashboard
   - /docs

Note: This project now supports DATABASE_URL from environment, so moving to PostgreSQL later is straightforward.

## 8) Session Expiry Behavior

- Frontend now checks JWT expiry on every protected action.
- If token is expired, user is logged out automatically and redirected to /auth.
- If API returns 401, session is cleared and user is redirected to login.
