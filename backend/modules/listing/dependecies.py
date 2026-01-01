from fastapi import Depends
from backend.modules.listing.repository import ListingRepository
from backend.modules.listing.service import ListingService

def get_listing_service(
    user_repo: ListingRepository = Depends(),
) -> ListingService:
    return ListingService(user_repo)