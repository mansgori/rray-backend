from fastapi import  APIRouter, Depends, Request, Response
from backend.modules.auth.schemas import TokenResponse
from backend.modules.users.schemas import UserLogin, UserResponse
from backend.modules.users.models import UserRegister
from backend.modules.auth.service import AuthService
from backend.modules.auth.dependecies import get_auth_service
from backend.modules.auth.utility import  get_current_user

auth_router = APIRouter(prefix="/auth", tags=["Auth"])

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
async def verify_otp(
    data: dict,
    service: AuthService = Depends(get_auth_service)
    ):
    return await service.verify_otp(data)

#Here google authentication added is pending

@auth_router.post("/logout")
async def logout(
    request: Request, 
    response: Response,
    service: AuthService = Depends(get_auth_service)
    ):
        return await service.logout(request, response)

@auth_router.post("/me", response_model=UserResponse)
async def get_me(
     current_user: dict = Depends(get_current_user),
     service: AuthService = Depends(get_auth_service)
    ):
     return await service.get_me(current_user)

