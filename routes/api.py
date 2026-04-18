import secrets
import string
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from auth_utils import get_current_user_id
from database import get_db

router = APIRouter(tags=["URL API"])


class ShortenRequest(BaseModel):
    original_url: str = Field(..., examples=["https://example.com/very/long/path"])
    custom_code: str | None = Field(default=None, min_length=3, max_length=32)
    expires_at: str | None = Field(
        default=None, examples=["2026-12-31T23:59:59"]
    )


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
def shorten_url(
    payload: ShortenRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    if not is_valid_http_url(payload.original_url):
        raise HTTPException(status_code=400, detail="Please provide a valid http or https URL")

    short_code = payload.custom_code.strip() if payload.custom_code else None
    if short_code:
        if not short_code.replace("-", "").replace("_", "").isalnum():
            raise HTTPException(
                status_code=400,
                detail="Custom short code can contain only letters, numbers, '-' and '_'",
            )
        existing = db.execute(
            text("SELECT id FROM urls WHERE short_code = :short_code LIMIT 1"),
            {"short_code": short_code},
        ).first()
        if existing:
            raise HTTPException(status_code=409, detail="Custom short code is already taken")
    else:
        short_code = get_unique_short_code(db)

    expires_at = None
    if payload.expires_at:
        try:
            parsed_expiry = datetime.fromisoformat(payload.expires_at)
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail="Invalid expires_at format. Use ISO format like 2026-12-31T23:59:59",
            ) from exc
        expires_at = parsed_expiry.strftime("%Y-%m-%d %H:%M:%S")

    db.execute(
        text(
            """
            INSERT INTO urls (original_url, short_code, clicks, user_id, expires_at)
            VALUES (:original_url, :short_code, 0, :user_id, :expires_at)
            """
        ),
        {
            "original_url": payload.original_url,
            "short_code": short_code,
            "user_id": current_user_id,
            "expires_at": expires_at,
        },
    )
    db.commit()

    base_url = str(request.base_url).rstrip("/")
    return {
        "message": "Short URL created successfully",
        "original_url": payload.original_url,
        "short_code": short_code,
        "expires_at": expires_at,
        "short_url": f"{base_url}/{short_code}",
    }


@router.get("/urls")
def get_all_urls(
    db: Session = Depends(get_db), current_user_id: int = Depends(get_current_user_id)
):
    rows = db.execute(
        text(
            """
            SELECT id, original_url, short_code, clicks, created_at, expires_at
            FROM urls
            WHERE user_id = :user_id
            ORDER BY created_at DESC
            """
        ),
        {"user_id": current_user_id},
    ).mappings().all()
    return [dict(row) for row in rows]


@router.get("/urls/top")
def get_top_clicked_urls(
    limit: int = 5,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    safe_limit = max(1, min(limit, 50))
    rows = db.execute(
        text(
            """
            SELECT id, original_url, short_code, clicks, created_at, expires_at
            FROM urls
            WHERE user_id = :user_id
            ORDER BY clicks DESC, created_at DESC
            LIMIT :limit
            """
        ),
        {"limit": safe_limit, "user_id": current_user_id},
    ).mappings().all()
    return [dict(row) for row in rows]


@router.delete("/urls/{url_id}")
def delete_url(
    url_id: int,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
) -> dict[str, Any]:
    result = db.execute(
        text("DELETE FROM urls WHERE id = :id AND user_id = :user_id"),
        {"id": url_id, "user_id": current_user_id},
    )
    db.commit()

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="URL entry not found")

    return {"message": "URL deleted successfully"}


@router.get("/analytics/summary")
def analytics_summary(
    db: Session = Depends(get_db), current_user_id: int = Depends(get_current_user_id)
):
    totals = db.execute(
        text(
            """
            SELECT COUNT(*) AS total_urls, COALESCE(SUM(clicks), 0) AS total_clicks
            FROM urls
            WHERE user_id = :user_id
            """
        ),
        {"user_id": current_user_id},
    ).mappings().first()

    top_urls = db.execute(
        text(
            """
            SELECT short_code, original_url, clicks
            FROM urls
            WHERE user_id = :user_id
            ORDER BY clicks DESC, created_at DESC
            LIMIT 5
            """
        ),
        {"user_id": current_user_id},
    ).mappings().all()

    daily_links = db.execute(
        text(
            """
            SELECT DATE(created_at) AS day, COUNT(*) AS links_created
            FROM urls
            WHERE user_id = :user_id
            GROUP BY DATE(created_at)
            ORDER BY day DESC
            """
        ),
        {"user_id": current_user_id},
    ).mappings().all()

    return {
        "totals": dict(totals) if totals else {"total_urls": 0, "total_clicks": 0},
        "top_urls": [dict(item) for item in top_urls],
        "links_per_day": [dict(item) for item in daily_links],
    }


@router.get("/analytics/top")
def analytics_top_urls(
    limit: int = 5,
    db: Session = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id),
):
    safe_limit = max(1, min(limit, 50))
    rows = db.execute(
        text(
            """
            SELECT short_code, original_url, clicks, created_at
            FROM urls
            WHERE user_id = :user_id
            ORDER BY clicks DESC, created_at DESC
            LIMIT :limit
            """
        ),
        {"user_id": current_user_id, "limit": safe_limit},
    ).mappings().all()
    return [dict(row) for row in rows]


@router.get("/analytics/daily")
def analytics_links_per_day(
    db: Session = Depends(get_db), current_user_id: int = Depends(get_current_user_id)
):
    rows = db.execute(
        text(
            """
            SELECT DATE(created_at) AS day, COUNT(*) AS links_created
            FROM urls
            WHERE user_id = :user_id
            GROUP BY DATE(created_at)
            ORDER BY day DESC
            """
        ),
        {"user_id": current_user_id},
    ).mappings().all()
    return [dict(row) for row in rows]
