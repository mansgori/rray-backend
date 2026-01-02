from fastapi import APIRouter, Depends, Request
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from backend.modules.auth.utility import get_current_user
from backend.modules.booking.schemas import BookingCreateV2, BookingCreate
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

