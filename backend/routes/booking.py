"""routes/booking.py — create, get, cancel, resale endpoints"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from models import CreateBookingRequest, BookingOut, CancelRequest, ResaleListRequest, ResaleBuyRequest
from database import get_supabase, publish_vacancy_update, invalidate_room_cache
from services.blockchain import cancel_onchain_booking
import time, os

router = APIRouter()

# In-memory fallback store
_bookings: dict = {}
_resale_listings: list = []

@router.post("", response_model=BookingOut)
async def create_booking(req: CreateBookingRequest):
    """Create a booking record (payment handled separately via /payment/create-order)."""
    from datetime import datetime
    nights = max(1, round((datetime(*[int(x) for x in req.checkout.split('-')]) - datetime(*[int(x) for x in req.checkin.split('-')])).days))
    booking_id = f"SC{int(time.time())}"
    booking = {
        "booking_id": booking_id, "hotel_id": req.hotel_id, "hotel_name": "",
        "checkin": req.checkin, "checkout": req.checkout, "nights": nights,
        "guests": req.guests, "room_type": req.room_type, "guest_name": req.guest_name,
        "status": "confirmed", "payment_status": "pending", "blockchain_status": "pending",
        "created_at": datetime.utcnow().isoformat()
    }
    _bookings[booking_id] = booking
    try:
        sb = get_supabase()
        sb.table("bookings").insert({**booking, "phone": req.phone, "email": req.email, "id_proof": req.id_proof, "special_requests": req.special_requests}).execute()
    except Exception: pass
    return BookingOut(**booking)

@router.get("/{booking_id}")
async def get_booking(booking_id: str):
    booking = _bookings.get(booking_id)
    if not booking:
        try:
            sb = get_supabase()
            result = sb.table("bookings").select("*").eq("booking_id", booking_id).single().execute()
            booking = result.data
        except Exception: pass
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking

@router.post("/cancel")
async def cancel_booking(req: CancelRequest, background_tasks: BackgroundTasks):
    booking = _bookings.get(req.booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    booking["status"] = "cancelled"
    booking["payment_status"] = "refunded"
    # Restore vacancy
    background_tasks.add_task(_restore_vacancy, booking["hotel_id"])
    # Trigger on-chain cancellation
    if req.onchain_booking_id:
        background_tasks.add_task(cancel_onchain_booking, req.booking_id, req.onchain_booking_id)
    return {"success": True, "booking_id": req.booking_id, "message": "Cancelled. Escrow refund initiated."}

async def _restore_vacancy(hotel_id: int):
    await publish_vacancy_update(hotel_id, -1)  # -1 means increment
    await invalidate_room_cache(hotel_id)

# ── Resale ────────────────────────────────────────────────────────────────
@router.get("/resale/listings")
async def list_resale():
    return _resale_listings

@router.post("/resale/list")
async def list_for_resale(req: ResaleListRequest):
    booking = _bookings.get(req.booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    listing = {**booking, "listing_id": f"RL{int(time.time())}", "resale_price": req.resale_price, "listed_at": __import__("datetime").datetime.utcnow().isoformat()}
    _resale_listings.append(listing)
    return {"success": True, "listing_id": listing["listing_id"]}

@router.post("/resale/buy")
async def buy_resale(req: ResaleBuyRequest, background_tasks: BackgroundTasks):
    listing = next((l for l in _resale_listings if l["listing_id"] == req.listing_id), None)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    # Atomic transfer: remove from resale, create new booking for buyer
    _resale_listings.remove(listing)
    new_id = f"SC{int(time.time())}"
    new_booking = {**listing, "booking_id": new_id, "status": "confirmed", "payment_status": "paid"}
    _bookings[new_id] = new_booking
    return {"success": True, "new_booking_id": new_id, "message": "Atomic resale transfer complete"}
