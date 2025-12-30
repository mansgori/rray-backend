from backend.modules.auth.repository import AuthRepository
from backend.modules.wallet.repository import WalletRepository
from backend.modules.users.repository import UserRepository
from typing import Optional
from datetime import datetime, timezone

class UserService:
    def __init__(self, 
                 auth_repo: AuthRepository,
                 wallet_repo:WalletRepository,
                 user_repo:UserRepository
                 ):
        self.auth_repo = auth_repo
        self.wallet_repo = wallet_repo
        self.user_repo = user_repo

    async def update_profile(
        self,
        current_user: dict,
        child_profiles: Optional[list],
        preferences: Optional[dict],
    ):
        update_data = {}

        if child_profiles is not None:
            update_data["child_profiles"] = [
                cp.model_dump() if hasattr(cp, "model_dump") else cp
                for cp in child_profiles
            ]

        if preferences is not None:
            update_data["preferences"] = preferences

        if not update_data:
            return {"message": "Nothing to update"}

        update_data["updated_at"] = datetime.now(timezone.utc)

        await self.user_repo.update_user_by_id(
            current_user["id"],
            update_data
        )

        return {"message": "Profile updated successfully"}