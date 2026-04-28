from datetime import datetime

from bson import ObjectId
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserDoc(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: ObjectId | str = Field(alias="_id")
    email: EmailStr
    password_hash: str
    created_at: datetime


class UrlDoc(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: ObjectId | str = Field(alias="_id")
    original_url: str
    short_code: str
    clicks: int = 0
    created_at: datetime
    user_id: str
    expires_at: datetime | None = None
