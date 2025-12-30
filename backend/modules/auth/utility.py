from fastapi import Depends, security, HTTPException
from typing import Dict
from fastapi.security import  HTTPBearer, HTTPAuthorizationCredentials
import bcrypt
import jwt
from datetime import datetime, timezone, timedelta
from backend.modules.auth.repository import AuthRepository
from backend.core.config import JWT_ALGORITHM, JWT_EXPIRY_HOURS, JWT_SECRET

security = HTTPBearer()

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_token(user_id: str, role: str) -> str:
    payload = {
        "sub": user_id,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), auth_repo: AuthRepository = Depends()) -> Dict:
    try:
        token = credentials.credentials
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        print(f"🔍 JWT Payload - sub (user_id): {payload.get('sub')}, role: {payload.get('role')}")
        
        user = await auth_repo.find_user_by_id(payload["sub"])
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        print(f"🔍 get_current_user - DB returned role: {user.get('role')} for user: {user.get('email')}")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")