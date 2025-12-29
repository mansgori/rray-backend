from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import Optional, Dict, Any
from datetime import datetime, timezone
import uuid


class Wallet(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    credits_balance: int = 0
    last_grant_at: Optional[datetime] = None

class CreditTransaction(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id:str
    transaction_type: str
    amount: int
    balance_after:int
    source:str
    description:Optional[str] = None
    metadata:Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )