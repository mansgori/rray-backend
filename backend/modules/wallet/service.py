from fastapi import Request, HTTPException
from typing import Dict, Any, Optional
from datetime import datetime, timezone, timedelta

import uuid
from backend.modules.auth.repository import AuthRepository
from backend.modules.wallet.repository import WalletRepository
from backend.modules.users.repository import UserRepository
from backend.modules.listing.repository import ListingRepository
from backend.modules.partner.repository import PartnerRepository
from backend.modules.sessions.repository import SessionRepository
from backend.modules.booking.repository import BookingRepository
from backend.modules.invoice.repository import InvoiceRepository
from backend.modules.wallet.models import CreditLedger, PlanSubscribeRequest, Wallet





class WalletService:
    def __init__(self, 
                 auth_repo: AuthRepository,
                 wallet_repo:WalletRepository,
                 user_repo:UserRepository,
                 listing_repo:ListingRepository,
                 partner_repo:PartnerRepository,
                 session_repo:SessionRepository,
                 booking_repo:BookingRepository,
                 invoice_repo:InvoiceRepository
                 ):
        self.auth_repo = auth_repo
        self.wallet_repo = wallet_repo
        self.user_repo = user_repo
        self.listing_repo = listing_repo
        self.partner_repo = partner_repo
        self.session_repo = session_repo
        self.booking_repo = booking_repo
        self.invoice_repo = invoice_repo


    async def get_credit_plans(self):
        plans = await self.wallet_repo.get_credit_plans()
        return {"plans": plans}


    async def subscribe_plan(self, request: PlanSubscribeRequest, current_user: Dict):
        if current_user["role"] != "customer":
            raise HTTPException(status_code=403, detail="Only customers can subscribe")
        
        plan = await self.wallet_repo.get_credit_plans_by_id(id= request.plan_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")
        
        # Mock payment
        payment_txn_id = f"mock_plan_{uuid.uuid4().hex[:12]}"
        
        # Grant credits
        await self.wallet_repo.grant_wallet_creadit(
            id=current_user["id"], 
            credit_balance=plan["credits_per_month"], 
            time=datetime.now(timezone.utc))        
        # Log ledger
        ledger_entry = CreditLedger(
            user_id=current_user["id"],
            delta=plan["credits_per_month"],
            reason="purchase"
        )
        await self.wallet_repo.create_credit_ledger(creadit_leadger=ledger_entry)
        
        return {"message": f"Subscribed to {plan['name']}", "credits_granted": plan["credits_per_month"]}


    async def get_wallet(self, current_user: Dict):
        wallet = await self.wallet_repo.find_wallet_by_id(id=current_user["id"])
        if not wallet:
            # Create if missing
            wallet = Wallet(user_id=current_user["id"])
            await self.wallet_repo.create_wallet(wallet=wallet)
        return wallet


    async def get_ledger(self, current_user: Dict):
        ledger = await self.wallet_repo.get_credit_ledger_by_id(id=current_user["id"])
        return {"ledger": ledger}


    async def activate_wallet(self, bonus_credits, current_user):
        """Activate wallet with bonus credits for new users"""
        wallet = await self.wallet_repo.find_wallet_by_id(id=current_user["id"])
        
        if not wallet:
            # Create wallet with bonus
            wallet = Wallet(
                user_id=current_user["id"],
                credits_balance=bonus_credits,
                cash_balance_inr=0.0
            )
            await self.wallet_repo.create_wallet(wallet=wallet)
            
            # Create ledger entry for bonus
            ledger_entry = CreditLedger(
                user_id=current_user["id"],
                delta=bonus_credits,
                reason="welcome_bonus",
                description=f"Welcome to rayy! {bonus_credits} bonus credits"
            )
            await self.wallet_repo.create_credit_ledger(creadit_leadger=ledger_entry)
            
            return {"message": "Wallet activated", "bonus_credits": bonus_credits}
        else:
            # Wallet already exists, just add bonus if not already given
            existing_bonus = await self.wallet_repo.get_credit_ledger_by_id(id=current_user["id"])
            # "reason": "welcome_bonus"
            # If some error add thois in query
            
            if not existing_bonus:
                # Add bonus
                await self.wallet_repo.grant_wallet_creadit(id=current_user["id"], credit_balance=bonus_credits, time=datetime.now(timezone.utc))
                
                ledger_entry = CreditLedger(
                    user_id=current_user["id"],
                    delta=bonus_credits,
                    reason="welcome_bonus",
                    description=f"Welcome to rayy! {bonus_credits} bonus credits"
                )
                await self.wallet_repo.create_credit_ledger(creadit_leadger=ledger_entry)
                
                return {"message": "Bonus credits added", "bonus_credits": bonus_credits}
            else:
                return {"message": "Wallet already activated", "bonus_credits": 0}