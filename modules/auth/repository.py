from ...core.config import mongodb
from ..users.models import User
from ..auth.schemas import UserRegister

class AuthRepository:
    async def user_exists(self, email: str) -> bool:
        return await mongodb.db.users.find_one({"email":email}) is not None
    
    async def create_user(self, user:UserRegister):
        return await mongodb.db.users.insert_one(user.model_dump())