from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum
import uuid


class PaymentMethod(str, Enum):
    credit_wallet = "credit_wallet"
    razorpay_card = "razorpay_card"
    upi = "upi"

class BookingCreate(BaseModel):
    session_id: str
    child_profile_name: str
    child_profile_age: int
    payment_method: PaymentMethod
    use_credits: bool = False
    is_trial: bool = False
    plan_type: Optional[str] = "single"  # "single", "weekly", "monthly", "quarterly"
    sessions_count: Optional[int] = 1  # Number of sessions in the plan

class BookingCreateV2(BaseModel):
    listing_id: str
    plan_option_id: str
    batch_id: str
    session_ids: List[str]
    child_profile_name: str
    child_profile_age: int
    payment_method: PaymentMethod
    use_credits: bool = False

class PlanBookingCreate(BaseModel):
    listing_id: str
    plan_id: str  # "single", "weekly", "monthly", "quarterly", "trial"
    session_ids: List[str]  # Specific sessions to book
    child_profile_name: str
    child_profile_age: int
    payment_method: PaymentMethod
    use_credits: bool = False