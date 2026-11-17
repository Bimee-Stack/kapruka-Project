"""
THE ROUTER
----------
Reads the customer's message and decides what kind of request it is.
It also pulls out any preference facts it sees ("she is allergic to nuts").
Intents: search | delivery | preference_update | other
"""

from llm import ask_json

SYSTEM = """You are the router for Kapruka's gift concierge (a Sri Lankan e-commerce site).
Classify the customer's latest message. Return JSON with these keys:
 "intent": "search" (wants gift ideas/products), "delivery" (asks if/when delivery is possible),
           "preference_update" (just telling us a like/dislike/allergy), or "other"
 "recipient": who the gift is for, lowercase (e.g. "wife", "mother"), or null
 "likes": list of strings (tastes of the RECIPIENT, never the item being requested now), "dislikes": list of strings, "allergies": list of strings
 "city": delivery city/district mentioned, or null
 "days_until_needed": whole number of days until the gift is needed, or null
 "repeat_last_order": true if they say things like "same as last year/time", else false"""


def route_with_rules(message):
    """Backup if the LLM fails: crude keyword rules, so the app never crashes."""
    m = message.lower()
    out = {"intent": "search", "recipient": None, "likes": [], "dislikes": [],
           "allergies": [], "city": None, "days_until_needed": None,
           "repeat_last_order": "last year" in m or "same as" in m,
           "fallback": True}
    if any(w in m for w in ["allergic", "allergy", "loves", "hates", "prefers"]):
        out["intent"] = "preference_update"
    elif any(w in m for w in ["deliver", "shipping", "reach"]) and not any(
            w in m for w in ["cake", "gift", "flower", "chocolate", "buy", "need", "basket", "hamper"]):
        out["intent"] = "delivery"
    return out


def route(message, history_text="", current_recipient=None):
    user = (f"Recent chat:\n{history_text}\n\n"
            f"Current recipient being discussed: {current_recipient}\n\n"
            f"Latest message: {message}")
    try:
        result = ask_json(SYSTEM, user)
        result.setdefault("intent", "search")
        for key in ("likes", "dislikes", "allergies"):
            result[key] = result.get(key) or []
        return result
    except Exception as e:
        print(f"  [router] LLM failed ({e}); using keyword rules")
        return route_with_rules(message)
