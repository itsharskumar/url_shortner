import secrets
import string
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from bson import ObjectId
from bson.errors import InvalidId

from auth_utils import get_current_user_id
from database import format_datetime, get_db, to_utc

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


def get_unique_short_code(db, length: int = 6) -> str:
    for _ in range(20):
        candidate = generate_short_code(length=length)
        found = db.urls.find_one({"short_code": candidate}, {"_id": 1})
        if not found:
            return candidate
    raise RuntimeError("Could not generate a unique short code")


@router.post("/shorten")
def shorten_url(
    payload: ShortenRequest,
    request: Request,
    db=Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
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
        existing = db.urls.find_one({"short_code": short_code}, {"_id": 1})
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
        expires_at = to_utc(parsed_expiry)

    db.urls.insert_one(
        {
            "original_url": payload.original_url,
            "short_code": short_code,
            "clicks": 0,
            "created_at": datetime.now(timezone.utc),
            "user_id": current_user_id,
            "expires_at": expires_at,
        }
    )

    base_url = str(request.base_url).rstrip("/")
    return {
        "message": "Short URL created successfully",
        "original_url": payload.original_url,
        "short_code": short_code,
        "expires_at": format_datetime(expires_at),
        "short_url": f"{base_url}/{short_code}",
    }


@router.get("/urls")
def get_all_urls(
    db=Depends(get_db), current_user_id: str = Depends(get_current_user_id)
):
    docs = db.urls.find({"user_id": current_user_id}).sort("created_at", -1)
    results = []
    for doc in docs:
        results.append(
            {
                "id": str(doc["_id"]),
                "original_url": doc["original_url"],
                "short_code": doc["short_code"],
                "clicks": doc.get("clicks", 0),
                "created_at": format_datetime(doc.get("created_at")),
                "expires_at": format_datetime(doc.get("expires_at")),
            }
        )
    return results


@router.get("/urls/top")
def get_top_clicked_urls(
    limit: int = 5,
    db=Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    safe_limit = max(1, min(limit, 50))
    docs = (
        db.urls.find({"user_id": current_user_id})
        .sort([("clicks", -1), ("created_at", -1)])
        .limit(safe_limit)
    )
    results = []
    for doc in docs:
        results.append(
            {
                "id": str(doc["_id"]),
                "original_url": doc["original_url"],
                "short_code": doc["short_code"],
                "clicks": doc.get("clicks", 0),
                "created_at": format_datetime(doc.get("created_at")),
                "expires_at": format_datetime(doc.get("expires_at")),
            }
        )
    return results


@router.delete("/urls/{url_id}")
def delete_url(
    url_id: str,
    db=Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
) -> dict[str, Any]:
    try:
        object_id = ObjectId(url_id)
    except InvalidId:
        raise HTTPException(status_code=404, detail="URL entry not found")

    result = db.urls.delete_one({"_id": object_id, "user_id": current_user_id})

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="URL entry not found")

    return {"message": "URL deleted successfully"}


@router.get("/analytics/summary")
def analytics_summary(
    db=Depends(get_db), current_user_id: str = Depends(get_current_user_id)
):
    totals_pipeline = [
        {"$match": {"user_id": current_user_id}},
        {"$group": {"_id": None, "total_urls": {"$sum": 1}, "total_clicks": {"$sum": "$clicks"}}},
    ]
    totals_doc = next(db.urls.aggregate(totals_pipeline), None)

    top_urls = list(
        db.urls.find(
            {"user_id": current_user_id},
            {"short_code": 1, "original_url": 1, "clicks": 1},
        )
        .sort([("clicks", -1), ("created_at", -1)])
        .limit(5)
    )

    daily_links_pipeline = [
        {"$match": {"user_id": current_user_id}},
        {
            "$group": {
                "_id": {
                    "$dateToString": {
                        "format": "%Y-%m-%d",
                        "date": "$created_at",
                        "timezone": "UTC",
                    }
                },
                "links_created": {"$sum": 1},
            }
        },
        {"$sort": {"_id": -1}},
    ]
    daily_links = list(db.urls.aggregate(daily_links_pipeline))

    return {
        "totals": {
            "total_urls": totals_doc.get("total_urls", 0) if totals_doc else 0,
            "total_clicks": totals_doc.get("total_clicks", 0) if totals_doc else 0,
        },
        "top_urls": [
            {
                "short_code": item["short_code"],
                "original_url": item["original_url"],
                "clicks": item.get("clicks", 0),
            }
            for item in top_urls
        ],
        "links_per_day": [
            {"day": item["_id"], "links_created": item["links_created"]}
            for item in daily_links
        ],
    }


@router.get("/analytics/top")
def analytics_top_urls(
    limit: int = 5,
    db=Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    safe_limit = max(1, min(limit, 50))
    docs = (
        db.urls.find(
            {"user_id": current_user_id},
            {"short_code": 1, "original_url": 1, "clicks": 1, "created_at": 1},
        )
        .sort([("clicks", -1), ("created_at", -1)])
        .limit(safe_limit)
    )
    return [
        {
            "short_code": doc["short_code"],
            "original_url": doc["original_url"],
            "clicks": doc.get("clicks", 0),
            "created_at": format_datetime(doc.get("created_at")),
        }
        for doc in docs
    ]


@router.get("/analytics/daily")
def analytics_links_per_day(
    db=Depends(get_db), current_user_id: str = Depends(get_current_user_id)
):
    daily_links_pipeline = [
        {"$match": {"user_id": current_user_id}},
        {
            "$group": {
                "_id": {
                    "$dateToString": {
                        "format": "%Y-%m-%d",
                        "date": "$created_at",
                        "timezone": "UTC",
                    }
                },
                "links_created": {"$sum": 1},
            }
        },
        {"$sort": {"_id": -1}},
    ]
    docs = list(db.urls.aggregate(daily_links_pipeline))
    return [{"day": doc["_id"], "links_created": doc["links_created"]} for doc in docs]
