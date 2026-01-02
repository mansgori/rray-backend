from fastapi import Depends
from backend.modules.listing.repository import ListingRepository
from backend.modules.listing.service import ListingService

def get_listing_service(
    listing_repo: ListingRepository = Depends(),
) -> ListingService:
    return ListingService(listing_repo)