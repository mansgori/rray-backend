from fastapi import Request, HTTPException
from typing import Dict, Any
from typing import Optional
from datetime import datetime, timezone
import os
import logging
from backend.modules.auth.repository import AuthRepository
from backend.modules.wallet.repository import WalletRepository
from backend.modules.users.repository import UserRepository
from backend.core.email_service.email_instance import email_service



class UserService:
    def __init__(self, 
                 auth_repo: AuthRepository,
                 wallet_repo:WalletRepository,
                 user_repo:UserRepository
                 ):
        self.auth_repo = auth_repo
        self.wallet_repo = wallet_repo
        self.user_repo = user_repo

    async def update_profile(
        self,
        current_user: dict,
        child_profiles: Optional[list],
        preferences: Optional[dict],
    ):
        update_data = {}

        if child_profiles is not None:
            update_data["child_profiles"] = [
                cp.model_dump() if hasattr(cp, "model_dump") else cp
                for cp in child_profiles
            ]

        if preferences is not None:
            update_data["preferences"] = preferences

        if not update_data:
            return {"message": "Nothing to update"}

        update_data["updated_at"] = datetime.now(timezone.utc)

        await self.user_repo.update_user_by_id(
            current_user["id"],
            update_data
        )

        return {"message": "Profile updated successfully"}
    
    async def update_partner_profile(
        self,
        profile_data: Dict[str, Any],
        current_user: Dict,
        request: Request = None
          ):
        tnc_acceptance = profile_data.pop('tncAcceptance', None)

            # Prepare update data
        update_data = {
            **profile_data,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }

            # Store T&C acceptance metadata
        if tnc_acceptance:
            update_data["tnc_acceptance"] = {
                **tnc_acceptance,
                "ip_address": request.client.host if request else "unknown",
                "accepted_at": datetime.now(timezone.utc).isoformat()
        }
            
            # Update user in database
        await self.user_repo.update_user_by_id(
            {"id": current_user["id"]},
            {"$set": update_data}
        )

        updated_user = await self.auth_repo.find_user_by_id({"id": current_user["id"]})
        partner_email=updated_user.get('email'),
        partner_data={
            'name': updated_user.get('name'),
            'email': updated_user.get('email'),
            'organizationName': updated_user.get('organizationName'),
            'phone': updated_user.get('phone') or updated_user.get('contactNumber'),
            'city': updated_user.get('city'),
            'state': updated_user.get('state'),
            'categories': updated_user.get('categories', []),
            'created_at': updated_user.get('created_at')
                    }

            # Send email notifications if onboarding completed
        if profile_data.get('onboardingCompleted') and tnc_acceptance:
            try:        
                # Send confirmation email to partner
                email_service.send_partner_registration_confirmation(partner_email=partner_email, partner_data=partner_data)
                
                # Notify admin of new pending partner
                admin_email = os.environ.get('ADMIN_EMAIL', 'admin@rrray.com')
                email_service.send_admin_new_partner_notification(admin_email=admin_email,partner_data=partner_data)
                
            except Exception as e:
                logging.error(f"Failed to send partner registration email: {e}")
        
        return {
            "message": "Profile updated successfully",
            "user": {
                "id": updated_user["id"],
                "name": updated_user.get("name"),
                "email": updated_user.get("email"),
                "role": updated_user.get("role"),
                "status": updated_user.get("status", "pending"),
                "onboardingCompleted": updated_user.get("onboardingCompleted", False)
            }
        }

    async def update_customer_profile(self, profile_data: Dict[str, Any], current_user: Dict ):
        try:
            if current_user["role"] not in ["customer", "partner_owner", "partner_staff"]:
                raise HTTPException(status_code=403, detail="Access denied")
            # Prepare update data
            update_data = {}
                
            # Allow updating name and phone
            if "name" in profile_data:
                update_data["name"] = profile_data["name"]
            if "phone" in profile_data:
                update_data["phone"] = profile_data["phone"]

            # Handle preferences
            if "preferences" in profile_data:
                update_data["preferences"] = profile_data["preferences"]

            # Add updated timestamp
            update_data["updated_at"] = datetime.now(timezone.utc)

            await self.user_repo.update_user_by_id(
                {"id": current_user["id"]},
                {"$push": update_data}
            )
            id = current_user["id"]

            updated_user = await self.auth_repo.find_user_by_id(id)
            
            return {"message": "Profile updated successfully", "user": updated_user}
        except HTTPException:
            raise  # Re-raise HTTP exceptions
        except Exception as e:
            logging.error(f"Error in add_children: {e}")
            return []
        
    async def update_location(self, location: Dict[str, Any], current_user: Dict ):
        try:
            if current_user["role"] not in ["customer", "partner_owner", "partner_staff"]:
                raise HTTPException(status_code=403, detail="Access denied")
            # Prepare update data
            update_data = {
                "location": location,
                "updated_at": datetime.now(timezone.utc)
            }

            await self.user_repo.update_user_by_id(
                {"id": current_user["id"]},
                {"$set": update_data}
            )
            id = current_user["id"]

            updated_user = await self.auth_repo.find_user_by_id(id)
            
            return {"message": "Location updated successfully", "user": updated_user}
        except HTTPException:
            raise  # Re-raise HTTP exceptions
        except Exception as e:
            logging.error(f"Error in update_location: {e}")
            return []
    
    async def complete_onboarding(self, current_user: Dict ):
        try:
            if current_user["role"] not in ["customer", "partner_owner", "partner_staff"]:
                raise HTTPException(status_code=403, detail="Access denied")
            # Prepare update data
            update_data = {
                "onboardingCompleted": True,
                "updated_at": datetime.now(timezone.utc)
            }

            await self.user_repo.update_user_by_id(
                {"id": current_user["id"]},
                {"$set": update_data}
            )
            id = current_user["id"]

            updated_user = await self.auth_repo.find_user_by_id(id)
            
            return {"message": "Onboarding completed successfully", "user": updated_user}
        except HTTPException:
            raise  # Re-raise HTTP exceptions
        except Exception as e:
            logging.error(f"Error in complete_onboarding: {e}")
            return []