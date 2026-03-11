"""services/ai_agent.py — LangChain booking agent (backend version)"""
import os
from langchain_anthropic import ChatAnthropic
from langchain.memory import ConversationBufferWindowMemory
from langchain.chains import ConversationChain
from langchain.prompts import PromptTemplate

ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY","")

BOOKING_SYSTEM_PROMPT = """You are StayAI, NextHome's intelligent booking agent.
NextHome is a blockchain-powered accommodation platform using Polygon smart contract escrow.

Collect these details conversationally (1-2 at a time):
1. Destination & property preference
2. Check-in date (YYYY-MM-DD)
3. Check-out date (YYYY-MM-DD)
4. Number of guests
5. Room type (Standard/Deluxe/Suite)
6. Guest full name
7. Mobile number
8. Email address
9. ID proof type (Aadhaar/Passport/Driving Licence)
10. Special requests (accept "none")

When ALL collected, end with:
BOOKING_READY:{{"destination":"...","checkin":"YYYY-MM-DD","checkout":"YYYY-MM-DD","nights":N,"guests":N,"roomType":"...","guestName":"...","phone":"...","email":"...","idProof":"...","specialRequests":"..."}}

Current conversation:
{{history}}
Human: {{input}}
AI:"""

def make_agent():
    llm = ChatAnthropic(
        model="claude-sonnet-4-20250514",
        api_key=ANTHROPIC_KEY,
        max_tokens=500,
    )
    memory = ConversationBufferWindowMemory(k=10, human_prefix="Human", ai_prefix="AI")
    prompt = PromptTemplate(input_variables=["history","input"], template=BOOKING_SYSTEM_PROMPT)
    return ConversationChain(llm=llm, memory=memory, prompt=prompt, verbose=False)

# Session store (replace with Redis in production)
_sessions: dict = {}

def get_or_create_session(session_id: str):
    if session_id not in _sessions:
        _sessions[session_id] = {"agent": make_agent(), "booking_data": None}
    return _sessions[session_id]

async def chat(session_id: str, message: str) -> dict:
    """Process a chat message and return AI reply + extracted booking data if ready."""
    import re, json
    session = get_or_create_session(session_id)
    agent   = session["agent"]
    try:
        reply = agent.predict(input=message)
    except Exception as e:
        return {"reply": f"Sorry, I encountered an error: {str(e)}", "booking_ready": False}

    booking_data = None
    match = re.search(r'BOOKING_READY:(\{[\s\S]*?\})', reply)
    if match:
        try:
            booking_data = json.loads(match.group(1))
            session["booking_data"] = booking_data
        except Exception: pass
        reply = reply[:match.start()].strip() or "All details collected! Tap below to proceed to payment."

    return {"reply": reply, "booking_ready": booking_data is not None, "booking_data": booking_data}

def clear_session(session_id: str):
    _sessions.pop(session_id, None)
