from pydantic import BaseModel, ConfigDict, Field, EmailStr
from typing import  Optional,List, Dict, Any
from enum import Enum
from backend.modules.users.models import ChildProfile


class UserRole(str, Enum):
    customer = "customer"
    partner_owner = "partner_owner"
    partner_staff = "partner_staff"
    admin = "admin"

class UserResponse(BaseModel):
    id: str
    role: UserRole
    name: str
    email: EmailStr
    phone: Optional[str] = None
    child_profiles: List[ChildProfile] = []
    onboarding_complete: bool = False

class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str
    phone: Optional[str] = None
    role: UserRole  # No default - must be explicitly provided

class UserLogin(BaseModel):
    email: EmailStr
    password: str