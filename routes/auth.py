from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from auth_utils import create_access_token, hash_password, verify_password
from database import get_db

router = APIRouter(prefix="/auth", tags=["Authentication"])


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


@router.post("/register")
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.execute(
        text("SELECT id FROM users WHERE email = :email LIMIT 1"),
        {"email": payload.email},
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email is already registered")

    password_hash = hash_password(payload.password)
    db.execute(
        text(
            """
            INSERT INTO users (email, password_hash)
            VALUES (:email, :password_hash)
            """
        ),
        {"email": payload.email, "password_hash": password_hash},
    )
    db.commit()

    return {"message": "User registered successfully"}


@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.execute(
        text(
            """
            SELECT id, email, password_hash
            FROM users
            WHERE email = :email
            LIMIT 1
            """
        ),
        {"email": payload.email},
    ).mappings().first()

    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    access_token = create_access_token(subject=user["email"])
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {"id": user["id"], "email": user["email"]},
    }
