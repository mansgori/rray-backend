from fastapi import  APIRouter, Depends, Request, Response
from typing import Dict, Any
from backend.modules.auth.schemas import TokenResponse
from backend.modules.users.schemas import UserLogin, UserResponse, ChildProfile
from backend.modules.users.models import UserRegister
from backend.modules.auth.service import AuthService
from backend.modules.users.service import UserService
from backend.modules.auth.dependecies import get_auth_service
from backend.modules.users.dependencies import get_user_service
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
    data: Dict,
    service: AuthService = Depends(get_auth_service)
    ):
    return await service.sendotp(data)

@auth_router.post("/check-partner-exists")
async def check_partner_exists(
    data: Dict,
    service: AuthService = Depends(get_auth_service)
    ):
    return await service.check_partner_exists(data)

@auth_router.post("/verify-otp", response_model=TokenResponse)
async def verify_otp(
    data: Dict,
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
     current_user: Dict = Depends(get_current_user),
     service: AuthService = Depends(get_auth_service)
    ):
     return await service.get_me(current_user)

@auth_router.get("/child-profile")
async def get_child_profile(
     current_user: Dict = Depends(get_current_user),
     service: AuthService = Depends(get_auth_service)
     ):
     return await service.get_child_profile(current_user)

@auth_router.post("/add-child")
async def add_child_profile(
     child:ChildProfile,
     current_user: Dict = Depends(get_current_user),
     service: AuthService = Depends(get_auth_service)
     ):
     return await service.add_child_profile(child=child, current_user=current_user)

@auth_router.put("/edit-child/{child_index}")
async def edit_child_profile(
     child_index: int, 
     child: ChildProfile, 
     current_user: Dict = Depends(get_current_user),
     service: AuthService = Depends(get_auth_service)
     ):
     return await service.edit_child_profile(child_index=child_index, child=child, current_user=current_user)

@auth_router.delete("/delete-child/{child_index}")
async def delete_child_profile(
     child_index: int, 
     current_user: Dict = Depends(get_current_user),
     service: AuthService = Depends(get_auth_service)
     ):
     return await service.delete_child_profile(child_index=child_index, current_user=current_user)





