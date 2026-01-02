from fastapi import Request, HTTPException
from typing import Dict, Any
from typing import Optional
from datetime import datetime, timezone, timedelta
import os
import logging
import uuid
from backend.modules.auth.repository import AuthRepository
from backend.modules.wallet.repository import WalletRepository
from backend.modules.users.repository import UserRepository
from backend.modules.listing.repository import ListingRepository
from backend.modules.partner.repository import PartnerRepository
from backend.modules.sessions.repository import SessionRepository
from backend.modules.booking.repository import BookingRepository
from backend.modules.invoice.repository import InvoiceRepository
from backend.modules.wallet.models import CreditLedger
from backend.modules.booking.models import Booking, BookingStatus




class InvoiceService:
    def __init__(self, 
                 auth_repo: AuthRepository,
                 wallet_repo:WalletRepository,
                 user_repo:UserRepository,
                 listing_repo:ListingRepository,
                 partner_repo:PartnerRepository,
                 session_repo:SessionRepository,
                 booking_repo:BookingRepository,
                 invoice_repo: InvoiceRepository
                 ):
        self.auth_repo = auth_repo
        self.wallet_repo = wallet_repo
        self.user_repo = user_repo
        self.listing_repo = listing_repo
        self.partner_repo = partner_repo
        self.session_repo = session_repo
        self.booking_repo = booking_repo
        self.invoice_repo = invoice_repo