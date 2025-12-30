from fastapi import APIRouter, Depends
from typing import Optional, Dict, Any, List
from backend.modules.users.schemas import ChildProfile
from backend.modules.users.dependencies import get_user_service
from backend.modules.auth.utility import get_current_user
from backend.modules.users.service import UserService

user_router = APIRouter(prefix="/user", tags=["User"])

@user_router.put("/me")
async def update_user_profile(
    child_profiles: Optional[List[ChildProfile]] = None,
    preferences: Optional[Dict[str, Any]] = None,
    current_user: Dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    return await user_service.update_profile(
        current_user=current_user,
        child_profiles=child_profiles,
        preferences=preferences,
    )