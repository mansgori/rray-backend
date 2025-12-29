from fastapi import  APIRouter, Depends
from backend.modules.auth.schemas import TokenResponse
from backend.modules.users.schemas import UserLogin
from backend.modules.users.models import UserRegister
from backend.modules.auth.service import AuthService
from backend.modules.auth.repository import AuthRepository
from backend.modules.wallet.repository import WalletRepository

auth_router = APIRouter(prefix="/auth", tags=["Auth"])

def get_auth_service(
    auth_repo: AuthRepository = Depends(),
    wallet_repo: WalletRepository = Depends(),
) -> AuthService:
    return AuthService(
        auth_repo=auth_repo,
        wallet_repo=wallet_repo,
    )

@auth_router.post("/register", response_model=TokenResponse)
async def register(
    data: UserRegister,
    service: AuthService = Depends(get_auth_service)
    ):
    return await service.register(data)

@auth_router.post("/login", response_model=TokenResponse)
async def login(
    data: UserLogin,
    service: AuthService = Depends(get_auth_service)
    ):
    return await service.login(data)

@auth_router.post("/send-otp")
async def sendotp(
    data: dict,
    service: AuthService = Depends(get_auth_service)
    ):
    return await service.sendotp(data)

@auth_router.post("/check-partner-exists")
async def check_partner_exists(
    data: dict,
    service: AuthService = Depends(get_auth_service)
    ):
    return await service.check_partner_exists(data)

@auth_router.post("/verify-otp", response_model=TokenResponse)
async def verifyotp(
    data: dict,
    service: AuthService = Depends(get_auth_service)
    ):
    return await service.verifyotp(data)