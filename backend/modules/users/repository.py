from backend.core.database import mongodb

class UserRepository:
    async def user_exists(self, email: str) -> bool:
        return await mongodb.db.users.find_one({"email":email}) is not None