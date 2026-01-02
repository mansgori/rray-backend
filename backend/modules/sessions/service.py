from fastapi import Request, HTTPException
from typing import Dict, Any
from typing import Optional
from datetime import datetime, timezone, timedelta
import os
import logging
from backend.modules.auth.repository import AuthRepository
from backend.modules.wallet.repository import WalletRepository
from backend.modules.users.repository import UserRepository
from backend.modules.listing.repository import ListingRepository
from backend.modules.partner.repository import PartnerRepository
from backend.modules.sessions.repository import SessionRepository
from backend.core.email_service.email_instance import email_service
from backend.modules.listing.utility import calculate_distance_km, format_distance

class SessionService:
    def __init__(self, 
                 session_repo:SessionRepository
                 ):
        self.session_repo = session_repo
    
    async def get_document_count(self):
        document_count = await self.session_repo.get_document_count()
        return document_count