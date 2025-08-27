from fastapi import APIRouter, Depends, HTTPException

from ..auth import get_current_user_id
from ..models import Profile, ProfileUpdate
from ..repositories import profile_repo


router = APIRouter(prefix="/me", tags=["profile"])


@router.get("/profile", response_model=Profile)
def get_my_profile(user_id: str = Depends(get_current_user_id)):
    row = profile_repo.get_profile(user_id)
    if not row:
        raise HTTPException(status_code=404, detail="Profile not found")
    return row


@router.put("/profile", response_model=Profile)
def update_my_profile(payload: ProfileUpdate, user_id: str = Depends(get_current_user_id)):
    row = profile_repo.upsert_profile(user_id, payload.model_dump())
    return row
