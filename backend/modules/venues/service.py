from fastapi import Request, HTTPException
from typing import Dict, Any
from typing import Optional
from datetime import datetime, timezone
import os
import logging
from backend.modules.venues.repositiry import VenueRepository
from backend.core.email_service.email_instance import email_service



class UserService:
    def __init__(self, 
                    venue_repo: VenueRepository,
                 ):
        self.venue_repo = venue_repo

    async def get_venue_details(self, venue_id: str):
        venue = await self.venue_repo.get_venue_by_id(venue_id)
        if not venue:
            raise HTTPException(status_code=404, detail="Venue not found")
        return venue
@api_router.post("/venues")
async def create_venue(data: VenueCreate, current_user: Dict = Depends(get_current_user)):
    """Create a new venue for partner"""
    if current_user["role"] not in ["partner_owner", "partner_staff"]:
        raise HTTPException(status_code=403, detail="Only partners can create venues")
    
    partner = await db.partners.find_one({"owner_user_id": current_user["id"]})
    
    # Auto-create partner profile if it doesn't exist (same as /partners/my)
    if not partner:
        user = await db.users.find_one({"id": current_user["id"]}, {"_id": 0})
        
        partner = {
            "id": str(uuid.uuid4()),
            "owner_user_id": current_user["id"],
            "brand_name": user.get("name", "My Studio"),
            "legal_name": user.get("name", ""),
            "email": user.get("email", ""),
            "phone": user.get("phone", ""),
            "address": "",
            "city": "",
            "description": "",
            "kyc_status": "pending",
            "kyc_documents": {},
            "bank_details": {},
            "commission_percent": 15.0,
            "partner_photo": "",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        
        await db.partners.insert_one(partner)
        
        # Create audit log
        await db.audit_logs.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": current_user["id"],
            "action": "partner_auto_created_venue",
            "entity_type": "partner",
            "entity_id": partner["id"],
            "details": {"auto_created": True, "trigger": "venue_creation"},
            "created_at": datetime.now(timezone.utc)
        })
    
    # Geocode address using Google Maps API (optional)
    lat, lng = None, None
    if GOOGLE_MAPS_API_KEY:
        try:
            full_address = f"{data.address}, {data.city}, {data.pincode or ''}"
            gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)
            geocode_result = gmaps.geocode(full_address)
            
            if geocode_result:
                location = geocode_result[0]['geometry']['location']
                lat = location['lat']
                lng = location['lng']
        except Exception as e:
            print(f"Geocoding error: {e}")
    
    venue = Venue(
        partner_id=partner["id"],
        name=data.name,
        address=data.address,
        city=data.city,
        pincode=data.pincode,
        google_maps_link=data.google_maps_link,
        landmarks=data.landmarks,
        lat=lat,
        lng=lng
    )
    
    await db.venues.insert_one(venue.model_dump())
    return {"id": venue.id, "venue": venue.model_dump()}

@api_router.get("/venues/my")
async def get_my_venues(current_user: Dict = Depends(get_current_user)):
    """Get all venues for current partner"""
    if current_user["role"] not in ["partner_owner", "partner_staff"]:
        raise HTTPException(status_code=403, detail="Only partners can access venues")
    
    partner = await db.partners.find_one({"owner_user_id": current_user["id"]})
    
    # Auto-create partner profile if it doesn't exist
    if not partner:
        user = await db.users.find_one({"id": current_user["id"]}, {"_id": 0})
        
        partner = {
            "id": str(uuid.uuid4()),
            "owner_user_id": current_user["id"],
            "brand_name": user.get("name", "My Studio"),
            "legal_name": user.get("name", ""),
            "email": user.get("email", ""),
            "phone": user.get("phone", ""),
            "address": "",
            "city": "",
            "description": "",
            "kyc_status": "pending",
            "kyc_documents": {},
            "bank_details": {},
            "commission_percent": 15.0,
            "partner_photo": "",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        
        await db.partners.insert_one(partner)
        
        # Create audit log
        await db.audit_logs.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": current_user["id"],
            "action": "partner_auto_created_venues",
            "entity_type": "partner",
            "entity_id": partner["id"],
            "details": {"auto_created": True, "trigger": "venues_fetch"},
            "created_at": datetime.now(timezone.utc)
        })
    
    venues = await db.venues.find(
        {"partner_id": partner["id"], "is_active": True},
        {"_id": 0}
    ).to_list(None)
    
    return {"venues": venues}

@api_router.get("/venues/{venue_id}")
async def get_venue(venue_id: str, current_user: Dict = Depends(get_current_user)):
    """Get specific venue details"""
    venue = await db.venues.find_one({"id": venue_id}, {"_id": 0})
    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")
    
    # Verify partner owns this venue
    if current_user["role"] in ["partner_owner", "partner_staff"]:
        partner = await db.partners.find_one({"owner_user_id": current_user["id"]})
        if partner and venue["partner_id"] != partner["id"]:
            raise HTTPException(status_code=403, detail="Not authorized to access this venue")
    
    return venue

@api_router.put("/venues/{venue_id}")
async def update_venue(venue_id: str, data: VenueCreate, current_user: Dict = Depends(get_current_user)):
    """Update venue details"""
    if current_user["role"] not in ["partner_owner", "partner_staff"]:
        raise HTTPException(status_code=403, detail="Only partners can update venues")
    
    partner = await db.partners.find_one({"owner_user_id": current_user["id"]})
    if not partner:
        raise HTTPException(status_code=404, detail="Partner profile not found")
    
    venue = await db.venues.find_one({"id": venue_id})
    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")
    
    if venue["partner_id"] != partner["id"]:
        raise HTTPException(status_code=403, detail="Not authorized to update this venue")
    
    # Geocode new address if changed
    lat, lng = venue.get("lat"), venue.get("lng")
    if GOOGLE_MAPS_API_KEY and (data.address != venue.get("address") or data.city != venue.get("city")):
        try:
            full_address = f"{data.address}, {data.city}, {data.pincode or ''}"
            gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)
            geocode_result = gmaps.geocode(full_address)
            
            if geocode_result:
                location = geocode_result[0]['geometry']['location']
                lat = location['lat']
                lng = location['lng']
        except Exception as e:
            print(f"Geocoding error: {e}")
    
    await db.venues.update_one(
        {"id": venue_id},
        {
            "$set": {
                "name": data.name,
                "address": data.address,
                "city": data.city,
                "pincode": data.pincode,
                "google_maps_link": data.google_maps_link,
                "landmarks": data.landmarks,
                "lat": lat,
                "lng": lng,
                "updated_at": datetime.now(timezone.utc)
            }
        }
    )
    
    return {"message": "Venue updated successfully"}

@api_router.delete("/venues/{venue_id}")
async def delete_venue(venue_id: str, current_user: Dict = Depends(get_current_user)):
    """Soft delete a venue"""
    if current_user["role"] not in ["partner_owner", "partner_staff"]:
        raise HTTPException(status_code=403, detail="Only partners can delete venues")
    
    partner = await db.partners.find_one({"owner_user_id": current_user["id"]})
    if not partner:
        raise HTTPException(status_code=404, detail="Partner profile not found")
    
    venue = await db.venues.find_one({"id": venue_id})
    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")
    
    if venue["partner_id"] != partner["id"]:
        raise HTTPException(status_code=403, detail="Not authorized to delete this venue")
    
    # Check if venue is used by any active listings
    active_listings = await db.listings.count_documents({"venue_id": venue_id, "status": "active"})
    if active_listings > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete venue. {active_listings} active listings are using this venue"
        )
    
    # Soft delete
    await db.venues.update_one(
        {"id": venue_id},
        {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc)}}
    )
    
    return {"message": "Venue deleted successfully"}