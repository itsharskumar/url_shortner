from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field

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
def register(payload: RegisterRequest, db=Depends(get_db)):
    existing = db.users.find_one({"email": payload.email}, {"_id": 1})
    if existing:
        raise HTTPException(status_code=400, detail="Email is already registered")

    password_hash = hash_password(payload.password)
    db.users.insert_one(
        {
            "email": payload.email,
            "password_hash": password_hash,
            "created_at": datetime.now(timezone.utc),
        }
    )

    return {"message": "User registered successfully"}


@router.post("/login")
def login(payload: LoginRequest, db=Depends(get_db)):
    user = db.users.find_one(
        {"email": payload.email},
        {"email": 1, "password_hash": 1},
    )

    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    access_token = create_access_token(subject=user["email"])
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {"id": str(user["_id"]), "email": user["email"]},
    }
