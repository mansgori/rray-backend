from backend.core.database import mongodb
from backend.modules.booking.models import Booking

class BookingRepository:
        
        async def find_booking(self, bookind_id: str):
              return await mongodb.db.bookings.find_one({"id":bookind_id})
        
        async def find_bookings(self, id: str):
              return await mongodb.db.bookings.find({"user_id": id}, {"_id": 0}).sort("booked_at", -1).to_list(100)
        

        async def add_booking(self, booking_doc: Booking):
            return await mongodb.db.bookings.insert_one(booking_doc.model_dump())
        
        async def update_booking(self, booking_id, update_data ):
              return await mongodb.db.bookings.update_one(
            {"id": booking_id},
            {
                "$set": update_data
            })
        async def update_booking_after_rescheduling(self, booking_id, update_data, inc_data):
              return await mongodb.db.bookings.update_one(
            {"id": booking_id},
            {
                "$set": update_data,
                "$inc":inc_data
            })
        
        async def check_trial_booking_this_week(self, id, date):
            return await mongodb.db.bookings.count_documents({
                    "user_id": id,
                    "is_trial": True,
                    "booked_at": {"$gte": date}
                })
        
        async def eligible_for_trial_booking(self, id, listing_id):
              return await mongodb.db.bookings.insert_one({
                    "user_id": id,
                    "listing_id": listing_id,
                    "is_trial": True
                })
        
        async def find_unable_to_attend_by_id(self, unable_to_attend_id):
              return await mongodb.db.unable_to_attend.find(
                {"booking_id": unable_to_attend_id},
                {"_id": 0}
            ).sort("created_at", -1).to_list(100)
        
        async def unable_to_attend(self, unable_to_attend_data):
              return await mongodb.db.unable_to_attend.insert_one(unable_to_attend_data)
        
        async def update_unable_to_attend(self, id, update_data):
              return await mongodb.db.unable_to_attend.update_one(
                {"id": id},
                {"$set": update_data}
            )