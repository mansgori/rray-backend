from fastapi import Request, HTTPException
from typing import Dict, Any
from typing import Optional
from datetime import datetime, timezone
import os
import logging
from backend.modules.venues.repositiry import VenueRepository
from backend.core.email_service.email_instance import email_service



class UserService:
    def __init__(self, 
                    venue_repo: VenueRepository,
                 ):
        self.venue_repo = venue_repo

    async def get_venue_details(self, venue_id: str):
        venue = await self.venue_repo.get_venue_by_id(venue_id)
        if not venue:
            raise HTTPException(status_code=404, detail="Venue not found")
        return venue