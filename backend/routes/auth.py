"""routes/auth.py — signup, login, profile"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os, jwt
from datetime import datetime, timedelta
from models import SignupRequest, LoginRequest, AuthResponse, UserOut
from database import get_supabase

router = APIRouter()
security = HTTPBearer()
JWT_SECRET = os.getenv("JWT_SECRET", "nexthome_dev_secret_change_in_prod")
JWT_ALGO   = "HS256"

def make_token(user_id: str, email: str) -> str:
    payload = {"sub": user_id, "email": email, "exp": datetime.utcnow() + timedelta(days=30)}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    try:
        return jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGO])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

@router.post("/signup", response_model=AuthResponse)
async def signup(req: SignupRequest):
    try:
        sb = get_supabase()
        result = sb.auth.sign_up({"email": req.email, "password": req.password,
            "options": {"data": {"first_name": req.first_name, "last_name": req.last_name}}})
        if not result.user:
            raise HTTPException(status_code=400, detail="Signup failed")
        user = result.user
        token = make_token(user.id, user.email)
        return AuthResponse(access_token=token, user=UserOut(
            id=user.id, first_name=req.first_name, last_name=req.last_name,
            email=user.email, created_at=str(user.created_at)))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/login", response_model=AuthResponse)
async def login(req: LoginRequest):
    try:
        sb = get_supabase()
        result = sb.auth.sign_in_with_password({"email": req.email, "password": req.password})
        if not result.user:
            raise HTTPException(status_code=401, detail="Invalid email or password")
        user = result.user
        meta = user.user_metadata or {}
        token = make_token(user.id, user.email)
        return AuthResponse(access_token=token, user=UserOut(
            id=user.id, first_name=meta.get("first_name",""), last_name=meta.get("last_name",""),
            email=user.email))
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid email or password")

@router.get("/me")
async def me(payload: dict = Depends(verify_token)):
    return {"user_id": payload["sub"], "email": payload["email"]}
