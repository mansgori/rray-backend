from fastapi import Request, HTTPException
from typing import Dict, Any
from typing import Optional
from datetime import datetime, timezone, timedelta
import os
import logging
import uuid
from backend.modules.auth.repository import AuthRepository
from backend.modules.wallet.repository import WalletRepository
from backend.modules.users.repository import UserRepository
from backend.modules.listing.repository import ListingRepository
from backend.modules.partner.repository import PartnerRepository
from backend.modules.sessions.repository import SessionRepository
from backend.core.email_service.email_instance import email_service
from backend.modules.listing.utility import calculate_distance_km, format_distance



class ListingService:
    def __init__(self, 
                 auth_repo: AuthRepository,
                 wallet_repo:WalletRepository,
                 user_repo:UserRepository,
                 listing_repo:ListingRepository,
                 partner_repo:PartnerRepository,
                 session_repo:SessionRepository
                 ):
        self.auth_repo = auth_repo
        self.wallet_repo = wallet_repo
        self.user_repo = user_repo
        self.listing_repo = listing_repo
        self.partner_repo = partner_repo
        self.session_repo = session_repo
    
    async def get_categories(self):
        categories = await self.listing_repo.get_categories()
        return categories
    
    async def search_listings(self,city, age, category,date,is_online,trial,
                            lat,lng,radius_km,skip,limit):
        listings = await self.repo.search_pipeline(
            city, age, category,
            is_online, trial,
            skip, limit
        )
        for listing in listings:
            listing.pop("_id", None)

            if listing.get("images") and not listing.get("media"):
                listing["media"] = listing["images"]
            
            # Partner info
            partner = (listing.get("partner_data") or [{}])[0]
            listing["partner_name"] = partner.get("brand_name", "")
            listing["partner_city"] = partner.get("city", "")

            # Venue info
            venue = (listing.get("venue_data") or [{}])[0]
            venue.pop("_id", None)
            listing["venue"] = venue

            if lat and lng and venue.get("lat") and venue.get("lng"):
                distance = calculate_distance_km(lat, lng, venue["lat"], venue["lng"])
                listing["distance_km"] = round(distance, 1)
                listing["distance_text"] = format_distance(distance)
            
            listing.pop("partner_data", None)
            listing.pop("venue_data", None)

        return {
            "listings": listings,
            "total": len(listings)
        }
    
    async def get_my_listings(self, current_user):
        try:
            if current_user["role"] not in ["partner_owner", "partner_staff"]:
                raise HTTPException(status_code=403, detail="Not a partner")
            
            partner = await self.partner_repo.get_partner_by_id(current_user["id"])

            if not partner:
                raise HTTPException(status_code=404, detail="Partner not found")
            
            listings = await self.listing_repo.get_category_by_id(partner["id"])

            return {"listings": listings}
        except HTTPException:
            raise  # Re-raise HTTP exceptions
        except Exception as e:
            logging.error(f"Error in add_children: {e}")
            return []

    async def get_listing_by_id(self, listing_id: str):
        try:
            listing = await self.listing_repo.get_listing_by_id(listing_id)

            if not listing:
                raise HTTPException(status_code=404, detail="Listing not found")
            
            partner = await self.partner_repo.get_partner_by_id(listing["partner_id"])
            if partner:
                listing["partner"] = {
                    "brand_name": partner.get("name", "Partner"),
                    "city": partner.get("city", ""),
                    "verification_badges": partner.get("badges", [])
                }
            # Enrich with venue details if applicable
            if listing.get("venue_id"):
                venue = await self.venue_repo.get_venue_by_id(listing["venue_id"])
                if venue:
                    listing["venue"] = venue
            
            # Category is already a string field on listing, no need to look up
            # Just ensure it exists
            if not listing.get("category"):
                listing["category"] = "General"

            # Convert images array to media array format for frontend
            if listing.get("images") and not listing.get("media"):
                listing["media"] = listing["images"]
            
            return listing
        except HTTPException:
            raise  # Re-raise HTTP exceptions
        except Exception as e:
            logging.error(f"Error in add_children: {e}")
            return []
        
    async def get_listing_sessions(
        self,
        listing_id: str,
        from_date: Optional[str],
        to_date: Optional[str]
    ):
        try:
            # Get the listing to get base price
            data_filter = {"base_price_inr": 1}
            listing = await self.listing_repo.get_listing_by_id(listing_id, data_filter)
            base_price = listing.get("base_price_inr", 1000) if listing else 1000
            
            # Get current date for filtering
            today = datetime.now(timezone.utc).date()
            today_str = today.isoformat()
            
            # Default to 90 days ahead if no to_date specified
            if not to_date:
                default_end_date = today + timedelta(days=90)
                to_date = default_end_date.isoformat()
            
            # Query both old and new session structures
            base_query = {"listing_id": listing_id, "status": "scheduled"}
            
            # Get sessions with new structure (date/time fields) - PRIORITIZE THESE
            new_sessions_query = {**base_query, "date": {"$exists": True}}
            if from_date:
                new_sessions_query["date"] = {"$gte": from_date}
            else:
                new_sessions_query["date"] = {"$gte": today_str}
            
            if to_date:
                if "date" in new_sessions_query and isinstance(new_sessions_query["date"], dict):
                    new_sessions_query["date"]["$lte"] = to_date
                else:
                    new_sessions_query["date"] = {"$lte": to_date}
            
            new_sessions = await db.sessions.find(new_sessions_query, {"_id": 0}).to_list(1000)
            
            # Get sessions with old structure (start_at field) ONLY if no new sessions found
            old_sessions = []
            if len(new_sessions) < 100:  # Get old sessions as fallback if not many new sessions
                old_sessions_query = {**base_query, "start_at": {"$exists": True}}
                if from_date:
                    old_sessions_query["start_at"] = {"$gte": datetime.fromisoformat(from_date)}
                else:
                    old_sessions_query["start_at"] = {"$gte": datetime.now(timezone.utc)}
                    
                if to_date:
                    if "start_at" in old_sessions_query and isinstance(old_sessions_query["start_at"], dict):
                        old_sessions_query["start_at"]["$lte"] = datetime.fromisoformat(to_date)
                    else:
                        old_sessions_query["start_at"] = {"$lte": datetime.fromisoformat(to_date)}
                
                old_sessions = await db.sessions.find(old_sessions_query, {"_id": 0}).limit(1000).to_list(1000)
            
            # Normalize and combine sessions
            all_sessions = []
            
            # Process new structure sessions (with pricing)
            for session in new_sessions:
                # Convert date/time to datetime for sorting
                try:
                    session_date = datetime.fromisoformat(session["date"])
                    session_time_str = session["time"]
                    
                    # Parse time
                    if isinstance(session_time_str, str):
                        time_parts = session_time_str.split(':')
                        hour = int(time_parts[0])
                        minute = int(time_parts[1]) if len(time_parts) > 1 else 0
                    else:
                        hour = session_time_str.hour if hasattr(session_time_str, 'hour') else 0
                        minute = session_time_str.minute if hasattr(session_time_str, 'minute') else 0
                    
                    # Combine date and time
                    session_datetime = session_date.replace(
                        hour=hour,
                        minute=minute,
                        second=0,
                        microsecond=0,
                        tzinfo=timezone.utc
                    )
                    
                    session["start_at"] = session_datetime
                    seats_booked = session.get("seats_booked", 0)
                    session["seats_available"] = session["seats_total"] - seats_booked
                    
                    # Ensure price_inr is present
                    if "price_inr" not in session or session["price_inr"] is None:
                        session["price_inr"] = base_price
                    
                    # Add is_bookable flag
                    has_seats = session["seats_available"] > 0
                    is_future = session_datetime > datetime.now(timezone.utc)
                    session["is_bookable"] = has_seats and is_future
                    
                    all_sessions.append(session)
                except Exception as e:
                    logging.warning(f"Error processing session {session.get('id')}: {e}")
                    continue
            
            # Process old structure sessions (add pricing from listing base_price)
            for session in old_sessions:
                seats_booked = session.get("seats_booked", 0)
                session["seats_available"] = session["seats_total"] - seats_booked
                
                # Add price_inr if missing
                if "price_inr" not in session:
                    session["price_inr"] = session.get("price_override_inr") or base_price
                    session["plan_type"] = "single"
                    session["plan_name"] = "Single Session"
                    session["sessions_count"] = 1
                
                # Ensure timezone-aware
                if session["start_at"].tzinfo is None:
                    session["start_at"] = session["start_at"].replace(tzinfo=timezone.utc)
                
                # Add is_bookable flag
                has_seats = session["seats_available"] > 0
                is_future = session["start_at"] > datetime.now(timezone.utc)
                session["is_bookable"] = has_seats and is_future
                
                all_sessions.append(session)
            
            # Sort by start_at
            all_sessions.sort(key=lambda x: x["start_at"])
            
            return {"sessions": all_sessions}
        except Exception as e:
            # CRITICAL: Return empty array instead of error object to prevent frontend crashes
            logging.error(f"Error in get_listing_sessions for listing {listing_id}: {e}")
            return {"sessions": []}

    async def get_listing_plans(self, listing_id):
        try:
            listing = await self.listing_repo.get_listing_by_id(listing_id)

            if not listing:
                raise HTTPException(status_code=404, detail="Listing not found")

            base_price = listing.get("base_price_inr", 1000)
            trial_price = listing.get("trial_price_inr")
            trial_available = listing.get("trial_available", False)

            date = datetime.now(timezone.utc).date().isoformat()

            total_sessions = await self.session_repo.get_document_count(listing_id, date)

            # Define pricing plans with discounts
            plans = []

            # Trial plan (if available)
            if trial_available and trial_price:
                plans.append({
                    "id": "trial",
                    "name": "Trial Class",
                    "description": "Try before you commit",
                    "sessions_count": 1,
                    "price_inr": trial_price,
                    "price_per_session": trial_price,
                    "discount_percent": int(((base_price - trial_price) / base_price) * 100),
                    "savings_inr": base_price - trial_price,
                    "validity_days": 30,
                    "is_trial": True,
                    "badge": "Most Popular"
                })

            # Single session
            plans.append({
                "id": "single",
                "name": "Single Session",
                "description": "Pay as you go",
                "sessions_count": 1,
                "price_inr": base_price,
                "price_per_session": base_price,
                "discount_percent": 0,
                "savings_inr": 0,
                "validity_days": 30,
                "is_trial": False
            })

                # Weekly plan (4 sessions, 10% off) - Always show
            weekly_price_per_session = int(base_price * 0.9)
            weekly_total = weekly_price_per_session * 4

            plans.append({
                "id": "weekly",
                "name": "Weekly Plan",
                "description": "4 sessions per month",
                "sessions_count": 4,
                "price_inr": weekly_total,
                "price_per_session": weekly_price_per_session,
                "discount_percent": 10,
                "savings_inr": (base_price * 4) - weekly_total,
                "validity_days": 60,
                "is_trial": False,
                "badge": "Save 10%",
                "available": total_sessions >= 4
            })

            # Monthly plan (12 sessions, 25% off) - Always show
            monthly_price_per_session = int(base_price * 0.75)
            monthly_total = monthly_price_per_session * 12
            plans.append({
                "id": "monthly",
                "name": "Monthly Plan",
                "description": "12 sessions over 3 months",
                "sessions_count": 12,
                "price_inr": monthly_total,
                "price_per_session": monthly_price_per_session,
                "discount_percent": 25,
                "savings_inr": (base_price * 12) - monthly_total,
                "validity_days": 90,
                "is_trial": False,
                "badge": "Best Value",
                "available": total_sessions >= 12
            })

            # Quarterly plan (36 sessions, 35% off)
            if total_sessions >= 36:
                quarterly_price_per_session = int(base_price * 0.65)
                quarterly_total = quarterly_price_per_session * 36
                plans.append({
                    "id": "quarterly",
                    "name": "Quarterly Plan",
                    "description": "36 sessions over 6 months",
                    "sessions_count": 36,
                    "price_inr": quarterly_total,
                    "price_per_session": quarterly_price_per_session,
                    "discount_percent": 35,
                    "savings_inr": (base_price * 36) - quarterly_total,
                    "validity_days": 180,
                    "is_trial": False,
                    "badge": "Maximum Savings"
                })
            return {
                "plans": plans,
                "total_available_sessions": total_sessions,
                "base_price_inr": base_price
            }
        except HTTPException:
            raise  # Re-raise HTTP exceptions
        except Exception as e:
            logging.error(f"Error in add_children: {e}")
            return []
    
    async def update_listing(self, listing_id, data, current_user):
        try:
            if current_user["role"] not in ["partner_owner", "partner_staff", "admin"]:
                raise HTTPException(status_code=403, detail="Only partners can update listings")
            
            listing = await self.listing_repo.get_listing_by_id(listing_id)
            if not listing:
                raise HTTPException(status_code=404, detail="Listing not found")
            
            # Verify ownership
            if current_user["role"] != "admin":
                partner = await self.partner_repo.get_partner_by_id(current_user["id"])
                if not partner or listing["partner_id"] != partner["id"]:
                    raise HTTPException(status_code=403, detail="Unauthorized")
            # Update fields
            data["updated_at"] = datetime.now(timezone.utc)

            await self.listing_repo.update_listing(listing_id, data)

        except HTTPException:
            raise  # Re-raise HTTP exceptions
        except Exception as e:
            logging.error(f"Error in add_children: {e}")
            return []
    
    async def add_plan_option(self, listing_id, plan, current_user):
        try:
            if current_user["role"] not in ["partner_owner", "partner_staff", "admin"]:
                raise HTTPException(status_code=403, detail="Only partners can manage plans")
            
            listing = await self.listing_repo.get_listing_by_id(listing_id)
            if not listing:
                raise HTTPException(status_code=404, detail="Listing not found")
            
            # Create plan with ID
            plan_dict = plan.model_dump()
            plan_dict["id"] = str(uuid.uuid4())
            plan_dict["is_active"] = True

            new_data = {
                "plan_options": plan_dict
            }
            date = datetime.now(timezone.utc)
            
            await self.listing_repo.update_listing(listing_id, new_data, date)

            return {"message": "Plan option added", "plan_id": plan_dict["id"]}

        except HTTPException:
            raise  # Re-raise HTTP exceptions
        except Exception as e:
            logging.error(f"Error in add_children: {e}")
            return []
    
    async def update_plan_option(self, listing_id, plan, plan_data, current_user):
        try:
            if current_user["role"] not in ["partner_owner", "partner_staff", "admin"]:
                raise HTTPException(status_code=403, detail="Only partners can manage plans")
            
            listing = await self.listing_repo.get_listing_by_id(listing_id)
            if not listing:
                raise HTTPException(status_code=404, detail="Listing not found")
            
            data=plan_data
            date = datetime.now(timezone.utc)
            
            result = await self.listing_repo.update_listing(listing_id, data, date)

            if result.modified_count == 0:
                raise HTTPException(status_code=404, detail="Plan not found")
    
            return {"message": "Plan updated successfully"}

        except HTTPException:
            raise  # Re-raise HTTP exceptions
        except Exception as e:
            logging.error(f"Error in add_children: {e}")
            return []

    async def delete_plan_option(self, listing_id, plan_id, current_user):
        try:
            if current_user["role"] not in ["partner_owner", "partner_staff", "admin"]:
                raise HTTPException(status_code=403, detail="Only partners can manage plans")
            
            listing = await self.listing_repo.get_listing_by_id(listing_id)
            if not listing:
                raise HTTPException(status_code=404, detail="Listing not found")
            
            delete_option={"plan_options": {"id":plan_id}}
            date = datetime.now(timezone.utc)
            
            result = await self.listing_repo.update_listing(listing_id, delete_option, date)

            if result.modified_count == 0:
                raise HTTPException(status_code=404, detail="Plan not found")
    
            return {"message": "Plan deleted successfully"}

        except HTTPException:
            raise  # Re-raise HTTP exceptions
        except Exception as e:
            logging.error(f"Error in add_children: {e}")
            return []
    
    async def add_batch(self, listing_id, batch, current_user):
        try:
            if current_user["role"] not in ["partner_owner", "partner_staff", "admin"]:
                raise HTTPException(status_code=403, detail="Only partners can manage batches")
            
            listing = await self.listing_repo.get_listing_by_id(listing_id)
            if not listing:
                raise HTTPException(status_code=404, detail="Listing not found")
            
            batch_dict = batch.model_dump()
            batch_dict["id"] = str(uuid.uuid4())
            batch_dict["enrolled_count"] = 0
            batch_dict["is_active"] = True
            date = datetime.now(timezone.utc)

            new_data = {
                "batches": batch_dict
            }
            
            result = await self.listing_repo.update_listing(listing_id, new_data, date)

            if result.modified_count == 0:
                raise HTTPException(status_code=404, detail="Batch not found")
    
            return {"message": "Batch added", "batch_id": batch_dict["id"]}

        except HTTPException:
            raise  # Re-raise HTTP exceptions
        except Exception as e:
            logging.error(f"Error in add_children: {e}")
            return []
        
    async def update_batch(self, listing_id, batch_id, batch_data, current_user):
        try:
            if current_user["role"] not in ["partner_owner", "partner_staff", "admin"]:
                raise HTTPException(status_code=403, detail="Only partners can manage plans")
            
            listing = await self.listing_repo.get_listing_by_id(listing_id)
            if not listing:
                raise HTTPException(status_code=404, detail="Listing not found")
            
            data=batch_data
            date = datetime.now(timezone.utc)
            
            result = await self.listing_repo.update_listing(listing_id, batch_id, data, date)

            if result.modified_count == 0:
                raise HTTPException(status_code=404, detail="Batch not found")
    
            return {"message": "Batch updated successfully"}

        except HTTPException:
            raise  # Re-raise HTTP exceptions
        except Exception as e:
            logging.error(f"Error in add_children: {e}")
            return []
        

    async def delete_batch(self, listing_id, batch_id, current_user):
        try:
            if current_user["role"] not in ["partner_owner", "partner_staff", "admin"]:
                raise HTTPException(status_code=403, detail="Only partners can manage plans")
            
            listing = await self.listing_repo.get_listing_by_id(listing_id)
            if not listing:
                raise HTTPException(status_code=404, detail="Listing not found")
            
            delete_option={"batches": {"id":batch_id}}
            date = datetime.now(timezone.utc)
            
            result = await self.listing_repo.update_listing(listing_id, delete_option, date)

            if result.modified_count == 0:
                raise HTTPException(status_code=404, detail="Batch not found")
    
            return {"message": "Batch updated successfully"}

        except HTTPException:
            raise  # Re-raise HTTP exceptions
        except Exception as e:
            logging.error(f"Error in add_children: {e}")
            return []

    async def check_batch_availability(self, listing_id, batch_id):
        try:
            data_filter = {"batches": 1}
            listing = await self.listing_repo.get_listing_by_id(listing_id, data_filter)
            if not listing:
                raise HTTPException(status_code=404, detail="Batch not found")
            
            batch = next((b for b in listing.get("batches", []) if b["id"] == batch_id), None)
            if not batch:
                raise HTTPException(status_code=404, detail="Batch not found")
    
            available_seats = batch["capacity"] - batch.get("enrolled_count", 0)
            
            return {
                "batch_id": batch_id,
                "capacity": batch["capacity"],
                "enrolled": batch.get("enrolled_count", 0),
                "available": available_seats,
                "is_full": available_seats <= 0
            }

        except HTTPException:
            raise  # Re-raise HTTP exceptions
        except Exception as e:
            logging.error(f"Error in add_children: {e}")
            return []
    
    async def generate_batch_sessions(self, listing_id, batch_id, weeks, current_user):
        try:
            if current_user["role"] not in ["partner_owner", "partner_staff", "admin"]:
                raise HTTPException(status_code=403, detail="Only partners can generate sessions")
            
            listing = await self.listing_repo.get_listing_by_id(listing_id)
            
            if not listing:
                raise HTTPException(status_code=404, detail="Listing not found")
            
            batch = next((b for b in listing.get("batches", []) if b["id"] == batch_id), None)
            if not batch:
                raise HTTPException(status_code=404, detail="Batch not found")
            
            sessions_created = []
            # Parse start date
            start_date = datetime.fromisoformat(batch["start_date"]).date()
            end_date_limit = start_date + timedelta(weeks=weeks)
           
            # Day name to weekday number mapping
            day_map = {
                "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
                "friday": 4, "saturday": 5, "sunday": 6
            }

                # Get weekday numbers for this batch
            batch_weekdays = [day_map[day.lower()] for day in batch["days_of_week"]]

            current_date = start_date

            while current_date < end_date_limit:
                if current_date.weekday() in batch_weekdays:
                    # Parse time
                    time_parts = batch["time"].split(":")
                    hour = int(time_parts[0])
                    minute = int(time_parts[1]) if len(time_parts) > 1 else 0
                    
                    # Create datetime
                    session_datetime = datetime.combine(
                        current_date,
                        datetime.min.time().replace(hour=hour, minute=minute)
                    ).replace(tzinfo=timezone.utc)
                    
                    end_datetime = session_datetime + timedelta(minutes=batch["duration_minutes"])
                    
                    # Create session document
                    session_doc = {
                        "id": str(uuid.uuid4()),
                        "listing_id": listing_id,
                        "batch_id": batch_id,
                        "start_at": session_datetime,
                        "end_at": end_datetime,
                        "date": current_date.isoformat(),
                        "time": batch["time"],
                        "duration_minutes": batch["duration_minutes"],
                        "seats_total": batch["capacity"],
                        "seats_booked": 0,
                        "status": "scheduled",
                        "is_rescheduled": False,
                        "original_date": None
                    }

                    await self.session_repo.add_session(session_doc)
                    sessions_created.append(session_doc["id"])
                current_date += timedelta(days=1)
            return {
                    "message": f"Generated {len(sessions_created)} sessions",
                    "sessions_count": len(sessions_created),
                    "batch_id": batch_id
                }

        except HTTPException:
            raise  # Re-raise HTTP exceptions
        except Exception as e:
            logging.error(f"Error in add_children: {e}")
            return []
        
    async def get_batch_sessions(self, listing_id, batch_id, from_date, to_date):
            try:
                query = {
                    "listing_id": listing_id,
                    "batch_id": batch_id,
                    "status": "scheduled"
                }
                
                if from_date:
                    query["date"] = {"$gte": from_date}
                
                if to_date:
                    if "date" in query:
                        query["date"]["$lte"] = to_date
                    else:
                        query["date"] = {"$lte": to_date}
                
                sessions = await self.session_repo.get_session(query)
                
                return {"sessions": sessions, "count": len(sessions)}
            except Exception as e:
                logging.error(f"Error in get_batch_sessions for listing {listing_id}, batch {batch_id}: {e}")
                return {"sessions": [], "count": 0}



