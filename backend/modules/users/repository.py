from backend.core.database import mongodb

class UserRepository:
    async def update_user_by_id(self, id, data):
        return await mongodb.db.update_one(
        {"id": id},
        {"$set": data}
    )
    async def get_user_detail_by_partner_id(self, partner_id):
        return await mongodb.db.find_one(
        {"id": partner_id, "role": "partner"}, 
        {"_id": 0, "name": 1, "email": 1, "city": 1, "badges": 1}
    )