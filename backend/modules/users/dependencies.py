from fastapi import Depends
from backend.modules.users.repository import UserRepository
from backend.modules.users.service import UserService

def get_user_service(
    user_repo: UserRepository = Depends(),
) -> UserService:
    return UserService(user_repo)