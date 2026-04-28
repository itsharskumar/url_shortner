from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from database import get_db, init_db
from routes.api import router as api_router
from routes.auth import router as auth_router
from routes.pages import router as pages_router

app = FastAPI(title="FastAPI URL Shortener", version="1.0.0")

app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(pages_router)
app.include_router(auth_router)
app.include_router(api_router)


@app.on_event("startup")
def startup_event() -> None:
    init_db()


@app.get("/{short_code}")
def redirect_to_original(short_code: str, db=Depends(get_db)):
    url_doc = db.urls.find_one({"short_code": short_code})

    if not url_doc:
        raise HTTPException(status_code=404, detail="Short URL not found")

    expires_at = url_doc.get("expires_at")
    if expires_at and expires_at <= datetime.now(timezone.utc):
        return HTMLResponse(
            "<h2>Link expired</h2><p>This short URL is no longer active.</p>",
            status_code=410,
        )

    db.urls.update_one({"_id": url_doc["_id"]}, {"$inc": {"clicks": 1}})

    return RedirectResponse(url=url_doc["original_url"], status_code=307)
