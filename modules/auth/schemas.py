from pydantic import BaseModel
from ..users.schema import UserResponse

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
    is_new_user: bool = False  # Flag to trigger onboarding on frontend