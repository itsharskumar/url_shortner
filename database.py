import os

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, declarative_base, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./shortener.db")

engine_options = {}
if DATABASE_URL.startswith("sqlite"):
    engine_options["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, **engine_options)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS urls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    original_url TEXT NOT NULL,
                    short_code TEXT NOT NULL UNIQUE,
                    clicks INTEGER NOT NULL DEFAULT 0,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    user_id INTEGER,
                    expires_at DATETIME,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                );
                """
            )
        )
        # Backward-compatible migrations for existing databases.
        url_columns = {
            row["name"]
            for row in conn.execute(text("PRAGMA table_info(urls)")).mappings().all()
        }
        if "user_id" not in url_columns:
            conn.execute(text("ALTER TABLE urls ADD COLUMN user_id INTEGER"))
        if "expires_at" not in url_columns:
            conn.execute(text("ALTER TABLE urls ADD COLUMN expires_at DATETIME"))

        conn.execute(
            text("CREATE INDEX IF NOT EXISTS idx_urls_user_id ON urls(user_id);")
        )
        conn.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_urls_short_code ON urls(short_code);"
            )
        )
