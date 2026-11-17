"""
LOGISTICS SPECIALIST
--------------------
Checks whether we can deliver to a Sri Lankan district in time.

!! IMPORTANT: the tiers below are an ASSUMPTION to make the project work.
   Before you submit, check Kapruka's real delivery policy and edit DISTRICT_TIERS.
   Say so in your report - it is an honest, good limitation to mention.
"""

DISTRICT_TIERS = {
    # same day (assumed)
    "colombo": 0, "gampaha": 0, "kalutara": 0, "kandy": 0, "galle": 0,
    # next day (assumed)
    "kurunegala": 1, "matale": 1, "nuwara eliya": 1, "matara": 1, "ratnapura": 1,
    "kegalle": 1, "puttalam": 1, "hambantota": 1, "badulla": 1, "anuradhapura": 1,
    # 2-3 days (assumed)
    "jaffna": 3, "kilinochchi": 3, "mannar": 3, "vavuniya": 3, "mullaitivu": 3,
    "batticaloa": 3, "ampara": 3, "trincomalee": 3, "polonnaruwa": 3, "monaragala": 3,
}


def find_district(text):
    """Return a district name if one appears in the text, else None."""
    if not text:
        return None
    t = text.lower()
    for name in DISTRICT_TIERS:
        if name in t:
            return name
    return None


def check_delivery(district, days_until_needed=None):
    """Tool: can we deliver to `district`, and by when?"""
    name = find_district(district)
    if not name:
        return {"district": district, "feasible": None,
                "message": "I couldn't recognise that district. Which Sri Lankan district is it?"}

    days_needed = DISTRICT_TIERS[name]
    label = {0: "same-day", 1: "next-day", 3: "2-3 day"}[days_needed]
    if days_until_needed is not None and days_until_needed < days_needed:
        return {"district": name.title(), "feasible": False,
                "message": f"{name.title()} needs {label} delivery, which is too late "
                           f"for your {days_until_needed}-day deadline."}
    return {"district": name.title(), "feasible": True,
            "message": f"Delivery to {name.title()} is possible ({label})."}
