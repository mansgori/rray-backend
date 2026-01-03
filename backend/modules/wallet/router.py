from fastapi import APIRouter, Depends, Request
from typing import Dict
from backend.modules.auth.utility import get_current_user
from backend.modules.wallet.dependencies import get_wallet_service
from backend.modules.wallet.service import WalletService
from backend.modules.wallet.models import  PlanSubscribeRequest


plans_router = APIRouter(prefix="/credit-plans", tags=["Credit-Plans"])
wallet_router = APIRouter(prefix="/wallet", tags=["Wallet"])


@plans_router.get("/")
async def get_credit_plans(wallet_service: WalletService = Depends(get_wallet_service)):
    return await wallet_service.get_credit_plans()

@plans_router.post("/subscribe")
async def subscribe_plan(
    request: PlanSubscribeRequest, 
    current_user: Dict = Depends(get_current_user),
    wallet_service: WalletService = Depends(get_wallet_service)):
    return await wallet_service.subscribe_plan(request, current_user)

@wallet_router.get("/me")
async def get_wallet(
    current_user: Dict = Depends(get_current_user), 
    wallet_service: WalletService = Depends(get_wallet_service)):
    return await wallet_service.get_wallet(current_user)

@wallet_router.get("/ledger")
async def get_ledger(    
    current_user: Dict = Depends(get_current_user), 
    wallet_service: WalletService = Depends(get_wallet_service)):
    return await wallet_service.get_ledger(current_user)

@wallet_router.post("/activate")
async def activate_wallet(
    bonus_credits: int = 10, 
    current_user: Dict = Depends(get_current_user),
    wallet_service: WalletService = Depends(get_wallet_service)):
    return await wallet_service.activate_wallet(bonus_credits, current_user)