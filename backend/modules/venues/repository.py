from backend.core.database import mongodb

class VenueRepository:
    async def get_venue_by_id(self, id):
        return await mongodb.db.find_one({"id": id}, {"_id": 0})
    