from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.orm import Session

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
def redirect_to_original(short_code: str, db: Session = Depends(get_db)):
    row = db.execute(
        text(
            """
            SELECT id, original_url, expires_at
            FROM urls
            WHERE short_code = :short_code
            LIMIT 1
            """
        ),
        {"short_code": short_code},
    ).mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail="Short URL not found")

    expiry_check = db.execute(
        text(
            """
            SELECT CASE
                WHEN expires_at IS NOT NULL AND expires_at <= CURRENT_TIMESTAMP THEN 1
                ELSE 0
            END AS is_expired
            FROM urls
            WHERE id = :id
            """
        ),
        {"id": row["id"]},
    ).mappings().first()
    if expiry_check and expiry_check["is_expired"]:
        return HTMLResponse(
            "<h2>Link expired</h2><p>This short URL is no longer active.</p>",
            status_code=410,
        )

    db.execute(
        text("UPDATE urls SET clicks = clicks + 1 WHERE id = :id"),
        {"id": row["id"]},
    )
    db.commit()

    return RedirectResponse(url=row["original_url"], status_code=307)
