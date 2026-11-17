"""
Tier 3: SEMANTIC MEMORY  (Recipient Profiles)
---------------------------------------------
Facts about the people a customer buys gifts for, saved in a JSON file.

File layout (data/profiles.json):
{
  "customer_001": {
    "wife": {
      "likes": ["dark chocolate"],
      "dislikes": [],
      "allergies": ["nuts"],
      "city": "Colombo",
      "past_orders": [{"year": 2025, "product_id": "...", "name": "..."}]
    }
  }
}
"""

import json
from pathlib import Path


class SemanticMemory:
    def __init__(self, path="data/profiles.json"):
        self.path = Path(path)
        self.data = {}
        self._load()

    # ---------- saving / loading ----------
    def _load(self):
        if self.path.exists():
            self.data = json.loads(self.path.read_text(encoding="utf-8"))

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, indent=2, ensure_ascii=False),
                             encoding="utf-8")

    # ---------- reading ----------
    def get_profile(self, user_id, recipient):
        """Return the profile dict, or None if we have never heard of them."""
        return self.data.get(user_id, {}).get(recipient.lower())

    def list_recipients(self, user_id):
        return list(self.data.get(user_id, {}).keys())

    def describe(self, user_id, recipient):
        """Profile as one readable sentence, for the Memory Found message / prompts."""
        p = self.get_profile(user_id, recipient)
        if not p:
            return f"No profile for {recipient} yet."
        parts = [f"{recipient.title()}:"]
        if p["likes"]:
            parts.append("likes " + ", ".join(p["likes"]) + ".")
        if p["dislikes"]:
            parts.append("dislikes " + ", ".join(p["dislikes"]) + ".")
        if p["allergies"]:
            parts.append("ALLERGIC to " + ", ".join(p["allergies"]) + ".")
        if p.get("city"):
            parts.append(f"Lives in {p['city']}.")
        return " ".join(parts)

    # ---------- writing ----------
    def update_profile(self, user_id, recipient, likes=None, dislikes=None,
                       allergies=None, city=None):
        """Create or update a profile. New items are ADDED, old ones are kept."""
        recipient = recipient.lower()
        user = self.data.setdefault(user_id, {})
        profile = user.setdefault(recipient, {
            "likes": [], "dislikes": [], "allergies": [],
            "city": None, "past_orders": [],
        })

        for field, new_items in [("likes", likes), ("dislikes", dislikes),
                                 ("allergies", allergies)]:
            for item in (new_items or []):
                item = item.lower().strip()
                if item and item not in profile[field]:
                    profile[field].append(item)

        if city:
            profile["city"] = city

        self._save()
        return profile

    def add_past_order(self, user_id, recipient, product_id, name, year):
        """Remember what was bought, so 'same as last year' works."""
        self.update_profile(user_id, recipient)          # makes sure profile exists
        self.data[user_id][recipient.lower()]["past_orders"].append(
            {"year": year, "product_id": product_id, "name": name})
        self._save()

    def get_last_order(self, user_id, recipient, year=None):
        p = self.get_profile(user_id, recipient)
        if not p or not p["past_orders"]:
            return None
        orders = p["past_orders"]
        if year:
            orders = [o for o in orders if o["year"] == year] or orders
        return orders[-1]
