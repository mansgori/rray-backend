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
from backend.modules.booking.repository import BookingRepository
from backend.modules.invoice.repository import InvoiceRepository
from backend.modules.wallet.models import CreditLedger
from backend.modules.booking.models import Booking, BookingStatus




class BookingService:
    def __init__(self, 
                 auth_repo: AuthRepository,
                 wallet_repo:WalletRepository,
                 user_repo:UserRepository,
                 listing_repo:ListingRepository,
                 partner_repo:PartnerRepository,
                 session_repo:SessionRepository,
                 booking_repo:BookingRepository,
                 invoice_repo:InvoiceRepository
                 ):
        self.auth_repo = auth_repo
        self.wallet_repo = wallet_repo
        self.user_repo = user_repo
        self.listing_repo = listing_repo
        self.partner_repo = partner_repo
        self.session_repo = session_repo
        self.booking_repo = booking_repo
        self.invoice_repo = invoice_repo

    async def create_booking_v2(self, booking_data, current_user):
        try:
            if current_user["role"] != "customer":
                raise HTTPException(status_code=403, detail="Only customers can create bookings")
            
            listing = await self.listing_repo.get_listing_by_id(booking_data.listing_id)
            
            if not listing:
                raise HTTPException(status_code=404, detail="Listing not found")
            
            # Find plan option
            plan_option = next(
                (p for p in listing.get("plan_options", []) if p["id"] == booking_data.plan_option_id),
                None
            )
            if not plan_option:
                raise HTTPException(status_code=404, detail="Plan option not found")
            
                # Find batch (only for FIXED timing plans)
            batch = None
            timing_type = plan_option.get("timing_type", "FLEXIBLE")

            if timing_type == "FIXED" or (booking_data.batch_id and booking_data.batch_id != ""):
                batch = next(
                    (b for b in listing.get("batches", []) if b["id"] == booking_data.batch_id),
                    None
                )
                if not batch and booking_data.batch_id:
                    raise HTTPException(status_code=404, detail="Batch not found")
                
                # Check batch capacity
                if batch and batch.get("enrolled_count", 0) >= batch["capacity"]:
                    raise HTTPException(status_code=400, detail="Batch is full")
            
            # Validate session count matches plan
            if len(booking_data.session_ids) != plan_option["sessions_count"]:
                raise HTTPException(
                    status_code=400,
                    detail=f"Plan requires {plan_option['sessions_count']} sessions, but {len(booking_data.session_ids)} provided"
                )
            
            session_ids = booking_data.session_ids
            sessions = await self.session_repo.session_belong_to_listing(session_ids)

            # For FIXED timing, verify all sessions belong to the same batch
            if timing_type == "FIXED" and batch:
                for session in sessions:
                    if session.get("batch_id") != booking_data.batch_id:
                        raise HTTPException(status_code=400, detail="All sessions must be from the same batch")
                    
            # For FLEXIBLE timing, just verify sessions belong to the listing
            for session in sessions:
                if session.get("listing_id") != booking_data.listing_id:
                    raise HTTPException(status_code=400, detail="All sessions must be from this listing")
            
            # Calculate pricing
            total_price = plan_option["price_inr"]
            tax = total_price * (listing.get("tax_percent", 18.0) / 100)
            total_with_tax = total_price + tax
            
            # Handle credits
            credits_used = 0
            if booking_data.use_credits:
                wallet = await self.wallet_repo.find_wallet_by_id(current_user["id"])
                if wallet and wallet.get("credits_balance", 0) > 0:
                    credits_used = min(wallet["credits_balance"], int(total_with_tax))
                    total_with_tax -= credits_used
            
            # Create bookings for each session
            booking_ids = []
            for session in sessions:
                booking = {
                    "id": str(uuid.uuid4()),
                    "user_id": current_user["id"],
                    "session_id": session["id"],
                    "listing_id": booking_data.listing_id,
                    "child_profile_name": booking_data.child_profile_name,
                    "child_profile_age": booking_data.child_profile_age,
                    "qty": 1,
                    "unit_price_inr": plan_option["price_inr"] / plan_option["sessions_count"],
                    "taxes_inr": tax / plan_option["sessions_count"],
                    "total_inr": total_with_tax / plan_option["sessions_count"],
                    "credits_used": credits_used / plan_option["sessions_count"] if credits_used > 0 else 0,
                    "payment_method": booking_data.payment_method,
                    "booking_status": "confirmed",
                    "booked_at": datetime.now(timezone.utc),
                    "is_trial": plan_option["plan_type"] == "trial",
                    "plan_option_id": booking_data.plan_option_id,
                    "batch_id": booking_data.batch_id,
                    "session_ids": booking_data.session_ids
                }
                await self.booking_repo.add_booking(booking)
                booking_ids.append(booking["id"])
                
                # Update session seats
                await self.session_repo.update_session(session["id"])
                listing_id = booking_data.listing_id
                batch_id = booking_data.batch_id
                inc_data = {"batches.$.enrolled_count": 1}
            # Update batch enrollment count
            await self.listing_repo.update_listing(listing_id, batch_id, inc_data)


            # Deduct credits if used
            if credits_used > 0:
                id = current_user["id"]
                await self.wallet_repo.update_wallet(id, credits_used)

                credit_ledger = {
                    "id": str(uuid.uuid4()),
                    "user_id": current_user["id"],
                    "delta": -credits_used,
                    "reason": "booking",
                    "ref_booking_id": booking_ids[0],
                    "created_at": datetime.now(timezone.utc)
                }
                
                # Log credit usage
                await self.wallet_repo.create_credit_ledger(credit_ledger)
            
            return {
                "message": "Booking successful",
                "booking_ids": booking_ids,
                "total_paid": total_with_tax,
                "credits_used": credits_used
            }
        except HTTPException:
            raise  # Re-raise HTTP exceptions
        except Exception as e:
            logging.error(f"Error in add_children: {e}")
            return []
        
    async def get_booking_options(self, listing_id):
        try:
            listing = await self.listing_repo.get_listing_by_id(listing_id)
            
            if not listing:
                raise HTTPException(status_code=404, detail="Listing not found")
            
            # Get active plan options
            plan_options = [p for p in listing.get("plan_options", []) if p.get("is_active", True)]
            
            # Get active batches with availability
            batches = []
            for batch in listing.get("batches", []):
                if not batch.get("is_active", True):
                    continue
                
                available_seats = batch["capacity"] - batch.get("enrolled_count", 0)
                batches.append({
                    **batch,
                    "available_seats": available_seats,
                    "is_full": available_seats <= 0
                })
            
            return {
                "listing": {
                    "id": listing["id"],
                    "title": listing["title"],
                    "description": listing.get("description"),
                    "media": listing.get("media", []),
                    "tax_percent": listing.get("tax_percent", 18.0)
                },
                "plan_options": plan_options,
                "batches": batches
            }
        except HTTPException:
            raise  # Re-raise HTTP exceptions
        except Exception as e:
            logging.error(f"Error in add_children: {e}")
            return []
        
    async def check_trial_eligibility(self, listing_id, current_user):
        try:
            id = current_user["id"]
            existing_trial = await self.booking_repo.eligible_for_trial_booking(id, listing_id)

            if existing_trial:
                return {
                    "eligible": False,
                    "reason": "You have already taken a trial class for this listing",
                    "trials_left": 0
                }
            # Check trials booked in the last 7 days
            date = datetime.now(timezone.utc) - timedelta(days=7)
            trials_this_week = await self.booking_repo.check_trial_booking_this_week(id, date)

            if trials_this_week >= 2:
                return {
                    "eligible": False,
                    "reason": "You have reached the limit of 2 trial classes per week",
                    "trials_left": 0
                }
            
            return {
                "eligible": True,
                "trials_left": 2 - trials_this_week,
                "message": "You can book this trial class"
            }
        except HTTPException:
            raise  # Re-raise HTTP exceptions
        except Exception as e:
            logging.error(f"Error in add_children: {e}")
            return []
        
    async def create_booking(self, data, current_user):
        try: 
            # Allow customers and partners to create bookings for themselves/their kids
            if current_user["role"] not in ["customer", "partner_owner", "partner_staff"]:
                raise HTTPException(status_code=403, detail="Access denied")
            
            # Validate trial eligibility if this is a trial booking
            if data.is_trial:
                # Check if listing offers trial
                listing_check = await self.listing_repo.get_listing_by_id(listing_id = data.session_id)
                if not listing_check:
                    session_check = await self.session_repo.get_session_by_id(session_id = data.session_id)
                    if session_check:
                        listing_check = await self.listing_repo.get_listing_by_id(listing_id = session_check["listing_id"])
                        
                
                if not listing_check or not listing_check.get("trial_available"):
                    raise HTTPException(status_code=400, detail="Trial not available for this class")
                
                # Check if already booked trial for this listing
                existing_trial = await self.booking_repo.eligible_for_trial_booking(id = current_user["id"], listing_id = listing_check["id"])
                
                if existing_trial:
                    raise HTTPException(status_code=400, detail="You have already booked a trial for this class")
                
                # Check weekly trial limit (2 per week)
                week_ago = datetime.now(timezone.utc) - timedelta(days=7)
                trials_this_week = await self.booking_repo.check_trial_booking_this_week(id, date = week_ago)
                
                if trials_this_week >= 2:
                    raise HTTPException(status_code=400, detail="You have reached the limit of 2 trial classes per week")
            
            # Get session
            session = await self.session_repo.get_session_by_id(session_id = data.session_id)
            if not session:
                raise HTTPException(status_code=404, detail="Session not found")
            
            # Check bookability
            if session["status"] != "scheduled":
                raise HTTPException(status_code=400, detail="Session not available")
            
            now = datetime.now(timezone.utc)
            
            # Handle both old (start_at) and new (date/time) session structures
            if "start_at" in session:
                session_start = session["start_at"]
                # Convert string to datetime if needed
                if isinstance(session_start, str):
                    session_start = datetime.fromisoformat(session_start.replace('Z', '+00:00'))
                elif session_start.tzinfo is None:
                    session_start = session_start.replace(tzinfo=timezone.utc)
            elif "date" in session and "time" in session:
                # Convert date/time to datetime
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
                    
                    session_start = session_date.replace(
                        hour=hour,
                        minute=minute,
                        second=0,
                        microsecond=0,
                        tzinfo=timezone.utc
                    )
                except Exception as e:
                    logging.error(f"Error parsing session date/time: {e}")
                    raise HTTPException(status_code=500, detail="Invalid session date/time format")
            else:
                raise HTTPException(status_code=500, detail="Session missing date/time information")
            
            cutoff = session_start - timedelta(minutes=session.get("allow_late_booking_minutes", 60))
            if now >= cutoff:
                raise HTTPException(status_code=400, detail="Booking window closed")
            
            # Atomic seat reservation
            result = await self.session_repo.atomic_seat_reservation(session_id=data.session_id, seats_total=session["seats_total"])
 
            
            if result.modified_count == 0:
                raise HTTPException(status_code=400, detail="No seats available")
            
            # Get listing for pricing
            listing = await self.listing_repo.get_listing_by_id(listing_id = session["listing_id"])
            if not listing:
                raise HTTPException(status_code=404, detail="Listing not found")
            
            # Use trial price if this is a trial booking
            if data.is_trial and listing.get("trial_available"):
                unit_price = listing.get("trial_price_inr") or listing["base_price_inr"]
            else:
                # Use session price if available, otherwise listing base price
                unit_price = session.get("price_inr") or session.get("price_override_inr") or listing["base_price_inr"]
            
            # Calculate taxes (use 0 if tax_percent not defined)
            tax_percent = listing.get("tax_percent", 0)
            taxes = unit_price * (tax_percent / 100)
            total = unit_price + taxes
            
            # Handle payment
            credits_used = 0
            payment_txn_id = None
            
            if data.use_credits:
                # Calculate credit cost based on total price (including taxes)
                # 1 credit = ₹1 (simpler conversion)
                credit_cost = int(total)
                
                # Check wallet
                wallet = await self.wallet_repo.find_wallet_by_id(id = current_user["id"])
                if not wallet or wallet["credits_balance"] < credit_cost:
                    # Rollback seat
                    await self.session_repo.update_session(session_id= data.session_id)
                    raise HTTPException(status_code=400, detail="Insufficient credits")
                
                # Deduct credits
                await self.wallet_repo.update_wallet(id= current_user["id"], credits_used=credit_cost)

                
                # Log ledger
                ledger_entry = CreditLedger(
                    user_id=current_user["id"],
                    delta=-credit_cost,
                    reason="booking"
                )
                await self.wallet_repo.create_credit_ledger(creadit_leadger=ledger_entry)
                
                credits_used = credit_cost
                total = 0  # Credits cover it
            else:
                # Mock payment
                if os.environ.get("PAYMENTS_MODE") == "mock":
                    payment_txn_id = f"mock_{uuid.uuid4().hex[:12]}"
                else:
                    # TODO: Integrate Razorpay
                    payment_txn_id = f"razorpay_{uuid.uuid4().hex[:12]}"
            
            # Create booking
            booking = Booking(
                user_id=current_user["id"],
                session_id=data.session_id,
                listing_id=session["listing_id"],
                child_profile_name=data.child_profile_name,
                child_profile_age=data.child_profile_age,
                qty=1,
                unit_price_inr=unit_price,
                taxes_inr=taxes,
                total_inr=total,
                credits_used=credits_used,
                payment_method=data.payment_method,
                payment_txn_id=payment_txn_id,
                booking_status=BookingStatus.confirmed,
                is_trial=data.is_trial
            )
            
            await self.booking_repo.add_booking(booking_doc=booking)
            
            # AUTO-GENERATE INVOICE for this booking
            try:
                logging.info(f"Starting invoice generation for booking {booking.id}")
                
                # Generate invoice number
                today = datetime.now(timezone.utc)
                date_str = today.strftime("%Y%m%d")
                count = await self.invoice_repo.generate_invoice_number(date= date_str)
                invoice_number = f"INV-{date_str}-{str(count + 1).zfill(4)}"
                
                logging.info(f"Generated invoice number: {invoice_number}")
                
                # Get partner name from partner user
                projection = {"name": 1, "business_name": 1}
                partner = await self.auth_repo.find_user_by_id(id = listing.get("partner_id"),filter=projection )
                partner_name = partner.get("business_name", partner.get("name", "")) if partner else ""
                
                # Create invoice
                invoice = {
                    "id": str(uuid.uuid4()),
                    "invoice_number": invoice_number,
                    "booking_id": booking.id,
                    "customer_id": current_user["id"],
                    "customer_name": current_user.get("name", ""),
                    "customer_email": current_user.get("email", ""),
                    "partner_id": listing.get("partner_id", ""),
                    "partner_name": partner_name,
                    "listing_title": listing["title"],
                    "items": [{
                        "description": listing["title"],
                        "quantity": 1,
                        "unit_price": unit_price,
                        "total": unit_price
                    }],
                    "subtotal": unit_price,
                    "discount": 0,
                    "credits_used": credits_used,
                    "credits_value": credits_used,
                    "total_inr": total,
                    "payment_method": data.payment_method,
                    "payment_status": "completed",
                    "invoice_date": today,
                    "paid_date": today,
                    "status": "paid",
                    "gst_amount": taxes,
                    "session_date": session_start if 'session_start' in locals() else today,
                    "session_duration": listing.get("session_duration", 60)
                }
                
                logging.info(f"Invoice object created, inserting into database...")
                await self.invoice_repo.add_invoice(data = invoice)
                logging.info(f"✅ Auto-generated invoice {invoice_number} for booking {booking.id}")
            except Exception as e:
                logging.error(f"❌ Failed to auto-generate invoice for booking {booking.id}: {e}")
                logging.exception("Full traceback:")
                # Don't fail the booking if invoice generation fails
            
            return {"booking": booking.model_dump(), "message": "Booking confirmed!"}
        except HTTPException:
            raise  # Re-raise HTTP exceptions
        except Exception as e:
            logging.error(f"Error in add_children: {e}")
            return []

    async def create_plan_booking(self, data, current_user):
        try:
            if current_user["role"] not in ["customer", "partner_owner", "partner_staff"]:
                raise HTTPException(status_code=403, detail="Access denied")
            
            listing = await self.listing_repo.get_listing_by_id(listing_id=data.listing_id)
            if not listing:
                raise HTTPException(status_code=404, detail="Listing not found")
            
            base_price = listing.get("base_price_inr", 1000)
            plan_config = {
            "trial": {"sessions": 1, "discount": 0, "price_multiplier": 1.0, "is_trial": True},
            "single": {"sessions": 1, "discount": 0, "price_multiplier": 1.0, "is_trial": False},
            "weekly": {"sessions": 4, "discount": 10, "price_multiplier": 0.9, "is_trial": False},
            "monthly": {"sessions": 12, "discount": 25, "price_multiplier": 0.75, "is_trial": False},
            "quarterly": {"sessions": 36, "discount": 35, "price_multiplier": 0.65, "is_trial": False}
            }
            
            if data.plan_id not in plan_config:
                raise HTTPException(status_code=400, detail="Invalid plan")
            
            plan = plan_config[data.plan_id]
            sessions_to_book = plan["sessions"]
            is_trial = plan["is_trial"]

               # Validate trial eligibility if trial booking
            if is_trial:
                if not listing.get("trial_available"):
                    raise HTTPException(status_code=400, detail="Trial not available for this class")

                existing_trial = await self.booking_repo.eligible_for_trial_booking(id=current_user["id"], listing_id=listing["id"])

                if existing_trial:
                    raise HTTPException(status_code=400, detail="You have already booked a trial for this class")
                
                week_ago = datetime.now(timezone.utc) - timedelta(days=7)
                trials_this_week = await self.booking_repo.check_trial_booking_this_week(id=current_user["id"], date=week_ago)
                if trials_this_week >= 2:
                    raise HTTPException(status_code=400, detail="You have reached the limit of 2 trial classes per week")
                
                # Validate session IDs
            if not data.session_ids or len(data.session_ids) != sessions_to_book:
                raise HTTPException(
                    status_code=400,
                    detail=f"Please select exactly {sessions_to_book} session(s). You selected {len(data.session_ids)}."
                )
            # Get the selected sessions
            selected_sessions = await self.session_repo.selected_sessions(
                id=data.session_ids,
                listing_id=data.listing_id,
                sessions_to_book=sessions_to_book
            )

            if len(selected_sessions) != sessions_to_book:
                raise HTTPException(
                    status_code=400,
                    detail=f"One or more selected sessions are invalid or no longer available"
                )
            
            # Sort sessions by date/time
            def get_session_datetime(session):
                if "start_at" in session:
                    return session["start_at"]
                else:
                    # Parse date/time for new format
                    date_obj = datetime.fromisoformat(session["date"])
                    time_str = session["time"]
                    if isinstance(time_str, str):
                        time_parts = time_str.split(':')
                        hour = int(time_parts[0])
                        minute = int(time_parts[1]) if len(time_parts) > 1 else 0
                    else:
                        hour = time_str.hour if hasattr(time_str, 'hour') else 0
                        minute = time_str.minute if hasattr(time_str, 'minute') else 0
                    return date_obj.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            selected_sessions.sort(key=get_session_datetime)

            # Calculate pricing
            if is_trial:
                unit_price = listing.get("trial_price_inr", base_price)
                total_price = unit_price
            else:
                price_per_session = int(base_price * plan["price_multiplier"])
                total_price = price_per_session * sessions_to_book
            
            tax_percent = listing.get("tax_percent", 0)
            taxes = total_price * (tax_percent / 100)
            grand_total = total_price + taxes

            # Handle payment
            credits_used = 0
            payment_txn_id = None
            
            if data.use_credits:
                # 1 credit = ₹1 (includes taxes in grand_total)
                credit_cost = int(grand_total)
                
                wallet = await self.wallet_repo.find_wallet_by_id(id=current_user["id"])
                if not wallet or wallet["credits_balance"] < credit_cost:
                    raise HTTPException(status_code=400, detail="Insufficient credits")
                
                await self.wallet_repo.update_wallet(id=current_user["id"], credits_used=credit_cost)
                
                ledger_entry = CreditLedger(
                    user_id=current_user["id"],
                    delta=-credit_cost,
                    reason="booking"
                )
                await self.wallet_repo.create_credit_ledger(creadit_leadger=ledger_entry)
                
                credits_used = credit_cost
                grand_total = 0
            else:
                if os.environ.get("PAYMENTS_MODE") == "mock":
                    payment_txn_id = f"mock_{uuid.uuid4().hex[:12]}"
                else:
                    payment_txn_id = f"razorpay_{uuid.uuid4().hex[:12]}"
            
            # Create bookings for each selected session
            booking_ids = []
            for session in selected_sessions:
                # Reserve seat
                result = await self.session_repo.atomic_seat_reservation(session_id=session["id"], seats_total=session["seats_total"])
                
                if result.modified_count == 0:
                    # Rollback previous reservations
                    for prev_booking_id in booking_ids:
                        prev_booking = await self.booking_repo.find_booking(bookind_id=prev_booking_id)
                        if prev_booking:
                            await self.session_repo.update_session(session_id= prev_booking["session_id"])

                            await self.session_repo.delete_session(session_id=prev_booking_id)
                    
                    raise HTTPException(status_code=400, detail=f"Failed to reserve seat for session on {session.get('date')}")
                
                # Create booking
                booking = Booking(
                    user_id=current_user["id"],
                    session_id=session["id"],
                    listing_id=data.listing_id,
                    child_profile_name=data.child_profile_name,
                    child_profile_age=data.child_profile_age,
                    qty=1,
                    unit_price_inr=total_price / sessions_to_book if not is_trial else unit_price,
                    taxes_inr=taxes / sessions_to_book,
                    total_inr=grand_total / sessions_to_book if sessions_to_book > 1 else grand_total,
                    credits_used=credits_used // sessions_to_book if credits_used > 0 else 0,
                    payment_method=data.payment_method,
                    payment_txn_id=payment_txn_id,
                    booking_status=BookingStatus.confirmed,
                    is_trial=is_trial
                )
                
                await self.booking_repo.add_booking(booking_doc=booking)
                booking_ids.append(booking.id)
                
                # AUTO-GENERATE INVOICE for each booking
                try:
                    logging.info(f"Starting invoice generation for plan booking {booking.id}")
                    
                    # Generate invoice number
                    today = datetime.now(timezone.utc)
                    date_str = today.strftime("%Y%m%d")
                    count = await self.invoice_repo.generate_invoice_number(date=date_str)
                    invoice_number = f"INV-{date_str}-{str(count + 1).zfill(4)}"
                    
                    # Get partner name
                    filter={ "name": 1, "business_name": 1}
                    partner = await self.auth_repo.find_user_by_id(id=listing.get("partner_id"), filter=filter)
                    
                    partner_name = partner.get("business_name", partner.get("name", "")) if partner else ""
                    
                    # Get session date
                    session_date = session.get("start_at") if "start_at" in session else datetime.now(timezone.utc)
                    
                    # Create invoice
                    invoice = {
                        "id": str(uuid.uuid4()),
                        "invoice_number": invoice_number,
                        "booking_id": booking.id,
                        "customer_id": current_user["id"],
                        "customer_name": current_user.get("name", ""),
                        "customer_email": current_user.get("email", ""),
                        "partner_id": listing.get("partner_id", ""),
                        "partner_name": partner_name,
                        "listing_title": listing["title"],
                        "items": [{
                            "description": f"{listing['title']} ({data.plan_id} plan)",
                            "quantity": 1,
                            "unit_price": booking.unit_price_inr,
                            "total": booking.unit_price_inr
                        }],
                        "subtotal": booking.unit_price_inr,
                        "discount": 0,
                        "credits_used": booking.credits_used,
                        "credits_value": booking.credits_used,
                        "total_inr": booking.total_inr,
                        "payment_method": data.payment_method,
                        "payment_status": "completed",
                        "invoice_date": today,
                        "paid_date": today,
                        "status": "paid",
                        "gst_amount": booking.taxes_inr,
                        "session_date": session_date,
                        "session_duration": listing.get("session_duration", 60)
                    }
                    
                    await self.invoice_repo.add_invoice(data=invoice)
                    logging.info(f"✅ Auto-generated invoice {invoice_number} for plan booking {booking.id}")
                except Exception as e:
                    logging.error(f"❌ Failed to auto-generate invoice for plan booking {booking.id}: {e}")
                    logging.exception("Full traceback:")
                    # Don't fail the booking if invoice generation fails
            
            return {
                "message": f"Successfully booked {sessions_to_book} sessions!",
                "bookings": booking_ids,
                "plan": data.plan_id,
                "sessions_count": sessions_to_book,
                "total_paid": grand_total,
                "discount_percent": plan["discount"],
                "savings": (base_price * sessions_to_book) - total_price if not is_trial else 0
            }
        except HTTPException:
            raise  # Re-raise HTTP exceptions
        except Exception as e:
            logging.error(f"Error in add_children: {e}")
            return []
    
    async def get_my_bookings(self, current_user):
        """Get user's bookings
        
        CRITICAL: Always returns {"bookings": [...]} even on error.
        """
        try:
            # Allow customers and partners to view their own bookings
            # Partners can book classes for themselves/their kids too
            if current_user["role"] not in ["customer", "partner_owner", "partner_staff"]:
                raise HTTPException(status_code=403, detail="Access denied")
            
            bookings = await self.booking_repo.find_bookings(id=current_user["id"])
            
            # Enrich with listing and session
            for booking in bookings:
                listing = await self.listing_repo.get_listing_by_id(listing_id=booking["listing_id"])
                if listing:
                    booking["listing_title"] = listing["title"]
                    booking["listing_media"] = listing.get("media", [])
                
                session = await self.session_repo.get_session_by_id(session_id=booking["session_id"])
                if session:
                    # Handle both old (start_at) and new (date/time) session structures
                    if "start_at" in session:
                        booking["session_start"] = session["start_at"]
                        booking["session_end"] = session.get("end_at")
                        # Add frontend-friendly fields
                        booking["session_date"] = session["start_at"]
                        booking["session_time"] = session["start_at"].strftime("%I:%M %p") if isinstance(session["start_at"], datetime) else "TBD"
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
                            # Calculate end time based on duration (assume 90 minutes if not specified)
                            duration_minutes = session.get("duration_minutes", 90)
                            booking["session_end"] = session_datetime + timedelta(minutes=duration_minutes)
                            
                            # Add frontend-friendly fields
                            booking["session_date"] = session_datetime.isoformat()
                            booking["session_time"] = session_datetime.strftime("%I:%M %p")
                        except Exception as e:
                            logging.warning(f"Error parsing session date/time for booking {booking['id']}: {e}")
                            booking["session_start"] = None
                            booking["session_end"] = None
                            booking["session_date"] = datetime.now(timezone.utc).isoformat()
                            booking["session_time"] = "TBD"
                else:
                    # No session found - provide defaults
                    booking["session_date"] = booking.get("booked_at", datetime.now(timezone.utc).isoformat())
                    booking["session_time"] = "TBD"
            
            return {"bookings": bookings}
        except HTTPException:
            raise  # Re-raise HTTP exceptions
        except Exception as e:
            logging.error(f"Error in get_my_bookings: {e}")
            return {"bookings": []}
    
    async def cancel_booking(self, booking_id, reason, current_user):
        booking = await self.booking_repo.find_booking(bookind_id=booking_id)
        if not booking:
            raise HTTPException(status_code=404, detail="Booking not found")
        
        if booking["user_id"] != current_user["id"]:
            raise HTTPException(status_code=403, detail="Not your booking")
        
        if booking["booking_status"] in ["canceled", "refunded"]:
            raise HTTPException(status_code=400, detail="Already canceled")
        
        # Check if this is a trial booking - no cancellation allowed
        if booking.get("is_trial", False):
            raise HTTPException(status_code=400, detail="Trial bookings cannot be canceled")
        
        # Get session to check timing
        session = await self.session_repo.get_session_by_id(session_id=booking["session_id"])
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Handle both old (start_at) and new (date/time) session structures
        now = datetime.now(timezone.utc)
        
        if "start_at" in session:
            session_start = session["start_at"]
            if session_start.tzinfo is None:
                session_start = session_start.replace(tzinfo=timezone.utc)
        elif "date" in session and "time" in session:
            # Convert date/time to datetime
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
                
                session_start = session_date.replace(
                    hour=hour,
                    minute=minute,
                    second=0,
                    microsecond=0,
                    tzinfo=timezone.utc
                )
            except Exception as e:
                logging.error(f"Error parsing session date/time: {e}")
                raise HTTPException(status_code=500, detail="Invalid session date/time format")
        else:
            raise HTTPException(status_code=500, detail="Session missing date/time information")
        
        # Calculate hours before session starts
        hours_before = (session_start - now).total_seconds() / 3600
        
        # Cancellation policy:
        # - More than 6 hours before: 100% refund
        # - Between 2-6 hours before: 50% refund
        # - Less than 2 hours before: No refund (0%)
        refund_pct = 0
        if hours_before >= 6:
            refund_pct = 100
        elif hours_before >= 2:
            refund_pct = 50
        else:
            # No cancellation within 2 hours
            raise HTTPException(
                status_code=400, 
                detail=f"Cancellation not allowed within 2 hours of class start time. Session starts in {hours_before:.1f} hours."
            )
        
        refund_amount = booking["total_inr"] * (refund_pct / 100)
        refund_credits = int(booking["credits_used"] * (refund_pct / 100))
        
        # Release seat
        await self.session_repo.update_session(session_id=booking["session_id"])
        
        # Refund credits
        if refund_credits > 0:
            await self.wallet_repo.update_wallet(id=current_user["id"], credits_balance = refund_credits)

            ledger_entry = CreditLedger(
                user_id=current_user["id"],
                delta=refund_credits,
                reason="refund",
                ref_booking_id=booking_id
            )
            await self.wallet_repo.create_credit_ledger(creadit_leadger=ledger_entry)

        
        # Update booking
        update_data = {
                    "booking_status": "canceled",
                    "canceled_at": datetime.now(timezone.utc),
                    "canceled_by": "customer",
                    "cancellation_reason": reason,
                    "refund_amount_inr": refund_amount,
                    "refund_credits": refund_credits,
                    "refund_percentage": refund_pct,
                    "payout_eligible": False
                }
        await self.booking_repo.update_booking(booking_id=booking_id, update_data=update_data)
        
        return {
            "message": f"Booking canceled successfully with {refund_pct}% refund",
            "refund_amount_inr": refund_amount,
            "refund_credits": refund_credits,
            "refund_percentage": refund_pct,
            "hours_before_session": round(hours_before, 1)
        }

    async def reschedule_booking(self, booking_id, request, current_user):
        try:
            """Reschedule a booking to a different session (ALL plan types allowed - only once per booking)"""
            new_session_id = request.new_session_id
            # Get original booking
            booking = await self.booking_repo.find_booking(bookind_id=booking_id)
            if not booking:
                raise HTTPException(status_code=404, detail="Booking not found")
            
            if booking["user_id"] != current_user["id"]:
                raise HTTPException(status_code=403, detail="Not your booking")
            
            if booking["booking_status"] in ["canceled", "refunded", "attended"]:
                raise HTTPException(status_code=400, detail=f"Cannot reschedule {booking['booking_status']} booking")
            
            # Check if reschedule is allowed - now allowed for ALL plan types (Trial, Single, Weekly, Monthly)
            # Get listing and plan details to check time limit
            listing = await self.listing_repo.get_listing_by_id(listing_id=booking_id["listing_id"])
            if not listing:
                raise HTTPException(status_code=404, detail="Listing not found")
            
            # Find the plan this booking was made with to get reschedule_limit_minutes
            plan_option_id = booking.get("plan_option_id")
            reschedule_limit = 30  # Default 30 minutes
            
            if plan_option_id and listing.get("plan_options"):
                plan = next((p for p in listing["plan_options"] if p.get("id") == plan_option_id), None)
                if plan:
                    reschedule_limit = plan.get("reschedule_limit_minutes", 30)
            
            # Check time limit - must be at least reschedule_limit minutes before class
            old_session = await self.session_repo.get_session_by_id(session_id=booking["session_id"])
            if old_session:
                session_start = old_session.get("start_at")
                if session_start:
                    # Ensure session_start is timezone-aware
                    if session_start.tzinfo is None:
                        session_start = session_start.replace(tzinfo=timezone.utc)
                    
                    time_until_session = (session_start - datetime.now(timezone.utc)).total_seconds() / 60
                    if time_until_session < reschedule_limit:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Cannot reschedule within {reschedule_limit} minutes of class start time"
                        )
            
            # Check if booking has already been rescheduled
            reschedule_count = booking.get("reschedule_count", 0)
            if reschedule_count >= 1:
                raise HTTPException(status_code=400, detail="This booking has already been rescheduled once. Only one reschedule is allowed per booking.")
            
            # Get original session
            old_session = await self.session_repo.get_session_by_id(session_id=booking["session_id"])
            if not old_session:
                raise HTTPException(status_code=404, detail="Original session not found")
            
            # Get new session
            new_session = await self.session_repo.get_session_by_id(session_id=new_session_id)
            if not new_session:
                raise HTTPException(status_code=404, detail="New session not found")
            
            # Verify same listing
            if old_session["listing_id"] != new_session["listing_id"]:
                raise HTTPException(status_code=400, detail="Can only reschedule to sessions from the same class")
            
            # Check if new session is in the future
            now = datetime.now(timezone.utc)
            if "start_at" in new_session:
                session_start = new_session["start_at"]
                if session_start.tzinfo is None:
                    session_start = session_start.replace(tzinfo=timezone.utc)
            elif "date" in new_session and "time" in new_session:
                session_date = datetime.fromisoformat(new_session["date"])
                # Ensure session_date is timezone-aware
                if session_date.tzinfo is None:
                    session_date = session_date.replace(tzinfo=timezone.utc)
                time_parts = new_session["time"].split(':')
                hour = int(time_parts[0])
                minute = int(time_parts[1]) if len(time_parts) > 1 else 0
                session_start = session_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
            else:
                raise HTTPException(status_code=500, detail="New session missing date/time")
            
            if session_start <= now:
                raise HTTPException(status_code=400, detail="Cannot reschedule to a past session")
            
            # Check new session availability
            if new_session.get("status") != "scheduled":
                raise HTTPException(status_code=400, detail="New session is not available")
            
            seats_booked = new_session.get("seats_booked", 0)
            seats_total = new_session.get("seats_total", 10)
            
            if seats_booked >= seats_total:
                raise HTTPException(status_code=400, detail="New session is fully booked")
            
            # Free up old session seat
            await self.session_repo.update_remove_session(session_id=booking["session_id"])
            
            # Book new session seat
            await self.session_repo.update_session(session_id=new_session_id)

            
            # Update booking with reschedule count
            update_data={
                        "session_id": new_session_id,
                        "rescheduled_at": datetime.now(timezone.utc),
                        "rescheduled_from": booking["session_id"]
                    }
            inc_data = {
                "reschedule_count": 1
            }
            await self.booking_repo.update_booking_after_rescheduling(booking_id=booking_id, update_data=update_data, inc_data= inc_data )
            
            # Create audit log
            # await db.audit_logs.insert_one({
            #     "id": str(uuid.uuid4()),
            #     "action": "booking_rescheduled",
            #     "actor_id": current_user["id"],
            #     "actor_role": current_user["role"],
            #     "target_id": booking_id,
            #     "target_type": "booking",
            #     "details": {
            #         "old_session_id": booking["session_id"],
            #         "new_session_id": new_session_id,
            #         "listing_id": old_session["listing_id"]
            #     },
            #     "timestamp": datetime.now(timezone.utc)
            # })
            
            return {
                "message": "Booking rescheduled successfully",
                "booking_id": booking_id,
                "new_session_id": new_session_id,
                "new_session_time": session_start.isoformat()
            }
        
        except HTTPException:
            raise  # Re-raise HTTP exceptions
        except Exception as e:
            logging.error(f"Error in get_my_bookings: {e}")
            return {"bookings": []}

    async def mark_unable_to_attend(
            self,
        booking_id,
        reason,
        custom_note,
        session_id,
        current_user
    ):
        """
        Mark user as unable to attend a session (for weekly/monthly plans)
        This notifies the partner but doesn't cancel the booking
        """
        try:
            # Validate reason
            valid_reasons = ["feeling_unwell", "traveling", "scheduling_conflict", "other"]
            if reason not in valid_reasons:
                raise HTTPException(status_code=400, detail=f"Invalid reason. Must be one of: {valid_reasons}")
            
            # Get booking
            booking = await self.booking_repo.find_booking(bookind_id=booking_id)
            if not booking:
                raise HTTPException(status_code=404, detail="Booking not found")
            
            if booking["user_id"] != current_user["id"]:
                raise HTTPException(status_code=403, detail="Not your booking")
            
            # Get listing to find partner
            listing = await self.listing_repo.get_listing_by_id(listing_id=booking["listing_id"])
            if not listing:
                raise HTTPException(status_code=404, detail="Listing not found")
            
            # Get session details
            session = await self.session_repo.get_session_by_id(session_id=session_id or booking["session_id"])
            if not session:
                raise HTTPException(status_code=404, detail="Session not found")
            
            # Get session datetime
            if "start_at" in session:
                session_datetime = session["start_at"]
            elif "date" in session and "time" in session:
                session_date = datetime.fromisoformat(session["date"])
                time_parts = session["time"].split(':')
                hour = int(time_parts[0])
                minute = int(time_parts[1]) if len(time_parts) > 1 else 0
                session_datetime = session_date.replace(hour=hour, minute=minute, tzinfo=timezone.utc)
            else:
                session_datetime = datetime.now(timezone.utc)
            
            # Create unable to attend record
            unable_to_attend = {
                "id": str(uuid.uuid4()),
                "booking_id": booking_id,
                "session_id": session_id or booking["session_id"],
                "user_id": current_user["id"],
                "listing_id": booking["listing_id"],
                "partner_id": listing["partner_id"],
                "session_date_time": session_datetime,
                "reason": reason,
                "custom_note": custom_note,
                "notification_sent": False,
                "created_at": datetime.now(timezone.utc)
            }
            
            await self.booking_repo.unable_to_attend(unable_to_attend_data=unable_to_attend)
            
            # Create notification for partner
            notification = {
                "id": str(uuid.uuid4()),
                "user_id": listing["partner_id"],
                "type": "unable_to_attend",
                "title": "Student Unable to Attend",
                "message": f"{current_user.get('name', 'A student')} won't be attending the session on {session_datetime.strftime('%b %d, %Y at %I:%M %p')}",
                "data": {
                    "booking_id": booking_id,
                    "student_name": current_user.get("name", "Student"),
                    "session_datetime": session_datetime.isoformat(),
                    "reason": reason,
                    "custom_note": custom_note,
                    "child_name": booking.get("child_profile_name", "")
                },
                "is_read": False,
                "created_at": datetime.now(timezone.utc)
            }
            
            await self.session_repo.add_notification(notification_data=notification)
            
            # Mark notification as sent
            await self.booking_repo.update_unable_to_attend(id=unable_to_attend["id"], update_data={"notification_sent": True})
            
            return {
                "message": "Partner has been notified",
                "unable_to_attend_id": unable_to_attend["id"]
            }
        
        except HTTPException:
            raise
        except Exception as e:
            logging.error(f"Error marking unable to attend: {e}")
            raise HTTPException(status_code=500, detail="Failed to process request")


    async def get_unable_to_attend_history(
        self, booking_id: str,
        current_user: Dict
    ):
        """Get unable to attend history for a booking"""
        try:
            # Verify booking belongs to user
            booking = await self.booking_repo.find_booking(bookind_id=booking_id)
            if not booking:
                raise HTTPException(status_code=404, detail="Booking not found")
            
            if booking["user_id"] != current_user["id"]:
                raise HTTPException(status_code=403, detail="Not your booking")
            
            # Get history
            history = await self.booking_repo.find_unable_to_attend_by_id(unable_to_attend_id=booking_id)
            
            return {"history": history, "count": len(history)}
        
        except HTTPException:
            raise
        except Exception as e:
            logging.error(f"Error fetching unable to attend history: {e}")
            return {"history": [], "count": 0}



    async def get_available_sessions_for_reschedule(
        self,
        booking_id: str,
        current_user: Dict 
    ):
        """Get available sessions for rescheduling"""
        # Get booking
        booking = await self.booking_repo.find_booking(bookind_id=booking_id)
        if not booking:
            raise HTTPException(status_code=404, detail="Booking not found")
        
        if booking["user_id"] != current_user["id"]:
            raise HTTPException(status_code=403, detail="Not your booking")
        
        # Get current session to find listing
        session = await self.session_repo.get_session_by_id(session_id=booking["session_id"])
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        listing_id = session["listing_id"]
        
        # Get all future sessions from same listing
        now = datetime.now(timezone.utc)
        
        # Query for scheduled sessions with available seats
        future_sessions = await self.session_repo.scheduled_session_with_available_seats(id=listing_id)
        
        # Filter to only future sessions and exclude current session
        available_sessions = []
        for s in future_sessions:
            if s["id"] == booking["session_id"]:
                continue  # Skip current session
            
            # Parse session time
            if "start_at" in s:
                session_start = s["start_at"]
                if session_start.tzinfo is None:
                    session_start = session_start.replace(tzinfo=timezone.utc)
            elif "date" in s and "time" in s:
                session_date = datetime.fromisoformat(s["date"])
                time_parts = s["time"].split(':')
                hour = int(time_parts[0])
                minute = int(time_parts[1]) if len(time_parts) > 1 else 0
                session_start = session_date.replace(hour=hour, minute=minute, second=0, microsecond=0, tzinfo=timezone.utc)
            else:
                continue
            
            if session_start > now:
                available_sessions.append({
                    **s,
                    "available_seats": s.get("seats_total", 10) - s.get("seats_booked", 0),
                    "session_datetime": session_start.isoformat()
                })
        
        return {
            "sessions": available_sessions,
            "listing_id": listing_id,
            "current_session_id": booking["session_id"]
        }