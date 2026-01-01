from fastapi import Request, HTTPException
from typing import Dict, Any
from typing import Optional
from datetime import datetime, timezone, timedelta
import os
import logging
from backend.modules.auth.repository import AuthRepository
from backend.modules.wallet.repository import WalletRepository
from backend.modules.users.repository import UserRepository
from backend.modules.listing.repository import ListingRepository
from backend.modules.partner.repository import PartnerRepository
from backend.core.email_service.email_instance import email_service
from backend.modules.listing.utility import calculate_distance_km, format_distance



class ListingService:
    def __init__(self, 
                 auth_repo: AuthRepository,
                 wallet_repo:WalletRepository,
                 user_repo:UserRepository,
                 listing_repo:ListingRepository,
                 partner_repo:PartnerRepository
                 ):
        self.auth_repo = auth_repo
        self.wallet_repo = wallet_repo
        self.user_repo = user_repo
        self.listing_repo = listing_repo
        self.partner_repo = partner_repo
    
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

    
