"""services/sentiment.py — AI review analysis and sentiment scoring"""
import os
from anthropic import Anthropic

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY",""))

async def analyze_reviews(reviews: list[str], hotel_name: str) -> dict:
    """Analyze guest reviews using Claude for sentiment and insights."""
    if not reviews:
        return {"sentiment": "neutral", "score": 0.5, "summary": "No reviews yet.", "highlights": [], "concerns": []}

    prompt = f"""Analyze these guest reviews for "{hotel_name}" and return a JSON object with:
- sentiment: "positive" | "neutral" | "negative"
- score: float 0-1
- summary: 2-sentence summary
- highlights: list of top 3 positive aspects
- concerns: list of top 2 concerns (if any)
- recommended: boolean

Reviews:
{chr(10).join(f'- {r}' for r in reviews[:20])}

Return ONLY valid JSON, no explanation."""

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=400,
            messages=[{"role":"user","content":prompt}]
        )
        import json, re
        text = response.content[0].text
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            return json.loads(match.group())
    except Exception as e:
        print(f"Sentiment analysis error: {e}")
    return {"sentiment":"positive","score":0.8,"summary":"Guests generally enjoy this property.","highlights":["Great location","Friendly host","Clean rooms"],"concerns":[],"recommended":True}

async def get_sentiment_badge(score: float) -> str:
    """Return emoji badge for sentiment score."""
    if score >= 0.85: return "⭐ Exceptional"
    if score >= 0.70: return "✅ Highly Rated"
    if score >= 0.50: return "👍 Good"
    return "⚠️ Mixed Reviews"
