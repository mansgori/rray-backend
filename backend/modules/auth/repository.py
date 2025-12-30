from backend.core.database import mongodb
from backend.modules.users.models import User, UserRegister
from backend.modules.auth.models import OTP
from datetime import datetime, timezone, timedelta


class AuthRepository:
    async def user_exists(self, email: str) -> bool:
        return await mongodb.db.users.find_one({"email":email}) is not None
    
    async def create_user(self, user:UserRegister) -> dict:
        data= user.model_dump()
        result = await mongodb.db.users.insert_one(data)
        data["_id"] = str(result.inserted_id)
        return data
    
    async def find_user(self, email: str) -> dict:
        return await mongodb.db.users.find_one({"email":email})
    
    async def find_user_by_id(self, id: str) -> dict:
        return await mongodb.db.users.find_one({"id":id}, {"_id": 0})
    
    async def find_partner(self, identifier: str) -> dict:
        return await mongodb.db.users.find_one({
        "$or": [
            {"email": identifier},
            {"phone": identifier}
        ],
        "role": {"$in": ["partner_owner", "partner_staff"]}
        }, {"_id": 0, "id": 1})
    
    async def find_user_from_email_or_phone(self, identifier: str) -> dict:
        return await mongodb.db.users.find_one({
        "$or": [
            {"email": identifier},
            {"phone": identifier}
        ]
        }, {"_id": 0})
    
    async def update_otp(self, data: OTP) ->bool:
        return await mongodb.db.otps.update_one(
        {"identifier": data.identifier},
        {
            "$set": {
                "identifier": data.identifier,
                "otp": data.otp,
                "user_id": data.user_id,
                "is_new_user": data.is_new_user,
                "created_at": datetime.now(timezone.utc),
                "expires_at": datetime.now(timezone.utc) + timedelta(minutes=5),
                "verified": data.verified
            }
        },
        upsert=True
    )

    async def find_otp(self, identifier:str):
        return await mongodb.db.otps.find_one({"identifier": identifier}, {"_id": 0})
    
    async def verified_otp(self, identifier:str):
        return await mongodb.db.otps.update_one(
            {"identifier": identifier},
            {"$set": {"verified": True}}
        )
    
    async def delete_session(self, session_token: str):
        return await mongodb.db.oauth_session.delete_one({"session_token":session_token})