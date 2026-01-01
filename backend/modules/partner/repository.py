from backend.core.database import mongodb

class PartnerRepository:
    async def get_partner_by_id(self, id):
        return await mongodb.db.partners.find_one({"owner_user_id": id}, {"_id": 0})