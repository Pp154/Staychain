"""services/optimizer.py — AI listing description and title optimizer"""
import os
from anthropic import Anthropic

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY",""))

async def optimize_listing(name: str, raw_desc: str, amenities: list, city: str, property_type: str) -> dict:
    """Generate SEO-optimized, engaging listing description using Claude."""
    prompt = f"""You are an expert hospitality copywriter. Improve this accommodation listing.

Property: {name}
Type: {property_type}
Location: {city}
Amenities: {', '.join(amenities)}
Raw description: {raw_desc}

Return JSON with:
- title: compelling 8-12 word title
- headline: one-line hook (max 15 words)
- description: 3-sentence engaging description (under 80 words)
- tags: list of 5 searchable tags
- highlights: list of 3 key selling points

Return ONLY valid JSON."""

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=500,
            messages=[{"role":"user","content":prompt}]
        )
        import json, re
        text  = response.content[0].text
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            return json.loads(match.group())
    except Exception as e:
        print(f"Optimizer error: {e}")
    return {"title": name, "headline": f"Experience {property_type} in {city}", "description": raw_desc, "tags": [property_type, city], "highlights": amenities[:3]}

async def suggest_price(property_type: str, city: str, amenities: list, current_price: int) -> dict:
    """Suggest optimal pricing based on property attributes."""
    prompt = f"""Given a {property_type} in {city} with amenities: {', '.join(amenities)}, current price ₹{current_price}/night.
Suggest optimal pricing. Return JSON: {{"suggested_price": int, "min_price": int, "max_price": int, "reasoning": str}}
Return ONLY valid JSON."""
    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001", max_tokens=200,
            messages=[{"role":"user","content":prompt}]
        )
        import json, re
        match = re.search(r'\{[\s\S]*\}', response.content[0].text)
        if match: return json.loads(match.group())
    except Exception: pass
    return {"suggested_price": current_price, "min_price": int(current_price*0.8), "max_price": int(current_price*1.3), "reasoning": "Based on market average."}
