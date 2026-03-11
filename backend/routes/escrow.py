"""routes/escrow.py — blockchain status endpoints"""
from fastapi import APIRouter, HTTPException
from services.blockchain import get_onchain_booking, release_funds
from models import BlockchainBookingOut

router = APIRouter()

@router.get("/booking/{onchain_id}")
async def onchain_status(onchain_id: int):
    try:
        return await get_onchain_booking(onchain_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/release/{onchain_id}")
async def trigger_release(onchain_id: int):
    try:
        result = await release_funds(onchain_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
