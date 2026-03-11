"""routes/rooms.py — room search and detail endpoints"""
from fastapi import APIRouter, Query
from typing import Optional
from database import get_supabase, get_cached_rooms, cache_rooms

router = APIRouter()

# Fallback mock data when Supabase is not configured
MOCK_ROOMS = [
    {"id":1,"name":"The Leela Palace","city":"Udaipur, Rajasthan","price":12500,"rating":4.97,"reviews":284,"type":"Heritage Palace","superhost":True,"rooms":5,"available":3,"cover":"https://images.unsplash.com/photo-1566073771259-6a8506099945?w=600","imgs":["https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=600"],"amenities":["Lake view","Infinity pool","Ayurvedic spa","Butler service","Heritage walks"],"desc":"A restored 18th-century palace on Lake Pichola.","cancel":"Full refund if cancelled 48h before check-in.","host":{"name":"Arjun Mewar","photo":"https://i.pravatar.cc/56?img=11","since":"2018"}},
    {"id":2,"name":"Taj Mahal Tower","city":"Mumbai, Maharashtra","price":18000,"rating":4.95,"reviews":512,"type":"City Landmark","superhost":True,"rooms":4,"available":2,"cover":"https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?w=600","imgs":["https://images.unsplash.com/photo-1590490360182-c33d57733427?w=600"],"amenities":["Harbour view","Rooftop bar","Spa","Concierge","Fine dining"],"desc":"Iconic harbour-view suites overlooking the Gateway of India.","cancel":"Full refund if cancelled 72h before check-in.","host":{"name":"Priya Kapoor","photo":"https://i.pravatar.cc/56?img=47","since":"2017"}},
    {"id":3,"name":"Coorg Forest Cottage","city":"Madikeri, Karnataka","price":6800,"rating":4.92,"reviews":198,"type":"Forest Retreat","superhost":False,"rooms":6,"available":5,"cover":"https://images.unsplash.com/photo-1441974231531-c6227db76b6e?w=600","imgs":["https://images.unsplash.com/photo-1601918774946-25832a4be0d6?w=600"],"amenities":["Coffee walks","Bonfire","Organic meals","Waterfall trek"],"desc":"Stone-and-timber cottages inside a coffee estate.","cancel":"Full refund if cancelled 24h before check-in.","host":{"name":"Anand Thimmaiah","photo":"https://i.pravatar.cc/56?img=33","since":"2019"}},
    {"id":4,"name":"Rann Luxury Tents","city":"Dhordo, Gujarat","price":14000,"rating":4.89,"reviews":143,"type":"Glamping","superhost":True,"rooms":4,"available":1,"cover":"https://images.unsplash.com/photo-1504280390367-361c6d9f38f4?w=600","imgs":["https://images.unsplash.com/photo-1537640538966-79f369143f8f?w=600"],"amenities":["Salt flat safari","Stargazing deck","Camel rides","Folk nights"],"desc":"Climate-controlled canvas pavilions over the White Rann.","cancel":"Full refund if cancelled 72h before check-in.","host":{"name":"Harshida Parmar","photo":"https://i.pravatar.cc/56?img=25","since":"2020"}},
    {"id":5,"name":"Wayanad Treehouse","city":"Vythiri, Kerala","price":8200,"rating":4.94,"reviews":367,"type":"Treehouse","superhost":True,"rooms":5,"available":4,"cover":"https://images.unsplash.com/photo-1448375240586-882707db888b?w=600","imgs":["https://images.unsplash.com/photo-1588880331179-bc9b93a8cb5e?w=600"],"amenities":["Dawn nature walks","Rope bridges","Organic meals","Night safari"],"desc":"Eight treehouses built 30 feet above the forest floor.","cancel":"Full refund if cancelled 24h before check-in.","host":{"name":"Suresh Nair","photo":"https://i.pravatar.cc/56?img=15","since":"2016"}},
    {"id":7,"name":"Ashvem Beach Villa","city":"Ashvem, North Goa","price":11500,"rating":4.91,"reviews":419,"type":"Beachfront Villa","superhost":True,"rooms":5,"available":3,"cover":"https://images.unsplash.com/photo-1499793983690-e29da59ef1c2?w=600","imgs":["https://images.unsplash.com/photo-1540518614846-7eded433c457?w=600"],"amenities":["Private plunge pool","Beach butler","Seafood BBQ","Kayaking"],"desc":"Private villas where the Arabian Sea is your backyard.","cancel":"Full refund if cancelled 48h before check-in.","host":{"name":"Maria Fernandes","photo":"https://i.pravatar.cc/56?img=44","since":"2019"}},
]

@router.get("")
async def list_rooms(
    city:     Optional[str]   = Query(None),
    type:     Optional[str]   = Query(None),
    checkin:  Optional[str]   = Query(None),
    checkout: Optional[str]   = Query(None),
    guests:   Optional[int]   = Query(None),
    limit:    int             = Query(20),
    offset:   int             = Query(0),
):
    # Try Redis cache
    cached = await get_cached_rooms()
    rooms = cached if cached else await _fetch_from_db()

    # Filter
    if city:
        city_lower = city.lower()
        rooms = [r for r in rooms if city_lower in r["city"].lower() or city_lower in r["name"].lower()]
    if type:
        rooms = [r for r in rooms if r["type"] == type]
    if guests:
        rooms = [r for r in rooms if r["available"] >= 1]

    return rooms[offset:offset+limit]

@router.get("/{room_id}")
async def get_room(room_id: int):
    rooms = await _fetch_from_db()
    room = next((r for r in rooms if r["id"] == room_id), None)
    if not room:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Room not found")
    return room

async def _fetch_from_db():
    try:
        sb = get_supabase()
        result = sb.table("rooms").select("*").execute()
        rooms = result.data or []
        if rooms:
            await cache_rooms(rooms)
            return rooms
    except Exception:
        pass
    return MOCK_ROOMS
