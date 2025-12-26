from fastapi import  APIRouter, Depends
from ...modules.auth.schemas import UserRegister, TokenResponse
from ...modules.auth.service import AuthService

api_router = APIRouter(prefix="/auth", tags=["Auth"])

@api_router.post("/register", response_model=TokenResponse)
async def register(
    data: UserRegister,
    service: AuthService = Depends()
    ):
    return await service.register(data)