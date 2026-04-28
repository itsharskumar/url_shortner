import os
from datetime import datetime, timezone

from pymongo import ASCENDING, DESCENDING, MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DB = os.getenv("MONGODB_DB", "shortener")

client = MongoClient(MONGODB_URI)
db = client[MONGODB_DB]


def to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def format_datetime(value: datetime | None) -> str | None:
    if not value:
        return None
    return to_utc(value).isoformat()


def get_db():
    yield db


def init_db() -> None:
    db.users.create_index([("email", ASCENDING)], unique=True)
    db.urls.create_index([("short_code", ASCENDING)], unique=True)
    db.urls.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])
    db.urls.create_index([("user_id", ASCENDING), ("clicks", DESCENDING)])
