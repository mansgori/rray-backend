from fastapi import APIRouter, Depends, Request
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from backend.modules.users.schemas import ChildProfile
from backend.modules.listing.dependecies import get_listing_service
from backend.modules.auth.utility import get_current_user
from backend.modules.listing.service import ListingService
from backend.modules.listing.schemas import PlanOptionCreate, BatchCreate

list_router = APIRouter(prefix="/listing", tags=["Listing"])
category_router = APIRouter(tags=["categories"])

@category_router.get("/categories")
async def get_categories(
    listing_service: ListingService = Depends(get_listing_service)
):
     return await listing_service.get_categories()

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
     return await listing_service.search_listings(
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
     return await listing_service.get_my_listings(current_user)

@list_router.get("/{listing_id}")
async def get_listing_by_id(
    listing_id: str,
    listing_service: ListingService = Depends(get_listing_service)
):
     return await listing_service.get_listing_by_id(listing_id)

# @list_router.get("/listings/{listing_id}/sessions") #pending

@list_router.get("/listings/{listing_id}/plans")
async def get_listing_plans(listing_id: str, listing_service: ListingService = Depends(get_listing_service)):
     return await listing_service.get_listing_plans(listing_id)

@list_router.get("/listings/{listing_id}/v2")
async def get_listing_v2(listing_id: str, listing_service: ListingService = Depends(get_listing_service)):
     return await listing_service.get_listing_by_id(listing_id)

@list_router.put("/listings/{listing_id}/v2")
async def update_listing_v2(
    listing_id: str,
    data: Dict[str, Any],
    current_user: Dict = Depends(get_current_user),
    listing_service: ListingService = Depends(get_listing_service)
):
     return await listing_service.update_listing(listing_id, data, current_user)

@list_router.post("/listings/{listing_id}/plan-options")
async def add_plan_option(
    listing_id: str,
    plan: PlanOptionCreate,
    current_user: Dict = Depends(get_current_user),
    listing_service: ListingService = Depends(get_listing_service)
):
     return await listing_service.add_plan_option(listing_id, plan, current_user)

@list_router.put("/listings/{listing_id}/plan-options/{plan_id}")
async def update_plan_option(
    listing_id: str,
    plan_id: str,
    plan_data: Dict[str, Any],
    current_user: Dict = Depends(get_current_user),
    listing_service: ListingService = Depends(get_listing_service)
    ):
     return await listing_service.update_plan_option(listing_id, plan_id, plan_data, current_user)

@list_router.delete("/listings/{listing_id}/plan-options/{plan_id}")
async def delete_plan_option(
    listing_id: str,
    plan_id: str,
    current_user: Dict = Depends(get_current_user),
    listing_service: ListingService = Depends(get_listing_service)
    ):
         return await listing_service.delete_plan_option(listing_id, plan_id, current_user)

@list_router.post("/listings/{listing_id}/batches")
async def add_batch(
    listing_id: str,
    batch: BatchCreate,
    current_user: Dict = Depends(get_current_user),
    listing_service: ListingService = Depends(get_listing_service)
):
     return await listing_service.add_batch(listing_id, batch, current_user)

@list_router.put("/listings/{listing_id}/batches/{batch_id}")
async def update_batch(
    listing_id: str,
    batch_id: str,
    batch_data: Dict[str, Any],
    current_user: Dict = Depends(get_current_user),
    listing_service: ListingService = Depends(get_listing_service)
):
     return await listing_service.update_batch(listing_id, batch_id, batch_data, current_user)

@list_router.delete("/listings/{listing_id}/batches/{batch_id}")
async def delete_batch(
    listing_id: str,
    batch_id: str,
    current_user: Dict = Depends(get_current_user),
    listing_service: ListingService = Depends(get_listing_service)
):
     return await listing_service.delete_batch(listing_id, batch_id, current_user)

@list_router.get("/listings/{listing_id}/batches/{batch_id}/availability")
async def check_batch_availability(
    listing_id: str, 
    batch_id: str, 
    listing_service: ListingService = Depends(get_listing_service)):
         return await listing_service.check_batch_availability(listing_id, batch_id)

@list_router.post("/listings/{listing_id}/batches/{batch_id}/generate-sessions")
async def generate_batch_sessions(
    listing_id: str,
    batch_id: str,
    weeks: int = 12,
    current_user: Dict = Depends(get_current_user),
    listing_service: ListingService = Depends(get_listing_service)
):
      return await listing_service.generate_batch_sessions(listing_id, batch_id, weeks, current_user)

@list_router.get("/listings/{listing_id}/batches/{batch_id}/sessions")
async def get_batch_sessions(
    listing_id: str,
    batch_id: str,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    listing_service: ListingService = Depends(get_listing_service)
):
      return await listing_service.get_batch_sessions(listing_id, batch_id, from_date, to_date)