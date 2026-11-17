"""Quick demo that all 3 memory tiers work. Run: python test_memory.py"""
from memory.short_term import ShortTermMemory
from memory.semantic import SemanticMemory
from memory.long_term import LongTermMemory

# --- Tier 1 ---
st = ShortTermMemory(max_messages=5)
st.add("user", "I need a cake for my wife's birthday this Sunday. Same as last year.")
print("SHORT-TERM:\n" + st.as_text(), "\n")

# --- Tier 3 ---
sem = SemanticMemory()
sem.update_profile("customer_001", "wife", likes=["dark chocolate"],
                   allergies=["nuts"], city="Colombo")
sem.add_past_order("customer_001", "wife", "cake00demo01", "Nut-free Chocolate Cake", 2025)
print("SEMANTIC:", sem.describe("customer_001", "wife"))
print("Last order:", sem.get_last_order("customer_001", "wife"), "\n")

# --- Tier 2 ---
lt = LongTermMemory()
lt.build_from_catalog("data/catalog.json")
for r in lt.search("chocolate birthday cake", limit=3):
    print(f"LONG-TERM: {r['name']} | {r['price']} {r['currency']} | score {r['score']}")
