from fastapi import Depends
from backend.modules.booking.repository import BookingRepository
from backend.modules.booking.service import BookingService

def get_booking_service(
    booking_repo: BookingRepository = Depends(),
) -> BookingService:
    return BookingService(booking_repo)