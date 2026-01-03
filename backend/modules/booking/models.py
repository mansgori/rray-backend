from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import datetime, timezone
from enum import Enum
import uuid
from backend.modules.booking.schemas import PaymentMethod

class RescheduleRequest(BaseModel):
    new_session_id: str
    
class BookingStatus(str, Enum):
    confirmed = "confirmed"
    pending = "pending"
    canceled = "canceled"
    attended = "attended"
    no_show = "no_show"
    refunded = "refunded"

class Booking(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    session_id: str
    listing_id: str
    child_profile_name: str
    child_profile_age: int
    qty: int = 1
    unit_price_inr: float
    taxes_inr: float
    total_inr: float
    credits_used: int = 0
    payment_method: PaymentMethod
    payment_txn_id: Optional[str] = None
    booking_status: BookingStatus = BookingStatus.confirmed
    booked_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    canceled_at: Optional[datetime] = None
    cancellation_reason: Optional[str] = None
    refund_amount_inr: float = 0.0
    refund_credits: int = 0
    # Attendance tracking fields
    attendance: Optional[str] = None  # "present", "absent", "late"
    attendance_notes: Optional[str] = None
    attendance_at: Optional[datetime] = None
    payout_eligible: bool = False
    canceled_by: Optional[str] = None  # "customer" or "partner"
    is_trial: bool = False  # Trial booking flag
    reschedule_count: int = 0  # Track number of times rescheduled
    # NEW: Flexible booking fields
    plan_option_id: Optional[str] = None  # Reference to listing.plan_options[].id
    batch_id: Optional[str] = None  # Which batch student enrolled in
    session_ids: List[str] = []  # All booked sessions (for multi-session plans)