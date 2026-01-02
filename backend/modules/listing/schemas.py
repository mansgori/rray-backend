from pydantic import BaseModel
from typing import Optional, List

class PlanOptionCreate(BaseModel):
    plan_type: str
    name: str
    description: Optional[str] = None
    sessions_count: int
    price_inr: float
    discount_percent: float = 0.0
    validity_days: int = 30

class BatchCreate(BaseModel):
    name: str
    days_of_week: List[str]
    time: str
    duration_minutes: int
    capacity: int
    plan_types: List[str]
    start_date: str
    end_date: Optional[str] = None