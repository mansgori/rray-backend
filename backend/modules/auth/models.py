from pydantic import BaseModel, Field
from datetime import datetime, timezone

class OTP(BaseModel):
    identifier:str
    otp:str
    user_id:str
    is_new_user:str
    verified:bool = False
    