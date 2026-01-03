from fastapi import APIRouter, Depends, Request
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from backend.modules.auth.utility import get_current_user
from backend.modules.booking.schemas import BookingCreateV2, BookingCreate, PlanBookingCreate
from backend.modules.booking.models import RescheduleRequest
from backend.modules.booking.service import BookingService
from backend.modules.booking.dependecies import get_booking_service

booking_router = APIRouter(prefix="/bookings", tags=["Booking"])

@booking_router.post("/")
async def create_booking(
    data: BookingCreate, 
    current_user: Dict = Depends(get_current_user),
    booking_service: BookingService = Depends(get_booking_service)
    ):
    return await booking_service.create_booking(data, current_user)

@booking_router.post("bookings/v2")
async def create_booking_v2(
    booking_data: BookingCreateV2,
    current_user: Dict = Depends(get_current_user),
    booking_service: BookingService = Depends(get_booking_service)

):
    return await booking_service.create_booking_v2(booking_data, current_user)

@booking_router.get("/listings/{listing_id}/booking-options")
async def get_booking_options(
    listing_id: str,
    booking_service: BookingService = Depends(get_booking_service)
    ):
    return await booking_service.get_booking_options(listing_id)

@booking_router.get("/trial-eligibility/{listing_id}")
async def check_trial_eligibility(
    listing_id: str, 
    current_user: Dict = Depends(get_current_user),
    booking_service: BookingService = Depends(get_booking_service)
    ):
    return await booking_service.check_trial_eligibility(listing_id, current_user)

@booking_router.post("/plan")
async def create_plan_booking(
    data: PlanBookingCreate, 
    current_user: Dict = Depends(get_current_user),
    booking_service: BookingService = Depends(get_booking_service)):
        return await booking_service.create_plan_booking(data=data, current_user=current_user)

@booking_router.get("/my")
async def get_my_bookings(
    current_user: Dict = Depends(get_current_user),
    booking_service: BookingService = Depends(get_booking_service)):
        return await booking_service.get_my_bookings(current_user=current_user)

@booking_router.post("/{booking_id}/cancel")
async def cancel_booking(
      booking_id: str, 
      reason: Optional[str] = None, 
      current_user: Dict = Depends(get_current_user),
      booking_service: BookingService = Depends(get_booking_service)
      ):
        return await booking_service.cancel_booking(booking_id, reason, current_user)

@booking_router.post("/{booking_id}/reschedule")
async def reschedule_booking(
    booking_id: str, 
    request: RescheduleRequest,
    current_user: Dict = Depends(get_current_user),
    booking_service: BookingService = Depends(get_booking_service)
    ):
      return await booking_service.reschedule_booking(booking_id, request, current_user)


# Unable to Attend endpoints
@booking_router.post("/{booking_id}/unable-to-attend")
async def mark_unable_to_attend(
    booking_id: str,
    reason: str,
    custom_note: Optional[str] = None,
    session_id: Optional[str] = None,
    current_user: Dict = Depends(get_current_user),
    booking_service: BookingService = Depends(get_booking_service)
):
     return await booking_service.mark_unable_to_attend(booking_id, reason, custom_note, session_id, current_user)

@booking_router.get("/bookings/{booking_id}/unable-to-attend-history")
async def get_unable_to_attend_history(
    booking_id: str,
    current_user: Dict = Depends(get_current_user),
    booking_service: BookingService = Depends(get_booking_service)
):
    return await booking_service.get_unable_to_attend_history(booking_id, current_user)

@booking_router.get("/bookings/{booking_id}/available-sessions")
async def get_available_sessions_for_reschedule(
    booking_id: str,
    current_user: Dict = Depends(get_current_user),
    booking_service: BookingService = Depends(get_booking_service)
):
    return await booking_service.get_available_sessions_for_reschedule(booking_id, current_user)

