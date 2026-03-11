"""
NextHome Backend — FastAPI entry point
Registers all route modules and middleware
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

load_dotenv()

from routes import auth, rooms, booking, payment, escrow

app = FastAPI(title="NextHome API", version="1.0.0", docs_url="/docs", redoc_url="/redoc")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_URL","http://localhost:5173"), "http://localhost:3000", "http://127.0.0.1:5500"],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

app.include_router(auth.router,    prefix="/api/auth",    tags=["auth"])
app.include_router(rooms.router,   prefix="/api/rooms",   tags=["rooms"])
app.include_router(booking.router, prefix="/api/booking", tags=["booking"])
app.include_router(payment.router, prefix="/api/payment", tags=["payment"])
app.include_router(escrow.router,  prefix="/api/escrow",  tags=["escrow"])

@app.get("/")
def root():
    return {"service": "NextHome API", "status": "live", "docs": "/docs"}

@app.get("/health")
def health():
    from datetime import datetime
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}
