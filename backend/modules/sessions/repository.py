from backend.core.database import mongodb

class SessionRepository:
    async def add_session(self, session_doc):
        return await mongodb.db.sessions.insert_one(session_doc)
    
    async def update_session(self, session_id):
        return await mongodb.db.sessions.update_one(
                    {"id": session_id},
                    {"$inc": {"seats_booked": 1}}
                )
    
    async def atomic_seat_reservation(self, session_id, seats_total):
        return await mongodb.db.update_one(
                {
                    "id": session_id,
                    "seats_booked": {"$lt": seats_total}
                },
                {"$inc": {"seats_booked": 1}}
            )
    
    async def get_session(self, query):
         return await mongodb.db.sessions.find(query, {"_id": 0}).sort("date", 1).to_list(500)
    
    async def get_session_by_id(self, session_id):
         return await mongodb.db.sessions.find({"id": session_id}, {"_id": 0})
    
    async def session_belong_to_listing(self, session_ids):
        return await mongodb.db.session.find(
        {"id": {"$in": session_ids}},
        {"_id": 0}
    ).to_list(100)
    
    async def get_document_count(self, listing_id, date ):
        return await mongodb.db.sessions.count_documents({
            "listing_id": listing_id,
            "status": "scheduled",
            "date": {"$gte": date}
            })