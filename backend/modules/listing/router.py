from fastapi import APIRouter, Depends, Request
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from backend.modules.users.schemas import ChildProfile
from backend.modules.listing.dependecies import get_listing_service
from backend.modules.auth.utility import get_current_user
from backend.modules.listing.service import ListingService

list_router = APIRouter(prefix="/listing", tags=["Listing"])

APIRouter.get("/categories")
async def get_categories(
    listing_service: ListingService = Depends(get_listing_service)
):
    return listing_service.get_categories()

@list_router.get("/search")
async def search_listings(
    city: Optional[str] = None,
    age: Optional[int] = None,
    category: Optional[str] = None,
    date: Optional[str] = None,
    is_online: Optional[bool] = None,
    trial: Optional[bool] = None,
    lat: Optional[float] = None,
    lng: Optional[float] = None,
    radius_km: float = 10,
    skip: int = 0,
    limit: int = 60,
    listing_service: ListingService = Depends(get_listing_service)
):
    return listing_service.search_listings(
        city=city,
        age=age,
        category=category,
        date=date,
        is_online=is_online,
        trial=trial,
        lat=lat,
        lng=lng,
        radius_km=radius_km,
        skip=skip,
        limit=limit
    )

@list_router.get("/my")
async def get_my_listings(
    current_user: Dict = Depends(get_current_user),
    listing_service: ListingService = Depends(get_listing_service)):
    return listing_service.get_my_listings(current_user)

@list_router.get("/{listing_id}")
async def get_listing_by_id(
    listing_id: str,
    listing_service: ListingService = Depends(get_listing_service)
):
    return listing_service.get_listing_by_id(listing_id)

