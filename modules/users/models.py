from pydantic import BaseModel, ConfigDict, Field, EmailStr, Optional,List, Dict, Any
from datetime import datetime, timezone, timedelta
from enum import Enum
import uuid

class KYCStatus(str, Enum):
    unverified = "unverified"
    pending = "pending"
    verified = "verified"

class ChildProfile(BaseModel):
    name: str
    age: int
    interests: List[str] = []

class UserRole(str, Enum):
    customer = "customer"
    partner_owner = "partner_owner"
    partner_staff = "partner_staff"
    admin = "admin"

class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    role: UserRole = UserRole.customer
    name: str
    email: EmailStr
    phone: Optional[str] = None
    hashed_password: str
    whatsapp_opt_in: bool = False
    child_profiles: List[ChildProfile] = []
    kyc_status: KYCStatus = KYCStatus.unverified
    location: Optional[Dict[str, Any]] = None  # {lat, lng, city, pin, accuracy, ts}
    wishlist: List[str] = []  # List of listing IDs
    onboarding_complete: bool = False  # Track if user completed onboarding wizard
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))