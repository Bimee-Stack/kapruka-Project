"""
PART 4: THE REFLECTION LOOP   Draft -> Reflect -> Revise
--------------------------------------------------------
1. DRAFT   : the LLM picks one product from the candidates and writes a reply.
2. REFLECT : we critique the pick against the recipient's profile, in TWO ways:
              (a) rule check  - plain Python keyword matching (reliable, never forgets)
              (b) LLM critic  - catches hidden ingredients (e.g. almonds in a macaroon)
3. REVISE  : if a violation is found, throw that product away and draft again.
Safety rule: "no allergen word found" is NOT the same as "safe". Unless the product
explicitly says e.g. "nut-free", we add a caution asking the customer to verify.
"""

from llm import ask_json

# Starter lists - extend them for your report. Deliberately over-cautious
# (e.g. "coconut" contains "nut" and gets flagged). A false alarm is safer than a miss.
ALLERGENS = {
    "nuts": ["nut", "almond", "cashew", "walnut", "pecan", "pistachio", "hazelnut",
             "peanut", "praline", "nougat", "marzipan", "macaroon", "gianduja"],
    "gluten": ["gluten", "wheat"],
    "dairy": ["milk", "butter", "cream", "cheese", "dairy", "yoghurt", "yogurt"],
    "egg": ["egg"],
}
SAFE_PHRASES = {
    "nuts": ["nut-free", "nut free", "nutfree", "free from nuts", "without nuts",
             "no nuts", "peanut-free", "peanut free"],
    "gluten": ["gluten-free", "gluten free"],
    "dairy": ["dairy-free", "dairy free", "lactose-free", "lactose free"],
    "egg": ["eggless", "egg-free", "egg free"],
}


def canonical(item):
    """'tree nuts' -> ('nuts', [...keywords...]). Unknown items use the word itself."""
    item = item.lower().strip()
    for name, words in ALLERGENS.items():
        if name in item or any(w in item for w in words):
            return name, words
    return item, [item]


# ---------------- REFLECT ----------------
def rule_check(product, profile):
    """Return (violations, verified_safe)."""
    text = f"{product['name']} {product.get('description', '')}".lower()
    allergies = (profile or {}).get("allergies", [])
    violations, verified = [], True

    for allergy in allergies:
        name, words = canonical(allergy)
        safe_phrases = SAFE_PHRASES.get(name, [])
        scan = text
        for phrase in safe_phrases:                 # "nut-free" must not trigger "nut"
            scan = scan.replace(phrase, " ")
        hits = [w for w in words if w in scan]
        if hits:
            violations.append(f"mentions '{hits[0]}' but the recipient is allergic to {allergy}")
        if not any(phrase in text for phrase in safe_phrases):
            verified = False                        # never explicitly confirmed safe

    for dislike in (profile or {}).get("dislikes", []):
        if dislike.lower() in text:
            violations.append(f"recipient dislikes {dislike}")

    return violations, verified


CRITIC_SYSTEM = """You are a strict safety reviewer for a gift concierge.
Given a recipient profile and a product, decide if the product CLEARLY conflicts with the
recipient's allergies or dislikes, including hidden ingredients (e.g. almond in a macaroon).
If the description simply doesn't mention ingredients, that is NOT a conflict.
Return JSON: {"ok": true or false, "problems": ["short reason", ...]}"""


def llm_critique(product, profile_text):
    try:
        r = ask_json(CRITIC_SYSTEM,
                     f"Recipient: {profile_text}\nProduct: {product['name']}. "
                     f"{product.get('description', '')[:300]}")
        return [] if r.get("ok", True) else (r.get("problems") or ["flagged by reviewer"])
    except Exception as e:
        print(f"  [reflect] LLM critic failed ({e}); relying on rule check")
        return []


def reflect(product, profile, profile_text):
    rule_problems, verified = rule_check(product, profile)
    # the critic costs an LLM call, so only use it when the cheap rule check passed
    critic_problems = [] if (rule_problems or not profile) else llm_critique(product, profile_text)
    return {"violations": rule_problems + critic_problems, "verified_safe": verified}


# ---------------- DRAFT ----------------
DRAFT_SYSTEM = """You are Kapruka's gift concierge in Sri Lanka.
Pick the ONE best product from the numbered list and write a short, friendly
recommendation (under 60 words) using its exact name and price.
Never invent products, prices or ingredients. Mention delivery info if given.
Never say a product is nut-free, gluten-free, dairy-free, eggless or allergy-friendly
unless its listed details say so.
Return JSON: {"choice": <number from the list>, "reply": "<your message>"}"""


def draft(message, candidates, profile_text, delivery_text, rejected):
    lines = [f"{i + 1}. {p['name']} | {p['price']} {p['currency']} | "
             f"{p.get('description', '')[:150]}" for i, p in enumerate(candidates)]
    user = (f"Recipient profile: {profile_text}\nDelivery info: {delivery_text or 'none'}\n"
            f"Products:\n" + "\n".join(lines) + "\n")
    if rejected:
        user += "Already rejected (do not choose similar ones): " + " | ".join(rejected) + "\n"
    user += f"Customer said: {message}"
    try:
        r = ask_json(DRAFT_SYSTEM, user, max_tokens=500)
        idx = int(r["choice"]) - 1
        if not 0 <= idx < len(candidates):
            raise ValueError("choice out of range")
        return idx, r["reply"]
    except Exception as e:
        print(f"  [draft] LLM failed ({e}); using first candidate")
        p = candidates[0]
        return 0, f"I suggest the {p['name']} for {p['price']} {p['currency']}."


# ---------------- CLAIM GUARD ----------------
EXTRA_CLAIMS = ["allergy-friendly", "allergy friendly", "does not contain nuts",
                "doesn't contain nuts", "contains no nuts", "safe for her", "safe for him"]


def strip_unsupported_claims(reply, product, profile):
    """Delete sentences claiming 'nut-free' etc. when the product details don't say it."""
    import re
    text = f"{product['name']} {product.get('description', '')}".lower()
    low = reply.lower()
    bad = []
    for allergy in (profile or {}).get("allergies", []):
        name, _ = canonical(allergy)
        for phrase in SAFE_PHRASES.get(name, []) + EXTRA_CLAIMS:
            if phrase in low and phrase not in text:
                bad.append(phrase)
    if not bad:
        return reply, []
    sentences = re.split(r"(?<=[.!?])\s+", reply)
    kept = [s for s in sentences if not any(b in s.lower() for b in bad)]
    cleaned = " ".join(kept).strip() or \
        f"I'd suggest the {product['name']} for {product['price']} {product['currency']}."
    return cleaned, sorted(set(bad))


# ---------------- THE LOOP ----------------
def run_reflection_loop(message, candidates, profile, profile_text, delivery_text="",
                        max_rounds=3, search_more=None):
    pool, log, rejected, retried = list(candidates), [], [], False

    for round_no in range(1, max_rounds + 1):
        if not pool and search_more and not retried:     # ran out: one fresh search
            retried = True
            seen = {r.split(":")[0] for r in rejected}
            pool = [p for p in search_more(rejected) if p["name"] not in seen]
        if not pool:
            break

        idx, reply = draft(message, pool, profile_text, delivery_text, rejected)   # DRAFT
        product = pool[idx]
        check = reflect(product, profile, profile_text)                            # REFLECT
        log.append({"round": round_no, "product": product["name"],
                    "violations": check["violations"]})

        if not check["violations"]:
            reply, removed = strip_unsupported_claims(reply, product, profile)
            log[-1]["claims_removed"] = removed
            allergies = (profile or {}).get("allergies", [])
            if allergies and not check["verified_safe"]:
                reply += (f"\n\nNote: the product details don't confirm it is free of "
                          f"{', '.join(allergies)}, so please verify the ingredients with "
                          f"Kapruka before ordering.")
            return {"status": "ok", "reply": reply, "product": product, "log": log}

        rejected.append(f"{product['name']}: {'; '.join(check['violations'])}")      # REVISE
        pool.pop(idx)

    allergies = ", ".join((profile or {}).get("allergies", []))
    why = f"given an allergy to {allergies}" if allergies else "for this recipient"
    return {"status": "none_safe", "product": None, "log": log,
            "reply": f"I'm sorry, I couldn't find a product I'm confident is suitable {why} "
                     f"in my search. Could you tell me more about what they'd enjoy? You can "
                     f"also ask Kapruka support about allergy-friendly options."}
