"""
THE ORCHESTRATOR - ties memory + router + specialists + reflection together.
Flow for each message:
  1. save message in short-term memory
  2. router decides intent + extracts preferences
  3. save any new preferences to semantic memory
  4. run the right specialist(s)  (catalog search, delivery check)
  5. DRAFT -> REFLECT -> REVISE loop (Part 4), then reply
  6. log latency + reflection stats to data/metrics.jsonl (used in Part 5)
"""

import datetime
import json
import time
from pathlib import Path

from llm import ask
from agents.router import route
from agents.catalog import catalog_specialist
from agents.logistics import check_delivery, find_district
from agents.reflection import run_reflection_loop
from memory.short_term import ShortTermMemory
from memory.semantic import SemanticMemory

METRICS_FILE = Path("data/metrics.jsonl")

PLAIN_SYSTEM = """You are Kapruka's friendly gift concierge in Sri Lanka.
Answer using ONLY the context given. Never invent products, prices or facts. Under 60 words."""


class Concierge:
    def __init__(self, long_term, semantic=None, short_term=None, router=route,
                 metrics_file=METRICS_FILE):
        self.long_term = long_term
        self.semantic = semantic or SemanticMemory()
        self.short_term = short_term or ShortTermMemory(max_messages=10)
        self.router = router
        self.metrics_file = Path(metrics_file) if metrics_file else None
        self.current_recipient = None

    def handle(self, user_id, message):
        start = time.time()
        trace = []                                     # events a UI can display (bonus)
        self.short_term.add("user", message)

        # --- Router ---
        plan = self.router(message, self.short_term.as_text(), self.current_recipient)
        trace.append(("routing", f"intent = {plan['intent']}"))
        if plan.get("fallback"):
            trace.append(("fallback", "Language model unavailable - using basic rules, so preferences cannot be understood or saved"))
        if plan.get("recipient"):
            self.current_recipient = plan["recipient"].lower()
        recipient = self.current_recipient

        # --- Save new preferences (semantic memory write) ---
        if recipient and (plan["likes"] or plan["dislikes"] or plan["allergies"] or plan.get("city")):
            self.semantic.update_profile(user_id, recipient, likes=plan["likes"],
                                         dislikes=plan["dislikes"],
                                         allergies=plan["allergies"], city=plan.get("city"))
            trace.append(("memory_saved", f"Updated profile for {recipient}"))

        profile = self.semantic.get_profile(user_id, recipient) if recipient else None
        profile_text = self.semantic.describe(user_id, recipient) if recipient else "unknown"
        if profile:
            trace.append(("memory_found", profile_text))

        if plan.get("fallback") and plan["intent"] == "preference_update":
            return self._finish("Sorry, my language model is unavailable right now, so I could not save that. Please try again later.", trace, start, plan, None)

        if plan["intent"] == "preference_update":
            reply = (f"Noted! I'll remember that for {recipient or 'them'}. "
                     "Want me to suggest some gifts?")
            return self._finish(reply, trace, start, plan, None)

        # --- Logistics specialist ---
        delivery_text = ""
        district = find_district(plan.get("city")) or find_district(message) \
            or find_district(profile.get("city") if profile else None)
        if plan["intent"] == "delivery" or district:
            result = check_delivery(district or "", plan.get("days_until_needed"))
            trace.append(("delivery_check", result["message"]))
            delivery_text = result["message"]

        # --- Delivery-only question: no product search needed ---
        if plan["intent"] == "delivery":
            reply = delivery_text      # the logistics tool already wrote the answer
            return self._finish(reply, trace, start, plan, None)

        # --- Catalog specialist ---
        last_order = None
        if recipient and plan.get("repeat_last_order"):
            last_order = self.semantic.get_last_order(user_id, recipient)
            if last_order:
                trace.append(("memory_found", f"Last order: {last_order['name']}"))
        found = catalog_specialist(message, self.long_term, profile, last_order)
        trace.append(("catalog_search", f"query = '{found['query']}'"))

        if not found["results"]:
            return self._finish("I couldn't find matching products right now. "
                                "Could you describe what you're looking for?",
                                trace, start, plan, None)

        # --- Part 4: Draft -> Reflect -> Revise ---
        def search_more(avoid):
            return catalog_specialist(message, self.long_term, profile, last_order,
                                      avoid=avoid)["results"]

        outcome = run_reflection_loop(message, found["results"], profile, profile_text,
                                      delivery_text, search_more=search_more)
        for step in outcome["log"]:
            verdict = "; ".join(step["violations"]) if step["violations"] else "passed"
            trace.append(("reflection", f"Round {step['round']}: {step['product']} -> {verdict}"))
            if step.get("claims_removed"):
                trace.append(("reflection", "Removed unsupported claim: " + ", ".join(step["claims_removed"])))
        if len(outcome["log"]) > 1:
            trace.append(("revised", "Recommendation changed after reflection"))

        return self._finish(outcome["reply"], trace, start, plan, outcome)

    def _finish(self, reply, trace, start, plan, outcome):
        self.short_term.add("assistant", reply)
        latency = round(time.time() - start, 2)
        log = outcome["log"] if outcome else []
        caught = sum(1 for s in log if s["violations"])
        if self.metrics_file:
            self.metrics_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.metrics_file, "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "time": datetime.datetime.now().isoformat(timespec="seconds"),
                    "intent": plan["intent"], "latency_s": latency,
                    "reflection_rounds": len(log), "violations_caught": caught,
                    "status": outcome["status"] if outcome else "n/a"}) + "\n")
        return {"reply": reply, "trace": trace, "latency_s": latency,
                "status": outcome["status"] if outcome else "n/a"}
