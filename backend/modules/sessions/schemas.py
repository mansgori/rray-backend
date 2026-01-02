from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class SessionCreate(BaseModel):
    listing_id: str
    start_at: datetime
    duration_minutes: int
    seats_total: int
    price_override_inr: Optional[float] = None