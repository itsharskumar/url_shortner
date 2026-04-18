import secrets
import string
from typing import Any
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from database import get_db

router = APIRouter(tags=["URL API"])


class ShortenRequest(BaseModel):
    original_url: str = Field(..., examples=["https://example.com/very/long/path"])


def is_valid_http_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def generate_short_code(length: int = 6) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def get_unique_short_code(db: Session, length: int = 6) -> str:
    for _ in range(20):
        candidate = generate_short_code(length=length)
        found = db.execute(
            text("SELECT id FROM urls WHERE short_code = :short_code LIMIT 1"),
            {"short_code": candidate},
        ).first()
        if not found:
            return candidate
    raise RuntimeError("Could not generate a unique short code")


@router.post("/shorten")
def shorten_url(payload: ShortenRequest, request: Request, db: Session = Depends(get_db)):
    if not is_valid_http_url(payload.original_url):
        raise HTTPException(status_code=400, detail="Please provide a valid http or https URL")

    short_code = get_unique_short_code(db)

    db.execute(
        text(
            """
            INSERT INTO urls (original_url, short_code, clicks)
            VALUES (:original_url, :short_code, 0)
            """
        ),
        {"original_url": payload.original_url, "short_code": short_code},
    )
    db.commit()

    base_url = str(request.base_url).rstrip("/")
    return {
        "message": "Short URL created successfully",
        "original_url": payload.original_url,
        "short_code": short_code,
        "short_url": f"{base_url}/{short_code}",
    }


@router.get("/urls")
def get_all_urls(db: Session = Depends(get_db)):
    rows = db.execute(
        text(
            """
            SELECT id, original_url, short_code, clicks, created_at
            FROM urls
            ORDER BY created_at DESC
            """
        )
    ).mappings().all()
    return [dict(row) for row in rows]


@router.get("/urls/top")
def get_top_clicked_urls(limit: int = 5, db: Session = Depends(get_db)):
    safe_limit = max(1, min(limit, 50))
    rows = db.execute(
        text(
            """
            SELECT id, original_url, short_code, clicks, created_at
            FROM urls
            ORDER BY clicks DESC, created_at DESC
            LIMIT :limit
            """
        ),
        {"limit": safe_limit},
    ).mappings().all()
    return [dict(row) for row in rows]


@router.delete("/urls/{url_id}")
def delete_url(url_id: int, db: Session = Depends(get_db)) -> dict[str, Any]:
    result = db.execute(text("DELETE FROM urls WHERE id = :id"), {"id": url_id})
    db.commit()

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="URL entry not found")

    return {"message": "URL deleted successfully"}
