"""Talk to the concierge in the terminal:  python chat_cli.py"""
from memory.long_term import LongTermMemory
from concierge import Concierge

lt = LongTermMemory()
lt.build_from_catalog("data/catalog.json")   # rebuilds every run; fine for small catalogs
bot = Concierge(lt)

print("Kapruka Gift Concierge (type 'quit' to exit)\n")
while True:
    text = input("You: ").strip()
    if text.lower() in ("quit", "exit"):
        break
    out = bot.handle("customer_001", text)
    for kind, detail in out["trace"]:
        print(f"   [{kind}] {detail}")
    print(f"Bot: {out['reply']}\n")
