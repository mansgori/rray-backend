from fastapi import APIRouter, HTTPException

api_router = APIRouter(prefix[])

@api_router.post("/auth/register", response_model=TokenResponse)
async def register(data: UserRegister):
    # LOG: Received registration data
    print(f"🔍 REGISTER - Received role: {data.role}")
    
    existing = await db.users.find_one({"email": data.email}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user = User(
        name=data.name,
        email=data.email,
        phone=data.phone,
        role=data.role,
        hashed_password=hash_password(data.password)
    )
    
    # LOG: User object created
    print(f"🔍 REGISTER - User object role: {user.role}")
    
    await db.users.insert_one(user.model_dump())
    
    # LOG: Verify what was inserted
    inserted_user = await db.users.find_one({"email": data.email}, {"_id": 0, "role": 1, "email": 1})
    print(f"🔍 REGISTER - DB stored role: {inserted_user.get('role')}")
    
    # Create wallet for customers with welcome bonus
    if user.role == UserRole.customer:
        wallet = Wallet(user_id=user.id, credits_balance=50)
        await db.wallets.insert_one(wallet.model_dump())
        
        # Log welcome bonus transaction
        await db.credit_transactions.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": user.id,
            "transaction_type": "earn",
            "amount": 50,
            "source": "welcome_bonus",
            "description": "Welcome to rayy! Here's your first 50 credits",
            "balance_after": 50,
            "created_at": datetime.now(timezone.utc),
            "metadata": {"reason": "signup_bonus"}
        })
    
    token = create_token(user.id, user.role.value)
    user_resp = UserResponse(
        id=user.id,
        role=user.role,
        name=user.name,
        email=user.email,
        phone=user.phone,
        child_profiles=user.child_profiles,
        onboarding_complete=user.onboarding_complete
    )
    
    return TokenResponse(access_token=token, user=user_resp, is_new_user=True)

from app.modules.auth.auth.repository import AuthRepository
from app.modules.auth.auth.schemas import UserRegister, TokenResponse
from app.modules.users.user.models import User
from app.modules.wallet.wallet.models import Wallet

class AuthService:
    def __init__(self, repo: AuthRepository = Depends()):
        self.repo = repo

    async def register(self, data: UserRegister) -> TokenResponse:
        # LOG: Received registration data
        print(f"🔍 REGISTER - Received role: {data.role}")

        existing = await self.repo.user_exists(data.email)
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        user = User(
            name=data.name,
            email=data.email,
            phone=data.phone,
            role=data.role,
            hashed_password=hash_password(data.password)
        )

        # LOG: User object created
        print(f"🔍 REGISTER - User object role: {user.role}")

        await self.repo.user_exists(user)

        # LOG: Verify what was inserted
        inserted_user = await self.repo.user_exists(data.email)
        print(f"🔍 REGISTER - DB stored role: {inserted_user.get('role')}")

        # Create wallet for customers with welcome bonus
        if user.role == UserRole.customer:
            wallet = Wallet(user_id=user.id, credits_balance=50)
            await db.wallets.insert_one(wallet.model_dump())
            
            # Log welcome bonus transaction
            await db.credit_transactions.insert_one({
                "id": str(uuid.uuid4()),
                "user_id": user.id,
                "transaction_type": "earn",
                "amount": 50,
                "source": "welcome_bonus",
                "description": "Welcome to rayy! Here's your first 50 credits",
                "balance_after": 50,
                "created_at": datetime.now(timezone.utc),
                "metadata": {"reason": "signup_bonus"}
            })
    
        token = create_token(user.id, user.role.value)
        user_resp = UserResponse(
            id=user.id,
            role=user.role,
            name=user.name,
            email=user.email,
            phone=user.phone,
            child_profiles=user.child_profiles,
            onboarding_complete=user.onboarding_complete
        )
        
        return TokenResponse(access_token=token, user=user_resp, is_new_user=True)





