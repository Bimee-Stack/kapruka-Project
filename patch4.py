import pathlib

def patch(path, old, new):
    p = pathlib.Path(path)
    text = p.read_text()
    assert old in text, f"Could not find the text to replace in {path}:\n{old}"
    p.write_text(text.replace(old, new, 1))
    print("patched", path)

patch("agents/reflection.py",
      "Never invent products, prices or ingredients. Mention delivery info if given.",
      "Never invent products, prices or ingredients. Mention delivery info if given.\n"
      "Never say a product is nut-free, gluten-free, dairy-free, eggless or allergy-friendly\n"
      "unless its listed details say so.")

patch("agents/reflection.py",
      "# ---------------- THE LOOP ----------------\n",
      '''# ---------------- CLAIM GUARD ----------------
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
    sentences = re.split(r"(?<=[.!?])\\s+", reply)
    kept = [s for s in sentences if not any(b in s.lower() for b in bad)]
    cleaned = " ".join(kept).strip() or \\
        f"I'd suggest the {product['name']} for {product['price']} {product['currency']}."
    return cleaned, sorted(set(bad))


# ---------------- THE LOOP ----------------
''')

patch("agents/reflection.py",
      '        if not check["violations"]:\n            allergies = (profile or {}).get("allergies", [])\n',
      '        if not check["violations"]:\n'
      '            reply, removed = strip_unsupported_claims(reply, product, profile)\n'
      '            log[-1]["claims_removed"] = removed\n'
      '            allergies = (profile or {}).get("allergies", [])\n')

patch("concierge.py",
      '            trace.append(("reflection", f"Round {step[\'round\']}: {step[\'product\']} -> {verdict}"))\n',
      '            trace.append(("reflection", f"Round {step[\'round\']}: {step[\'product\']} -> {verdict}"))\n'
      '            if step.get("claims_removed"):\n'
      '                trace.append(("reflection", "Removed unsupported claim: " + ", ".join(step["claims_removed"])))\n')

patch("agents/catalog.py", "<short product search phrase>", "<short product search phrase, no city names>")
