"""routes/payment.py — Razorpay order creation and verification"""
from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
import os, hmac, hashlib, json, time
import razorpay
from models import CreateOrderRequest, VerifyPaymentRequest, OrderOut
from services.blockchain import create_blockchain_escrow

router = APIRouter()

RAZORPAY_KEY_ID     = os.getenv("RAZORPAY_KEY_ID","")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET","")

def get_rzp():
    if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
        raise HTTPException(status_code=503, detail="Razorpay not configured. Set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET in .env")
    return razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

_pending_orders: dict = {}
from routes.booking import _bookings

@router.post("/create-order", response_model=OrderOut)
async def create_order(req: CreateOrderRequest):
    try:
        rzp = get_rzp()
        amount_paise = int(req.amount_inr * 100)
        order = rzp.order.create({
            "amount": amount_paise, "currency": "INR",
            "receipt": f"nh_{req.hotel_id}_{int(time.time())}",
            "notes": {"hotel": req.hotel_name, "guest": req.guest_name, "checkin": req.checkin, "checkout": req.checkout}
        })
        _pending_orders[order["id"]] = {"order": order, "booking_data": req.dict()}
        return OrderOut(order_id=order["id"], amount=amount_paise, currency="INR", key_id=RAZORPAY_KEY_ID)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Order creation failed: {str(e)}")

@router.post("/verify")
async def verify_payment(req: VerifyPaymentRequest, background_tasks: BackgroundTasks):
    # Verify Razorpay signature
    expected = hmac.new(
        RAZORPAY_KEY_SECRET.encode(),
        f"{req.razorpay_order_id}|{req.razorpay_payment_id}".encode(),
        hashlib.sha256
    ).hexdigest()
    if expected != req.razorpay_signature:
        raise HTTPException(status_code=400, detail="Payment signature invalid")

    from datetime import datetime
    booking_id = f"SC{int(time.time())}"
    booking = {
        "booking_id": booking_id,
        "razorpay_order_id": req.razorpay_order_id,
        "razorpay_payment_id": req.razorpay_payment_id,
        "payment_status": "paid",
        "blockchain_status": "pending",
        "data": req.booking_data,
        "created_at": datetime.utcnow().isoformat(),
        "status": "confirmed",
    }
    _bookings[booking_id] = booking
    background_tasks.add_task(create_blockchain_escrow, booking_id, req.booking_data)
    return {"success": True, "booking_id": booking_id, "payment_id": req.razorpay_payment_id}

@router.post("/webhook/razorpay")
async def razorpay_webhook(request: Request):
    body = await request.body()
    sig  = request.headers.get("X-Razorpay-Signature","")
    expected = hmac.new(RAZORPAY_KEY_SECRET.encode(), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig):
        raise HTTPException(status_code=400, detail="Invalid webhook signature")
    payload = json.loads(body)
    event   = payload.get("event","")
    print(f"📩 Razorpay webhook: {event}")
    return {"status": "ok"}
