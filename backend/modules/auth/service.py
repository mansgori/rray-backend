from fastapi import APIRouter, HTTPException, Depends
import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Any
from backend.modules.auth.repository import AuthRepository
from backend.modules.wallet.repository import WalletRepository
from backend.modules.auth.schemas import TokenResponse
from backend.modules.users.schemas import UserResponse, UserLogin
from backend.modules.users.models import User, UserRegister, ChildProfile
from backend.modules.wallet.models import Wallet, CreditTransaction
from backend.modules.auth.utility import hash_password, create_token, verify_password
from backend.modules.users.models import UserRole


class AuthService:
    def __init__(self, 
                 auth_repo: AuthRepository,
                 wallet_repo:WalletRepository
                 ):
        self.auth_repo = auth_repo
        self.wallet_repo = wallet_repo

    async def register(self, data: UserRegister) -> TokenResponse:
        # LOG: Received registration data
        print(f"🔍 REGISTER - Received role: {data.role}")

        existing = await  self.auth_repo.user_exists(data.email)
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

        inserted_user = await self.auth_repo.create_user(user)

        # LOG: Verify what was inserted
        verify_inserted_user = await self.auth_repo.user_exists(data.email)
        if(verify_inserted_user):
            print(f"🔍 REGISTER - DB stored role: {inserted_user.get('role')}")

        # Create wallet for customers with welcome bonus
        if user.role == UserRole.customer:
            wallet = Wallet(user_id=user.id, credits_balance=50)
            await self.wallet_repo.create_wallet(wallet)

            credit_transaction = CreditTransaction (
                id= str(uuid.uuid4()),
                user_id=user.id,
                transaction_type= "earn",
                amount= 50,
                source= "welcome_bonus",
                description= "Welcome to rayy! Here's your first 50 credits",
                balance_after= 50,
                created_at= datetime.now(timezone.utc),
                metadata= {"reason": "signup_bonus"}
            )
            
            # Log welcome bonus transaction
            await self.wallet_repo.create_credit_transactions(credit_transaction)
    
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

    async def login(self, data:UserLogin) -> TokenResponse:

        user = await self.auth_repo.find_user(data.email)
        print(user)
        if not user or not verify_password(data.password, user["hashed_password"]):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        token = create_token(user["id"], user["role"])
        user_resp = UserResponse(
            id=user["id"],
            role=UserRole(user["role"]),
            name=user["name"],
            email=user["email"],
            phone=user.get("phone"),
            child_profiles=[ChildProfile(**cp) for cp in user.get("child_profiles", [])],
            onboarding_complete=user.get("onboarding_complete", False)
        )
        return TokenResponse(access_token=token, user=user_resp, is_new_user=False)

    async def sendotp(self, data:dict):
        identifier = data.get("identifier", "")
        user = await self.auth_repo.find_user_from_email_or_phone(identifier)
        user["is_new_user"] = user is None
        user["user_id"] = user["id"] if user else None
        user["otp"] = "1234"
        user["verified"]=False

        await self.auth_repo.update_otp(user)

        return {
        "message": "OTP sent successfully",
        "otp": user["otp"],  # Remove this in production
        "identifier": identifier,
        "is_new_user": user["is_new_user"]
        }

    async def check_partner_exists(self, data:dict):
        identifier = data.get("identifier")
        if not identifier:
            raise HTTPException(status_code=400, detail="Identifier required")
        
        user=await self.auth_repo.find_partner(identifier)

        return {"exists": user is not None}

    async def verify_otp(self, data:dict):
        identifier = data.get("identifier", "")
        otp = data.get("otp", "")
        name = data.get("name")
        role = data.get("role", "customer")

        otp_record = await self.auth_repo.find_otp(identifier)

        if not otp_record:
            raise HTTPException(status_code=404, detail="OTP not found. Please request a new OTP.")
        
        # Check if OTP expired
        expires_at = otp_record["expires_at"]
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at)
        # Ensure timezone awareness
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
    
        if datetime.now(timezone.utc) > expires_at:
            raise HTTPException(status_code=400, detail="OTP expired. Please request a new OTP.")
        
        # Check if OTP is correct
        if otp_record["otp"] != otp:
            raise HTTPException(status_code=401, detail="Invalid OTP")
        
        await self.auth_repo.verified_otp(identifier)
        # Check if this is a new user
        if otp_record.get("is_new_user", False):
            # Create new user
            if not name:
                raise HTTPException(status_code=400, detail="Name is required for new users")
            
            # Determine if identifier is email or phone
            is_email = "@" in identifier

            user = User(
                name=name,
                email=identifier if is_email else f"{identifier}@phone.user",
                phone=identifier if not is_email else None,
                role=UserRole(role),
                hashed_password=hash_password(str(uuid.uuid4()))  # Random password
            )

            await self.auth_repo.create_user(user)

            # Create wallet for customers with welcome bonus
            if user.role == UserRole.customer:
                wallet = Wallet(user_id=user.id, credits_balance=50)
                await self.wallet_repo.create_wallet(wallet)

                credit_transaction = CreditTransaction (
                    id= str(uuid.uuid4()),
                    user_id=user.id,
                    transaction_type= "earn",
                    amount= 50,
                    source= "welcome_bonus",
                    description= "Welcome to rayy! Here's your first 50 credits",
                    balance_after= 50,
                    created_at= datetime.now(timezone.utc),
                    metadata= {"reason": "signup_bonus"}
                )
            
                # Log welcome bonus transaction
                await self.wallet_repo.create_credit_transactions(credit_transaction)
    
            user_dict = user.model_dump()
        else:
            user_dict = await self.auth_repo.find_user_by_id(otp_record["user_id"])
            if not user_dict:
                raise HTTPException(status_code=404, detail="User not found")
        
        # Generate JWT token
        token = create_token(user_dict["id"], user_dict["role"])
        user_resp = UserResponse(
            id=user_dict["id"],
            role=UserRole(user_dict["role"]),
            name=user_dict["name"],
            email=user_dict["email"],
            phone=user_dict.get("phone"),
            child_profiles=[ChildProfile(**cp) for cp in user_dict.get("child_profiles", [])]
        )

        # CRITICAL: Set is_new_user flag based on whether we just created the account
        is_new_user_flag = otp_record.get("is_new_user", False)
        
        return TokenResponse(access_token=token, user=user_resp, is_new_user=is_new_user_flag)
    
    async def logout(self, request, response):
        session_token = request.cookies.get("session_token")

        if session_token:
            self.auth_repo.delete_session(session_token)
        
        response.delete_cookie(key="session_token", path="/")

        return {"message":"Logged out Successfully"}
    
    async def get_me(self, current_user):
            # LOG: What role is in current_user from JWT
        print(f"🔍 /auth/me - current_user role from JWT: {current_user.get('role')}")

        db_user= await self.auth_repo.find_user_by_id(current_user["id"])
        print(f"🔍 /auth/me - DB role for user: {db_user.get('role') if db_user else 'NOT FOUND'}")

        return UserResponse(
            id=current_user["id"],
            role=UserRole(current_user["role"]),
            name=current_user["name"],
            email=current_user["email"],
            phone=current_user.get("phone"),
            child_profiles=[ChildProfile(**cp) for cp in current_user.get("child_profiles", [])],
            onboarding_complete=current_user.get("onboarding_complete", False)
        )
    
    async def get_child_profile(self, current_user:Dict):
        try:
            if current_user["role"] not in ["customer", "partner_owner", "partner_staff"]:
                raise HTTPException(status_code=403, detail="Access denied")
        
            user = await self.auth_repo.get_child_profile(current_user["id"])
        
            return user.get("child_profiles", []) if user else []
        except HTTPException:
            raise  # Re-raise HTTP exceptions
        except Exception as e:
            logging.error(f"Error in get_children: {e}")
            return []

    async def add_child_profile(self, child:ChildProfile, current_user=Dict):
        try:
            if current_user["role"] not in ["customer", "partner_owner", "partner_staff"]:
                raise HTTPException(status_code=403, detail="Access denied")
                
            await self.auth_repo.users.update_one(
            {"id": current_user["id"]},
            {"$push": {"child_profiles": child.model_dump()}}
            )
    
            return {"message": "Child added successfully"}
        except HTTPException:
            raise  # Re-raise HTTP exceptions
        except Exception as e:
            logging.error(f"Error in add_children: {e}")
            return []
        
    async def edit_child_profile(self, child_index:int, child:ChildProfile, current_user:Dict):
        try:
            if current_user["role"] not in ["customer", "partner_owner", "partner_staff"]:
                raise HTTPException(status_code=403, detail="Access denied")
            
            id = current_user["id"]

            user = await self.auth_repo.find_user_by_id(id)

            if not user or "child_profiles" not in user or len(user["child_profiles"]) <= child_index:
                raise HTTPException(status_code=404, detail="Child profile not found")
            
            user["child_profiles"][child_index] = child.model_dump()

            await self.auth_repo.add_child_profile(
                {"id": current_user["id"]},
                {"$push": {"child_profiles": user["child_profiles"]}}
            )

            return {"message": "Child profile updated successfully"}
        except HTTPException:
            raise  # Re-raise HTTP exceptions
        except Exception as e:
            logging.error(f"Error in add_children: {e}")
            return []
    
    async def delete_child_profile(self, child_index: int, current_user: Dict):
        try:
            if current_user["role"] not in ["customer", "partner_owner", "partner_staff"]:
                raise HTTPException(status_code=403, detail="Access denied")
            
            id = current_user["id"]

            user = await self.auth_repo.find_user_by_id(id)

            if not user or "child_profiles" not in user or len(user["child_profiles"]) <= child_index:
                raise HTTPException(status_code=404, detail="Child profile not found")
            
                # Remove the child profile at the specified index
            user["child_profiles"].pop(child_index)

            await self.auth_repo.add_child_profile(
                {"id": current_user["id"]},
                {"$push": {"child_profiles": user["child_profiles"]}}
            )
            
            return {"message": "Child profile deleted successfully"}
        except HTTPException:
            raise  # Re-raise HTTP exceptions
        except Exception as e:
            logging.error(f"Error in add_children: {e}")
            return []

