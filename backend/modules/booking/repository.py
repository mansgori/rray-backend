from backend.core.database import mongodb
from backend.modules.booking.models import Booking

class BookingRepository:
        async def add_booking(self, booking_doc: Booking):
            return await mongodb.db.bookings.insert_one(booking_doc.model_dump())
        
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