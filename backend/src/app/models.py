from typing import Optional
from pydantic import BaseModel, Field


class Profile(BaseModel):
    id: str
    display_name: Optional[str] = None
    time_zone: str = Field(default="UTC")


class ProfileUpdate(BaseModel):
    display_name: Optional[str] = None
    time_zone: Optional[str] = None

