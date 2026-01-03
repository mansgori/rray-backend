@api_router.post("/partners")
async def create_partner(data: PartnerCreate, current_user: Dict = Depends(get_current_user)):
    # Allow partner_owner or admin to create partner profiles
    if current_user["role"] not in ["partner_owner", "admin", "customer"]:
        raise HTTPException(status_code=403, detail="Invalid role for partner creation")
    
    # Validate KYC documents if provided
    if data.pan_number and not validate_pan(data.pan_number):
        raise HTTPException(status_code=400, detail="Invalid PAN format. Format: ABCDE1234F")
    
    if data.aadhaar_number and not validate_aadhaar(data.aadhaar_number):
        raise HTTPException(status_code=400, detail="Invalid Aadhaar format. Must be 12 digits")
    
    if data.gst_number and not validate_gst(data.gst_number):
        raise HTTPException(status_code=400, detail="Invalid GST format")
    
    if data.bank_ifsc and not validate_ifsc(data.bank_ifsc):
        raise HTTPException(status_code=400, detail="Invalid IFSC code format")
    
    # Check if all KYC documents are submitted (now optional - just check if basic info is there)
    kyc_documents_submitted = bool(
        data.pan_number and
        data.aadhaar_number and
        data.bank_account_number and data.bank_ifsc and
        data.bank_account_holder_name
    )
    
    # Check if partner profile already exists
    existing_partner = await db.partners.find_one({"owner_user_id": current_user["id"]})
    if existing_partner:
        # Update existing partner instead of throwing error
        update_data = {
            "brand_name": data.brand_name,
            "legal_name": data.legal_name,
            "description": data.description,
            "address": data.address,
            "city": data.city,
            "updated_at": datetime.now(timezone.utc),
            "kyc_documents_submitted": kyc_documents_submitted
        }
        
        # Add KYC fields if provided
        if data.pan_number:
            update_data["pan_number"] = data.pan_number
        if data.pan_document:
            update_data["pan_document"] = data.pan_document
        if data.aadhaar_number:
            update_data["aadhaar_number"] = data.aadhaar_number
        if data.aadhaar_document:
            update_data["aadhaar_document"] = data.aadhaar_document
        if data.gst_number:
            update_data["gst_number"] = data.gst_number
        if data.gst_document:
            update_data["gst_document"] = data.gst_document
        if data.bank_account_number:
            update_data["bank_account_number"] = data.bank_account_number
        if data.bank_ifsc:
            update_data["bank_ifsc"] = data.bank_ifsc
        if data.bank_account_holder_name:
            update_data["bank_account_holder_name"] = data.bank_account_holder_name
        if data.bank_name:
            update_data["bank_name"] = data.bank_name
        if data.bank_account_type:
            update_data["bank_account_type"] = data.bank_account_type
        if data.cancelled_cheque_document:
            update_data["cancelled_cheque_document"] = data.cancelled_cheque_document
        if data.partner_photo:
            update_data["partner_photo"] = data.partner_photo
        
        # Legacy fields
        if data.gstin:
            update_data["gstin"] = data.gstin
        if data.pan:
            update_data["pan"] = data.pan
        if data.kyc_documents:
            update_data["kyc_documents"] = data.kyc_documents
        if data.bank_details:
            update_data["bank_details"] = data.bank_details
        if data.kyc_status:
            update_data["kyc_status"] = data.kyc_status
        
        await db.partners.update_one(
            {"owner_user_id": current_user["id"]},
            {"$set": update_data}
        )
        return {"id": existing_partner["id"], "partner": existing_partner, "updated": True}
    
    # Update user role to partner_owner if they're currently customer
    if current_user["role"] == "customer":
        await db.users.update_one(
            {"id": current_user["id"]},
            {"$set": {"role": "partner_owner"}}
        )
        # Issue new token with updated role
        new_token = create_token(current_user["id"], "partner_owner")
    else:
        new_token = None
    
    partner = Partner(
        owner_user_id=current_user["id"],
        brand_name=data.brand_name,
        legal_name=data.legal_name,
        description=data.description,
        address=data.address,
        city=data.city,
        pan_number=data.pan_number,
        pan_document=data.pan_document,
        aadhaar_number=data.aadhaar_number,
        aadhaar_document=data.aadhaar_document,
        gst_number=data.gst_number,
        gst_document=data.gst_document,
        bank_account_number=data.bank_account_number,
        bank_ifsc=data.bank_ifsc,
        bank_account_holder_name=data.bank_account_holder_name,
        bank_name=data.bank_name,
        bank_account_type=data.bank_account_type,
        cancelled_cheque_document=data.cancelled_cheque_document,
        partner_photo=data.partner_photo,
        kyc_documents_submitted=kyc_documents_submitted,
        gstin=data.gstin,
        pan=data.pan,
        kyc_documents=data.kyc_documents,
        bank_details=data.bank_details,
        kyc_status=data.kyc_status or "pending"
    )
    
    await db.partners.insert_one(partner.model_dump())
    
    # Create wallet for partner if doesn't exist
    existing_wallet = await db.wallets.find_one({"user_id": current_user["id"]})
    if not existing_wallet:
        wallet = Wallet(user_id=current_user["id"])
        await db.wallets.insert_one(wallet.model_dump())
    
    response = {"id": partner.id, "partner": partner.model_dump()}
    if new_token:
        response["new_token"] = new_token
    
    return response

@api_router.get("/partners/my")
async def get_my_partner(current_user: Dict = Depends(get_current_user)):
    if current_user["role"] not in ["partner_owner", "partner_staff"]:
        raise HTTPException(status_code=403, detail="Not a partner")
    
    partner = await db.partners.find_one({"owner_user_id": current_user["id"]}, {"_id": 0})
    
    # Auto-create partner profile if it doesn't exist
    if not partner:
        # Create a basic partner profile with user's information
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
            "action": "partner_auto_created",
            "entity_type": "partner",
            "entity_id": partner["id"],
            "details": {"auto_created": True},
            "created_at": datetime.now(timezone.utc)
        })
    
    return partner

@api_router.get("/partners/my/completion")
async def get_profile_completion(current_user: Dict = Depends(get_current_user)):
    """Calculate partner profile completion percentage"""
    if current_user["role"] not in ["partner_owner", "partner_staff"]:
        raise HTTPException(status_code=403, detail="Not a partner")
    
    partner = await db.partners.find_one({"owner_user_id": current_user["id"]}, {"_id": 0})
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    
    # Define completion criteria with weights
    sections = {
        "basic_info": {
            "weight": 40,
            "fields": ["brand_name", "legal_name", "description", "partner_photo"],
            "completed": 0,
            "total": 4
        },
        "address": {
            "weight": 10,
            "fields": ["address", "city"],
            "completed": 0,
            "total": 2
        },
        "kyc_documents": {
            "weight": 25,
            "fields": ["pan_number", "pan_document", "aadhaar_number", "aadhaar_document"],
            "completed": 0,
            "total": 4
        },
        "bank_details": {
            "weight": 25,
            "fields": ["bank_account_number", "bank_ifsc", "bank_account_holder_name", "bank_name", "bank_account_type"],
            "completed": 0,
            "total": 5
        }
    }
    
    # Calculate completion for each section
    for section_name, section_data in sections.items():
        for field in section_data["fields"]:
            value = partner.get(field)
            if value is not None and value != "" and value != []:
                section_data["completed"] += 1
    
    # Calculate total percentage
    total_percentage = 0
    section_percentages = {}
    missing_fields = []
    
    for section_name, section_data in sections.items():
        section_completion = (section_data["completed"] / section_data["total"]) * 100
        section_percentage = (section_completion / 100) * section_data["weight"]
        total_percentage += section_percentage
        
        section_percentages[section_name] = {
            "percentage": round(section_completion, 1),
            "completed": section_data["completed"],
            "total": section_data["total"],
            "weight": section_data["weight"]
        }
        
        # Track missing fields
        for field in section_data["fields"]:
            value = partner.get(field)
            if value is None or value == "" or value == []:
                missing_fields.append({
                    "field": field,
                    "section": section_name,
                    "label": field.replace("_", " ").title()
                })
    
    return {
        "total_percentage": round(total_percentage, 1),
        "sections": section_percentages,
        "missing_fields": missing_fields,
        "meets_minimum": total_percentage >= 70,
        "minimum_required": 70
    }

@api_router.put("/partners/profile")
async def update_partner_profile_details(
    profile_updates: Dict[str, Any],
    current_user: Dict = Depends(get_current_user)
):
    """Update partner profile details (description, KYC, bank info)"""
    if current_user["role"] not in ["partner_owner", "partner_staff"]:
        raise HTTPException(status_code=403, detail="Not a partner")
    
    partner = await db.partners.find_one({"owner_user_id": current_user["id"]})
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    
    # Allowed fields to update (safe fields that don't impact critical business logic)
    allowed_fields = [
        'description', 'partner_photo',
        'pan_number', 'aadhaar_number', 'gst_number',
        'bank_account_number', 'bank_ifsc', 'bank_account_holder_name',
        'bank_name', 'bank_account_type'
    ]
    
    # Filter updates to only allowed fields
    filtered_updates = {
        k: v for k, v in profile_updates.items() 
        if k in allowed_fields and v is not None and v != ''
    }
    
    if not filtered_updates:
        raise HTTPException(status_code=400, detail="No valid fields to update")
    
    # Add updated timestamp
    filtered_updates['updated_at'] = datetime.now(timezone.utc).isoformat()
    
    # Update partner profile
    await db.partners.update_one(
        {"owner_user_id": current_user["id"]},
        {"$set": filtered_updates}
    )
    
    return {
        "message": "Profile updated successfully",
        "updated_fields": list(filtered_updates.keys())
    }

@api_router.post("/partners/documents")
async def upload_partner_documents(
    pan_document: UploadFile = File(None),
    aadhaar_document: UploadFile = File(None),
    gst_document: UploadFile = File(None),
    cancelled_cheque_document: UploadFile = File(None),
    current_user: Dict = Depends(get_current_user)
):
    """Upload KYC and bank documents for partner"""
    if current_user["role"] not in ["partner_owner", "partner_staff"]:
        raise HTTPException(status_code=403, detail="Not a partner")
    
    partner = await db.partners.find_one({"owner_user_id": current_user["id"]})
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    
    updates = {}
    uploaded_docs = []
    
    # Process each document
    if pan_document:
        content = await pan_document.read()
        pan_base64 = base64.b64encode(content).decode('utf-8')
        updates['pan_document'] = f"data:{pan_document.content_type};base64,{pan_base64}"
        uploaded_docs.append('PAN Document')
    
    if aadhaar_document:
        content = await aadhaar_document.read()
        aadhaar_base64 = base64.b64encode(content).decode('utf-8')
        updates['aadhaar_document'] = f"data:{aadhaar_document.content_type};base64,{aadhaar_base64}"
        uploaded_docs.append('Aadhaar Document')
    
    if gst_document:
        content = await gst_document.read()
        gst_base64 = base64.b64encode(content).decode('utf-8')
        updates['gst_document'] = f"data:{gst_document.content_type};base64,{gst_base64}"
        uploaded_docs.append('GST Document')
    
    if cancelled_cheque_document:
        content = await cancelled_cheque_document.read()
        cheque_base64 = base64.b64encode(content).decode('utf-8')
        updates['cancelled_cheque_document'] = f"data:{cancelled_cheque_document.content_type};base64,{cheque_base64}"
        uploaded_docs.append('Cancelled Cheque')
    
    if not updates:
        raise HTTPException(status_code=400, detail="No documents provided")
    
    # Mark KYC as submitted if PAN and Aadhaar are uploaded
    if 'pan_document' in updates and 'aadhaar_document' in updates:
        updates['kyc_documents_submitted'] = True
        updates['kyc_status'] = 'submitted'
    
    updates['updated_at'] = datetime.now(timezone.utc).isoformat()
    
    # Update partner with documents
    await db.partners.update_one(
        {"owner_user_id": current_user["id"]},
        {"$set": updates}
    )
    
    return {
        "message": "Documents uploaded successfully",
        "uploaded_documents": uploaded_docs
    }

@api_router.get("/partners/my/stats")
async def get_partner_stats(current_user: Dict = Depends(get_current_user)):
    """Get dashboard stats for partner"""
    if current_user["role"] not in ["partner_owner", "partner_staff"]:
        raise HTTPException(status_code=403, detail="Not a partner")
    
    partner = await db.partners.find_one({"owner_user_id": current_user["id"]})
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    
    partner_id = partner["id"]
    
    # Get partner's listings first (limit to reasonable number)
    listings = await db.listings.find({"partner_id": partner_id}, {"id": 1}).to_list(500)
    listing_ids = [l["id"] for l in listings]
    
    # Get stats
    total_bookings = await db.bookings.count_documents({"listing_id": {"$in": listing_ids}})
    
    # Revenue this month
    start_of_month = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    revenue_pipeline = [
        {
            "$match": {
                "listing_id": {"$in": listing_ids},
                "booking_status": {"$in": ["confirmed", "attended"]},
                "booked_at": {"$gte": start_of_month}
            }
        },
        {
            "$group": {
                "_id": None,
                "total": {"$sum": "$total_inr"}
            }
        }
    ]
    revenue_result = await db.bookings.aggregate(revenue_pipeline).to_list(1)
    revenue_this_month = revenue_result[0]["total"] if revenue_result else 0.0
    
    # Active listings
    active_listings = await db.listings.count_documents({
        "partner_id": partner_id,
        "status": "active"
    })
    
    # Upcoming sessions
    upcoming_sessions = await db.sessions.count_documents({
        "listing_id": {"$in": listing_ids},
        "start_at": {"$gte": datetime.now(timezone.utc)},
        "status": "scheduled"
    })
    
    return {
        "total_bookings": total_bookings,
        "revenue_this_month": revenue_this_month,
        "active_listings": active_listings,
        "upcoming_sessions": upcoming_sessions,
        "pending_approvals": 0
    }

@api_router.get("/partners/my/bookings")
async def get_partner_bookings(
    limit: int = 10,
    current_user: Dict = Depends(get_current_user)
):
    """Get bookings for partner's listings"""
    if current_user["role"] not in ["partner_owner", "partner_staff"]:
        raise HTTPException(status_code=403, detail="Not a partner")
    
    partner = await db.partners.find_one({"owner_user_id": current_user["id"]})
    if not partner:
        return {"bookings": []}
    
    # Get partner's listings
    listings = await db.listings.find({"partner_id": partner["id"]}, {"id": 1, "title": 1}).to_list(500)
    listing_ids = [l["id"] for l in listings]
    listing_titles = {l["id"]: l["title"] for l in listings}
    
    # Get bookings
    bookings = await db.bookings.find(
        {"listing_id": {"$in": listing_ids}},
        {"_id": 0}
    ).sort("booked_at", -1).limit(limit).to_list(limit)
    
    # Enrich with listing title and session info
    for booking in bookings:
        booking["listing_title"] = listing_titles.get(booking["listing_id"], "Unknown")
        session = await db.sessions.find_one({"id": booking["session_id"]}, {"_id": 0})
        if session:
            # Handle both old (start_at) and new (date/time) session structures
            if "start_at" in session:
                booking["session_start"] = session["start_at"]
            elif "date" in session and "time" in session:
                # Convert date/time to datetime for compatibility
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
                    
                    booking["session_start"] = session_datetime
                except Exception as e:
                    logging.warning(f"Error parsing session date/time for booking {booking['id']}: {e}")
                    booking["session_start"] = None
    
    return {"bookings": bookings}


# ============== PARTNER BOOKING MANAGEMENT ==============
@api_router.get("/partner/bookings")
async def get_partner_bookings_advanced(
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    status: Optional[str] = None,
    listing_id: Optional[str] = None,
    session_id: Optional[str] = None,
    q: Optional[str] = None,
    page: int = 1,
    limit: int = 25,
    current_user: Dict = Depends(get_current_user)
):
    """Get bookings for partner's listings with advanced filtering"""
    if current_user["role"] not in ["partner_owner", "partner_staff"]:
        raise HTTPException(status_code=403, detail="Not a partner")
    
    # Get partner
    partner = await db.partners.find_one({"owner_user_id": current_user["id"]})
    if not partner:
        return {"items": [], "page": page, "total": 0}
    
    # Get partner's listings
    listings = await db.listings.find({"partner_id": partner["id"]}, {"id": 1, "title": 1}).to_list(500)
    listing_ids = [l["id"] for l in listings]
    listing_map = {l["id"]: l["title"] for l in listings}
    
    if not listing_ids:
        return {"items": [], "page": page, "total": 0}
    
    # Build query
    query = {"listing_id": {"$in": listing_ids}}
    
    # Add filters
    if status:
        query["booking_status"] = status
    if listing_id:
        query["listing_id"] = listing_id
    if session_id:
        query["session_id"] = session_id
    
    # Date range filter on session start_at
    if from_date or to_date:
        date_query = {}
        if from_date:
            date_query["$gte"] = datetime.fromisoformat(from_date.replace('Z', '+00:00'))
        if to_date:
            date_query["$lte"] = datetime.fromisoformat(to_date.replace('Z', '+00:00'))
        # We'll filter by session date after fetching
    
    # Text search in child name
    if q:
        query["child_profile_name"] = {"$regex": q, "$options": "i"}
    
    # Get total count
    total = await db.bookings.count_documents(query)
    
    # Get bookings with pagination
    skip = (page - 1) * limit
    bookings = await db.bookings.find(
        query,
        {"_id": 0}
    ).sort("booked_at", -1).skip(skip).limit(limit).to_list(limit)
    
    # Enrich with listing and session data
    items = []
    for booking in bookings:
        # Get session
        session = await db.sessions.find_one(
            {"id": booking["session_id"]},
            {"_id": 0, "start_at": 1, "seats_total": 1}
        )
        
        # Apply date filter if needed
        if session and (from_date or to_date):
            session_start = session["start_at"]
            if session_start.tzinfo is None:
                session_start = session_start.replace(tzinfo=timezone.utc)
            
            if from_date:
                from_dt = datetime.fromisoformat(from_date.replace('Z', '+00:00'))
                if session_start < from_dt:
                    continue
            if to_date:
                to_dt = datetime.fromisoformat(to_date.replace('Z', '+00:00'))
                if session_start > to_dt:
                    continue
        
        if session:
            # Get user info
            user = await db.users.find_one(
                {"id": booking["user_id"]},
                {"_id": 0, "name": 1, "email": 1, "phone": 1}
            )
            
            item = {
                "booking_id": booking["id"],
                "created_at": booking["booked_at"].isoformat() if booking["booked_at"] else None,
                "status": booking["booking_status"],
                "child": {
                    "name": booking["child_profile_name"],
                    "age_band": f"{booking['child_profile_age']}-{booking['child_profile_age']+1}"
                },
                "listing": {
                    "id": booking["listing_id"],
                    "title": listing_map.get(booking["listing_id"], "Unknown")
                },
                "session": {
                    "id": booking["session_id"],
                    "start_at": session["start_at"].isoformat() if session["start_at"] else None,
                    "seats_total": session.get("seats_total", 0)
                },
                "payment": {
                    "method": booking["payment_method"],
                    "total_inr": booking["total_inr"],
                    "credits_used": booking["credits_used"]
                },
                "attendance": booking.get("attendance"),
                "notes": booking.get("attendance_notes", ""),
                "customer": {
                    "name": user.get("name", "Unknown") if user else "Unknown",
                    "email": user.get("email", "") if user else "",
                    "phone": user.get("phone", "") if user else ""
                }
            }
            items.append(item)
    
    return {
        "items": items,
        "page": page,
        "total": total
    }

@api_router.put("/partner/bookings/{booking_id}/attendance")
async def mark_attendance(
    booking_id: str,
    request: AttendanceUpdateRequest,
    current_user: Dict = Depends(get_current_user)
):
    """Mark attendance for a booking"""
    if current_user["role"] not in ["partner_owner", "partner_staff"]:
        raise HTTPException(status_code=403, detail="Not a partner")
    
    # Validate status
    if request.status not in ["present", "absent", "late"]:
        raise HTTPException(status_code=400, detail="Invalid attendance status")
    
    # Validate notes length
    if request.notes and len(request.notes) > 240:
        raise HTTPException(status_code=400, detail="Notes too long (max 240 chars)")
    
    # Get booking
    booking = await db.bookings.find_one({"id": booking_id}, {"_id": 0})
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    # Verify partner owns this listing
    partner = await db.partners.find_one({"owner_user_id": current_user["id"]})
    if not partner:
        raise HTTPException(status_code=403, detail="Partner profile not found")
    
    listing = await db.listings.find_one(
        {"id": booking["listing_id"], "partner_id": partner["id"]},
        {"_id": 0, "id": 1}
    )
    if not listing:
        raise HTTPException(status_code=403, detail="Not your booking")
    
    # Determine payout eligibility
    payout_eligible = request.status == "present"
    
    # Update booking status based on attendance
    new_status = "attended" if request.status == "present" else "no_show"
    
    # Update booking
    await db.bookings.update_one(
        {"id": booking_id},
        {
            "$set": {
                "attendance": request.status,
                "attendance_notes": request.notes,
                "attendance_at": datetime.now(timezone.utc),
                "payout_eligible": payout_eligible,
                "booking_status": new_status
            }
        }
    )
    
    # Create audit log
    audit_entry = {
        "id": str(uuid.uuid4()),
        "actor_id": current_user["id"],
        "actor_role": current_user["role"],
        "action": "partner_mark_attendance",
        "resource_type": "booking",
        "resource_id": booking_id,
        "details": {
            "attendance": request.status,
            "notes": request.notes,
            "payout_eligible": payout_eligible
        },
        "timestamp": datetime.now(timezone.utc)
    }
    await db.audit_logs.insert_one(audit_entry)
    
    # TODO: Send review email if present (T+4h)
    
    return {
        "message": "Attendance marked successfully",
        "booking_id": booking_id,
        "attendance": request.status,
        "payout_eligible": payout_eligible
    }

@api_router.put("/partner/bookings/{booking_id}/cancel")
async def partner_cancel_booking(
    booking_id: str,
    request: PartnerCancelBookingRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    current_user: Dict = Depends(get_current_user)
):
    """Partner cancels a booking - issues full refund + goodwill credit"""
    if current_user["role"] not in ["partner_owner", "partner_staff"]:
        raise HTTPException(status_code=403, detail="Not a partner")
    
    # Get booking
    booking = await db.bookings.find_one({"id": booking_id}, {"_id": 0})
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    # Verify partner owns this listing
    partner = await db.partners.find_one({"owner_user_id": current_user["id"]})
    if not partner:
        raise HTTPException(status_code=403, detail="Partner profile not found")
    
    listing = await db.listings.find_one(
        {"id": booking["listing_id"], "partner_id": partner["id"]},
        {"_id": 0, "id": 1, "title": 1}
    )
    if not listing:
        raise HTTPException(status_code=403, detail="Not your booking")
    
    # Check if already canceled
    if booking["booking_status"] in ["canceled", "refunded"]:
        raise HTTPException(status_code=400, detail="Already canceled")
    
    # Get session
    session = await db.sessions.find_one({"id": booking["session_id"]}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get goodwill config
    config = await db.configs.find_one({"_id": "partner_cancel_goodwill"}, {"_id": 0})
    goodwill_credits = 5
    goodwill_inr = 100
    if config:
        goodwill_type = config.get("type", "credits")
        goodwill_amount = config.get("amount", 5)
        if goodwill_type == "credits":
            goodwill_credits = goodwill_amount
            goodwill_inr = 0
        else:
            goodwill_inr = goodwill_amount
            goodwill_credits = 0
    
    # Partner cancel = 100% refund + goodwill
    refund_amount = booking["total_inr"]
    refund_credits = booking["credits_used"]
    
    # Release seat
    await db.sessions.update_one({"id": booking["session_id"]}, {"$inc": {"seats_booked": -1}})
    
    # Refund credits + goodwill
    total_credits_refund = refund_credits + goodwill_credits
    if total_credits_refund > 0:
        await db.wallets.update_one(
            {"user_id": booking["user_id"]},
            {"$inc": {"credits_balance": total_credits_refund}}
        )
        # Create ledger entries
        if refund_credits > 0:
            ledger_entry = CreditLedger(
                user_id=booking["user_id"],
                delta=refund_credits,
                reason="refund",
                ref_booking_id=booking_id
            )
            await db.credit_ledger.insert_one(ledger_entry.model_dump())
        
        if goodwill_credits > 0:
            goodwill_entry = CreditLedger(
                user_id=booking["user_id"],
                delta=goodwill_credits,
                reason="goodwill",
                ref_booking_id=booking_id
            )
            await db.credit_ledger.insert_one(goodwill_entry.model_dump())
    
    # Update booking
    cancellation_message = f"Partner canceled: {request.reason}. {request.message or ''}"
    await db.bookings.update_one(
        {"id": booking_id},
        {
            "$set": {
                "booking_status": "canceled",
                "canceled_at": datetime.now(timezone.utc),
                "canceled_by": "partner",
                "cancellation_reason": cancellation_message,
                "refund_amount_inr": refund_amount,
                "refund_credits": refund_credits,
                "payout_eligible": False
            }
        }
    )
    
    # Create audit log
    audit_entry = {
        "id": str(uuid.uuid4()),
        "actor_id": current_user["id"],
        "actor_role": current_user["role"],
        "action": "partner_cancel_booking",
        "resource_type": "booking",
        "resource_id": booking_id,
        "details": {
            "reason": request.reason,
            "message": request.message,
            "refund_inr": refund_amount,
            "refund_credits": refund_credits,
            "goodwill_credits": goodwill_credits,
            "goodwill_inr": goodwill_inr
        },
        "timestamp": datetime.now(timezone.utc)
    }
    await db.audit_logs.insert_one(audit_entry)
    
    # Get customer info for notification
    user = await db.users.find_one({"id": booking["user_id"]}, {"_id": 0, "email": 1, "name": 1})
    
    # TODO: Send email notification to customer
    # TODO: Send email notification to admin
    
    return {
        "message": "Booking canceled successfully",
        "booking_id": booking_id,
        "refund_amount_inr": refund_amount,
        "refund_credits": refund_credits,
        "goodwill_credits": goodwill_credits,
        "goodwill_inr": goodwill_inr,
        "customer_email": user.get("email") if user else None
    }


# ============== PARTNER FINANCIALS & PAYOUTS ==============

class PayoutRequest(BaseModel):
    amount_inr: float
    bank_account_id: Optional[str] = None
    notes: Optional[str] = None

@api_router.get("/partner/financials/summary")
async def get_partner_financials_summary(current_user: Dict = Depends(get_current_user)):
    """Get partner's financial summary - earnings, pending payouts, available balance"""
    if current_user["role"] not in ["partner_owner", "partner_staff"]:
        raise HTTPException(status_code=403, detail="Not a partner")
    
    # Get partner
    partner = await db.partners.find_one({"owner_user_id": current_user["id"]}, {"_id": 0})
    if not partner:
        raise HTTPException(status_code=404, detail="Partner profile not found")
    
    # Get partner's listings
    listings = await db.listings.find({"partner_id": partner["id"]}, {"_id": 0, "id": 1}).to_list(500)
    listing_ids = [l["id"] for l in listings]
    
    if not listing_ids:
        return {
            "total_earnings_inr": 0,
            "available_balance_inr": 0,
            "pending_payout_inr": 0,
            "lifetime_earnings_inr": 0,
            "total_bookings": 0,
            "commission_rate": partner.get("commission_percent", 15.0),
            "currency": "INR"
        }
    
    # Get all payout-eligible bookings (attended status with payout_eligible=True)
    eligible_bookings = await db.bookings.find({
        "listing_id": {"$in": listing_ids},
        "booking_status": "attended",
        "payout_eligible": True
    }, {"_id": 0}).to_list(None)
    
    # Get all bookings for total count
    total_bookings = await db.bookings.count_documents({
        "listing_id": {"$in": listing_ids},
        "booking_status": {"$in": ["confirmed", "attended"]}
    })
    
    # Calculate gross earnings from eligible bookings
    gross_earnings = sum(b.get("total_inr", 0) for b in eligible_bookings)
    
    # Calculate commission
    commission_rate = partner.get("commission_percent", 15.0) / 100
    commission_amount = gross_earnings * commission_rate
    net_earnings = gross_earnings - commission_amount
    
    # Get pending payout requests
    pending_payouts = await db.payout_requests.find({
        "partner_id": partner["id"],
        "status": "pending"
    }, {"_id": 0}).to_list(None)
    pending_payout_amount = sum(p.get("amount_inr", 0) for p in pending_payouts)
    
    # Get completed payouts for lifetime earnings
    completed_payouts = await db.payout_requests.find({
        "partner_id": partner["id"],
        "status": "completed"
    }, {"_id": 0}).to_list(None)
    completed_payout_amount = sum(p.get("amount_inr", 0) for p in completed_payouts)
    
    # Available balance = net earnings - pending payouts - completed payouts
    available_balance = net_earnings - pending_payout_amount - completed_payout_amount
    
    return {
        "total_earnings_inr": round(net_earnings, 2),
        "available_balance_inr": round(available_balance, 2),
        "pending_payout_inr": round(pending_payout_amount, 2),
        "lifetime_earnings_inr": round(completed_payout_amount, 2),
        "total_bookings": total_bookings,
        "commission_rate": partner.get("commission_percent", 15.0),
        "currency": "INR",
        "gross_revenue_inr": round(gross_earnings, 2),
        "commission_paid_inr": round(commission_amount, 2)
    }


@api_router.get("/partner/financials/transactions")
async def get_partner_transactions(
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    transaction_type: Optional[str] = None,  # "booking" or "payout"
    page: int = 1,
    limit: int = 50,
    current_user: Dict = Depends(get_current_user)
):
    """Get partner's transaction history"""
    if current_user["role"] not in ["partner_owner", "partner_staff"]:
        raise HTTPException(status_code=403, detail="Not a partner")
    
    # Get partner
    partner = await db.partners.find_one({"owner_user_id": current_user["id"]}, {"_id": 0})
    if not partner:
        raise HTTPException(status_code=404, detail="Partner profile not found")
    
    # Get partner's listings
    listings = await db.listings.find({"partner_id": partner["id"]}, {"_id": 0, "id": 1, "title": 1}).to_list(500)
    listing_ids = [l["id"] for l in listings]
    listing_map = {l["id"]: l["title"] for l in listings}
    
    transactions = []
    
    # Build date filter
    date_filter = {}
    if from_date:
        date_filter["$gte"] = datetime.fromisoformat(from_date.replace('Z', '+00:00'))
    if to_date:
        date_filter["$lte"] = datetime.fromisoformat(to_date.replace('Z', '+00:00'))
    
    # Get bookings as transactions
    if not transaction_type or transaction_type == "booking":
        booking_query = {
            "listing_id": {"$in": listing_ids},
            "booking_status": {"$in": ["confirmed", "attended", "refunded"]}
        }
        if date_filter:
            booking_query["booked_at"] = date_filter
        
        bookings = await db.bookings.find(booking_query, {"_id": 0}).sort("booked_at", -1).to_list(1000)
        
        commission_rate = partner.get("commission_percent", 15.0) / 100
        
        for booking in bookings:
            gross_amount = booking.get("total_inr", 0)
            commission = gross_amount * commission_rate
            net_amount = gross_amount - commission
            
            transactions.append({
                "id": booking["id"],
                "type": "booking",
                "date": booking["booked_at"],
                "listing_title": listing_map.get(booking["listing_id"], "Unknown"),
                "child_name": booking.get("child_profile_name", "Unknown"),
                "gross_amount_inr": round(gross_amount, 2),
                "commission_inr": round(commission, 2),
                "net_amount_inr": round(net_amount, 2),
                "status": booking["booking_status"],
                "payout_eligible": booking.get("payout_eligible", False)
            })
    
    # Get payout requests as transactions
    if not transaction_type or transaction_type == "payout":
        payout_query = {"partner_id": partner["id"]}
        if date_filter:
            payout_query["requested_at"] = date_filter
        
        payouts = await db.payout_requests.find(payout_query, {"_id": 0}).sort("requested_at", -1).to_list(200)
        
        for payout in payouts:
            transactions.append({
                "id": payout["id"],
                "type": "payout",
                "date": payout["requested_at"],
                "amount_inr": payout["amount_inr"],
                "status": payout["status"],
                "notes": payout.get("notes", ""),
                "processed_at": payout.get("processed_at"),
                "reference_number": payout.get("reference_number", "")
            })
    
    # Sort by date
    transactions.sort(key=lambda x: x["date"], reverse=True)
    
    # Paginate
    total = len(transactions)
    start = (page - 1) * limit
    end = start + limit
    paginated = transactions[start:end]
    
    return {
        "transactions": paginated,
        "page": page,
        "total": total,
        "pages": (total + limit - 1) // limit if limit > 0 else 0
    }


@api_router.post("/partner/financials/payout-request")
async def request_payout(request: PayoutRequest, current_user: Dict = Depends(get_current_user)):
    """Request a payout"""
    if current_user["role"] not in ["partner_owner"]:
        raise HTTPException(status_code=403, detail="Only partner owners can request payouts")
    
    # Get partner
    partner = await db.partners.find_one({"owner_user_id": current_user["id"]}, {"_id": 0})
    if not partner:
        raise HTTPException(status_code=404, detail="Partner profile not found")
    
    # Validate bank details exist
    if not partner.get("bank_details"):
        raise HTTPException(status_code=400, detail="Please add bank details before requesting payout")
    
    # Get financial summary to check available balance
    summary_response = await get_partner_financials_summary(current_user)
    available_balance = summary_response["available_balance_inr"]
    
    # Validate amount
    if request.amount_inr <= 0:
        raise HTTPException(status_code=400, detail="Payout amount must be greater than 0")
    
    if request.amount_inr > available_balance:
        raise HTTPException(status_code=400, detail=f"Insufficient balance. Available: ₹{available_balance}")
    
    # Minimum payout amount check (e.g., ₹500)
    MIN_PAYOUT = 500
    if request.amount_inr < MIN_PAYOUT:
        raise HTTPException(status_code=400, detail=f"Minimum payout amount is ₹{MIN_PAYOUT}")
    
    # Create payout request
    payout_request = {
        "id": str(uuid.uuid4()),
        "partner_id": partner["id"],
        "partner_name": partner["brand_name"],
        "amount_inr": request.amount_inr,
        "status": "pending",
        "requested_at": datetime.now(timezone.utc),
        "bank_account_id": request.bank_account_id or partner.get("bank_details", {}).get("account_number", ""),
        "notes": request.notes or "",
        "processed_at": None,
        "reference_number": None
    }
    
    await db.payout_requests.insert_one(payout_request)
    
    # Create audit log
    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "action": "payout_requested",
        "actor_id": current_user["id"],
        "actor_role": current_user["role"],
        "target_id": payout_request["id"],
        "target_type": "payout_request",
        "details": {
            "partner_id": partner["id"],
            "amount_inr": request.amount_inr
        },
        "timestamp": datetime.now(timezone.utc)
    })
    
    # TODO: Send email notification to admin and partner
    
    return {
        "message": "Payout request submitted successfully",
        "payout_request_id": payout_request["id"],
        "amount_inr": request.amount_inr,
        "status": "pending"
    }


@api_router.get("/partner/financials/payout-requests")
async def get_partner_payout_requests(
    page: int = 1,
    limit: int = 20,
    current_user: Dict = Depends(get_current_user)
):
    """Get partner's payout request history"""
    if current_user["role"] not in ["partner_owner", "partner_staff"]:
        raise HTTPException(status_code=403, detail="Not a partner")
    
    # Get partner
    partner = await db.partners.find_one({"owner_user_id": current_user["id"]}, {"_id": 0})
    if not partner:
        raise HTTPException(status_code=404, detail="Partner profile not found")
    
    # Get payout requests
    total = await db.payout_requests.count_documents({"partner_id": partner["id"]})
    skip = (page - 1) * limit
    
    requests = await db.payout_requests.find(
        {"partner_id": partner["id"]},
        {"_id": 0}
    ).sort("requested_at", -1).skip(skip).limit(limit).to_list(limit)
    
    return {
        "requests": requests,
        "page": page,
        "total": total,
        "pages": (total + limit - 1) // limit if limit > 0 else 0
    }



@api_router.post("/partners/create")
async def create_partner_profile(
    brand_name: str,
    legal_name: str,
    address: str,
    city: str,
    description: str = "",
    kyc_documents: dict = {},
    bank_details: dict = {},
    current_user: Dict = Depends(get_current_user)
):
    """Create partner profile"""
    # Check if partner already exists
    existing = await db.partners.find_one({"owner_user_id": current_user["id"]})
    if existing:
        raise HTTPException(status_code=400, detail="Partner profile already exists")
    
    partner = {
        "id": str(uuid.uuid4()),
        "owner_user_id": current_user["id"],
        "brand_name": brand_name,
        "legal_name": legal_name,
        "address": address,
        "city": city,
        "description": description,
        "kyc_status": "pending",
        "kyc_documents": kyc_documents,
        "bank_details": bank_details,
        "commission_percent": 15.0,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }
    
    await db.partners.insert_one(partner)
    
    # Create audit log
    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "action": "partner_created",
        "entity_type": "partner",
        "entity_id": partner["id"],
        "details": {"brand_name": brand_name},
        "created_at": datetime.now(timezone.utc)
    })
    
    return {"id": partner["id"], "message": "Partner created successfully"}

@api_router.post("/partners/{partner_id}/venues")
async def create_venue(
    partner_id: str,
    data: VenueCreate,
    current_user: Dict = Depends(get_current_user)
):
    """Create venue for partner"""
    # Verify partner ownership
    partner = await db.partners.find_one({"id": partner_id, "owner_user_id": current_user["id"]})
    if not partner:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    venue = {
        "id": str(uuid.uuid4()),
        "partner_id": partner_id,
        "name": data.name,
        "address": data.address,
        "city": data.city,
        "pincode": data.pincode or "",
        "google_maps_link": data.google_maps_link or "",
        "is_active": True,
        "created_at": datetime.now(timezone.utc)
    }
    
    await db.venues.insert_one(venue)
    
    return {"id": venue["id"], "message": "Venue created successfully"}

@api_router.get("/partners/my/listings")
async def get_partner_listings(current_user: Dict = Depends(get_current_user)):
    """Get all listings for current partner"""
    if current_user["role"] not in ["partner_owner", "partner_staff"]:
        raise HTTPException(status_code=403, detail="Not a partner")
    
    partner = await db.partners.find_one({"owner_user_id": current_user["id"]})
    if not partner:
        return {"listings": []}
    
    listings = await db.listings.find(
        {"partner_id": partner["id"]},
        {"_id": 0}
    ).to_list(None)
    
    return {"listings": listings}

@api_router.get("/partners/{partner_id}/listings")

class TimeSlot(BaseModel):
    time: str
    seats: int

class BulkSessionCreate(BaseModel):
    listing_id: str
    start_date: str
    end_date: str
    days: List[str]
    time_slots: List[TimeSlot]
    duration_minutes: int = 60
    price_override: Optional[float] = None

@api_router.post("/sessions/bulk-create")
async def bulk_create_sessions(
    data: BulkSessionCreate,
    current_user: Dict = Depends(get_current_user)
):
    """Bulk create sessions with recurring pattern"""
    listing_id = data.listing_id
    start_date = data.start_date
    end_date = data.end_date
    days = data.days
    time_slots = data.time_slots
    duration_minutes = data.duration_minutes
    price_override = data.price_override
    if current_user["role"] not in ["partner_owner", "partner_staff"]:
        raise HTTPException(status_code=403, detail="Not a partner")
    
    # Verify listing ownership
    listing = await db.listings.find_one({"id": listing_id})
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    
    partner = await db.partners.find_one({"owner_user_id": current_user["id"]})
    if not partner or listing["partner_id"] != partner["id"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Parse dates
    from datetime import datetime, timedelta
    start = datetime.fromisoformat(start_date)
    end = datetime.fromisoformat(end_date)
    
    # Day mapping
    day_map = {
        'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
        'friday': 4, 'saturday': 5, 'sunday': 6
    }
    
    selected_weekdays = [day_map[day.lower()] for day in days if day.lower() in day_map]
    
    sessions_created = []
    current_date = start
    
    while current_date <= end:
        if current_date.weekday() in selected_weekdays:
            # Create session for each time slot
            for slot in time_slots:
                time_parts = slot.time.split(':')
                hour = int(time_parts[0])
                minute = int(time_parts[1]) if len(time_parts) > 1 else 0
                
                session_start = current_date.replace(
                    hour=hour, 
                    minute=minute, 
                    second=0, 
                    microsecond=0,
                    tzinfo=timezone.utc
                )
                
                session_end = session_start + timedelta(minutes=duration_minutes)
                
                session = Session(
                    id=str(uuid.uuid4()),
                    listing_id=listing_id,
                    start_at=session_start,
                    end_at=session_end,
                    seats_total=int(slot.seats),
                    seats_booked=0,
                    price_override_inr=price_override,
                    status="scheduled"
                )
                
                await db.sessions.insert_one(session.model_dump())
                sessions_created.append(session.id)
        
        current_date += timedelta(days=1)
    
    return {
        "message": f"Created {len(sessions_created)} sessions",
        "sessions_created": len(sessions_created)
    }

@api_router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """Delete a session"""
    if current_user["role"] not in ["partner_owner", "partner_staff", "admin"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Check if session has bookings
    bookings_count = await db.bookings.count_documents({"session_id": session_id})
    if bookings_count > 0:
        raise HTTPException(status_code=400, detail="Cannot delete session with existing bookings")
    
    result = await db.sessions.delete_one({"id": session_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {"message": "Session deleted successfully"}
