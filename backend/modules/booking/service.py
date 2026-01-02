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