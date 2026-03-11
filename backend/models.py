"""models.py — Pydantic data models / schemas"""
from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from datetime import datetime
from enum import Enum

class BookingStatus(str, Enum):
    PENDING   = "pending"
    CONFIRMED = "confirmed"
    CHECKED_IN = "checked_in"
    CANCELLED = "cancelled"
    COMPLETED = "completed"

# ── Auth ──────────────────────────────────────────────────────────────────
class SignupRequest(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    password: str
    @field_validator('password')
    def pw_length(cls, v):
        if len(v) < 8: raise ValueError('Password must be at least 8 characters')
        return v

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: str
    first_name: str
    last_name: str
    email: str
    created_at: Optional[str] = None

class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut

# ── Rooms ─────────────────────────────────────────────────────────────────
class RoomOut(BaseModel):
    id: int
    name: str
    city: str
    price: int
    rating: float
    reviews: int
    type: str
    superhost: bool
    rooms: int
    available: int
    cover: str
    imgs: list[str] = []
    amenities: list[str] = []
    desc: str
    cancel: str
    host: Optional[dict] = None

# ── Booking ───────────────────────────────────────────────────────────────
class CreateBookingRequest(BaseModel):
    hotel_id: int
    checkin: str
    checkout: str
    guests: int
    room_type: str
    guest_name: str
    phone: str
    email: EmailStr
    id_proof: str
    special_requests: Optional[str] = ""

class BookingOut(BaseModel):
    booking_id: str
    hotel_id: int
    hotel_name: str
    checkin: str
    checkout: str
    nights: int
    guests: int
    room_type: str
    guest_name: str
    status: BookingStatus
    payment_status: str
    blockchain_status: str
    total: Optional[int] = None
    tx_hash: Optional[str] = None
    ipfs_cid: Optional[str] = None
    block_number: Optional[int] = None
    onchain_booking_id: Optional[int] = None
    polygonscan_url: Optional[str] = None
    created_at: Optional[str] = None

class CancelRequest(BaseModel):
    booking_id: str
    onchain_booking_id: Optional[int] = None

# ── Payment ───────────────────────────────────────────────────────────────
class CreateOrderRequest(BaseModel):
    hotel_id: int
    hotel_name: str
    amount_inr: float
    checkin: str
    checkout: str
    nights: int
    guests: int
    room_type: str
    guest_name: str
    phone: str
    email: EmailStr
    id_proof: str
    special_requests: Optional[str] = ""

class VerifyPaymentRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    booking_data: dict

class OrderOut(BaseModel):
    order_id: str
    amount: int
    currency: str
    key_id: str

# ── Escrow ────────────────────────────────────────────────────────────────
class BlockchainBookingRequest(BaseModel):
    booking_id: str
    guest_wallet: str
    host_wallet: str
    amount_matic: float
    checkin_timestamp: int
    checkout_timestamp: int
    ipfs_cid: str

class BlockchainBookingOut(BaseModel):
    tx_hash: str
    block_number: int
    onchain_booking_id: Optional[int] = None
    polygonscan_url: str

# ── Resale ────────────────────────────────────────────────────────────────
class ResaleListRequest(BaseModel):
    booking_id: str
    resale_price: int

class ResaleBuyRequest(BaseModel):
    listing_id: str
    buyer_wallet: Optional[str] = None
