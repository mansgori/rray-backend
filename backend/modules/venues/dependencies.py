from fastapi import Depends
from backend.modules.venues.repository import VenueRepository
from backend.modules.venues.service import VenuesService

def get_user_service(
    venues_repo: VenueRepository = Depends(),
) -> VenuesService:
    return VenuesService(venues_repo)