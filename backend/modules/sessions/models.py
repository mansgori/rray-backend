from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime
from enum import Enum
import uuid


class SessionStatus(str, Enum):
    scheduled = "scheduled"
    canceled = "canceled"
    completed = "completed"

class Session(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    listing_id: str
    start_at: datetime
    end_at: datetime
    seats_total: int
    seats_booked: int = 0
    allow_late_booking_minutes: int = 60
    price_override_inr: Optional[float] = None
    staff_assigned: Optional[str] = None
    status: SessionStatus = SessionStatus.scheduled
    # NEW: Flexible booking fields
    batch_id: Optional[str] = None  # Link to batch
    is_rescheduled: bool = False
    original_date: Optional[str] = None  # ISO date if rescheduled