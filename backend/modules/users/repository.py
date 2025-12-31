from backend.core.database import mongodb

class UserRepository:
    async def update_user_by_id(self, id, data):
        return await mongodb.db.update_one(
        {"id": id},
        {"$set": data}
    )