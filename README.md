# FastAPI URL Shortener

A beginner-friendly, resume-ready URL shortener project built with FastAPI, SQLite, SQL-focused queries, and a simple Jinja2 frontend.

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

- POST /shorten
- GET /{short_code}
- GET /urls
- DELETE /urls/{id}
- GET /urls/top?limit=5

## 5) SQL Queries Used (Core Focus)

1. Insert URL:

INSERT INTO urls (original_url, short_code, clicks)
VALUES (:original_url, :short_code, 0)

Purpose: saves a new long URL with generated short code and initial click count.

2. Update click count:

UPDATE urls SET clicks = clicks + 1 WHERE id = :id

Purpose: increments clicks every time someone opens a short URL.

3. Fetch all URLs:

SELECT id, original_url, short_code, clicks, created_at
FROM urls
ORDER BY created_at DESC

Purpose: fills dashboard table with latest entries first.

4. Fetch top clicked URLs:

SELECT id, original_url, short_code, clicks, created_at
FROM urls
ORDER BY clicks DESC, created_at DESC
LIMIT :limit

Purpose: analytics view showing most popular links.

## 6) Browser + Swagger Testing

Home page testing:

1. Open home page.
2. Enter a URL like https://www.python.org.
3. Click Shorten URL.
4. Open generated short URL and verify redirect works.

Dashboard testing:

1. Open dashboard.
2. Verify row appears with clicks and created time.
3. Click short URL multiple times and refresh dashboard to verify click increments.
4. Test delete button.

Swagger testing:

1. Open /docs.
2. Test POST /shorten with body:
{
  "original_url": "https://fastapi.tiangolo.com"
}
3. Test GET /urls.
4. Test DELETE /urls/{id}.
5. Test GET /urls/top.

## 7) Render Deployment (Step-by-Step)

1. Push this project to GitHub.
2. Sign in to Render and click New + > Web Service.
3. Connect your GitHub repo.
4. Use these settings:
   - Environment: Python
   - Build Command: pip install -r requirements.txt
   - Start Command: uvicorn app:app --host 0.0.0.0 --port 10000
5. Add environment variable (optional):
   - PYTHON_VERSION = 3.11.9
6. Click Create Web Service.
7. After deploy completes, open the Render URL and test:
   - /
   - /dashboard
   - /docs

Note: SQLite on Render may reset if the service restarts, because filesystem can be ephemeral on free plans. For production, move to a managed database.
