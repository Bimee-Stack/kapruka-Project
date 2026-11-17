import json
import os
import re
import time

from dotenv import load_dotenv

load_dotenv(override=True)          # .env wins over anything set in the terminal

PROVIDER = os.getenv("LLM_PROVIDER", "anthropic").lower()
DEFAULT_MODELS = {
    "anthropic": "claude-haiku-5-5",
    "openai": "gpt-4o-mini",
    "gemini": "gemini-2.0-flash",
}
MODEL = os.getenv("LLM_MODEL") or DEFAULT_MODELS.get(PROVIDER, "")
FALLBACKS = [m.strip() for m in os.getenv("LLM_FALLBACK_MODELS", "").split(",") if m.strip()]
MODELS = [MODEL] + [m for m in FALLBACKS if m != MODEL]     # tried in this order


def _ask_once(model, system, user, max_tokens=600):
    """One call to one model. No retries here."""
    if PROVIDER == "anthropic":
        import anthropic
        client = anthropic.Anthropic()
        r = client.messages.create(
            model=model, max_tokens=max_tokens, system=system,
            messages=[{"role": "user", "content": user}])
        return r.content[0].text

    if PROVIDER == "openai":
        from openai import OpenAI
        client = OpenAI()
        r = client.chat.completions.create(
            model=model, max_tokens=max_tokens,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}])
        return r.choices[0].message.content

    if PROVIDER == "gemini":
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        r = client.models.generate_content(
            model=model, contents=user,
            config=types.GenerateContentConfig(
                system_instruction=system,
                max_output_tokens=max(max_tokens, 2048)))
        return r.text or ""

    raise ValueError(f"Unknown LLM_PROVIDER '{PROVIDER}'. Use anthropic, openai or gemini.")


def ask(system, user, max_tokens=600, retries=3):
    """Ask the LLM. Retries when busy, then falls back to the next model."""
    last_error = None
    for model in MODELS:
        for attempt in range(retries):
            try:
                return _ask_once(model, system, user, max_tokens)
            except Exception as e:
                msg, last_error = str(e), e
                if "PerDay" in msg or "NOT_FOUND" in msg or "404" in msg:
                    print(f"  [llm] {model} is not usable right now (quota or name); trying next model")
                    break
                busy = any(c in msg for c in ("503", "429", "UNAVAILABLE", "overloaded"))
                if not busy:
                    raise
                if attempt < retries - 1:
                    wait = 2 * 2 ** attempt
                    print(f"  [llm] {model} busy, retrying in {wait}s...")
                    time.sleep(wait)
                else:
                    print(f"  [llm] {model} still busy; trying next model")
    raise last_error


def ask_json(system, user, max_tokens=400):
    """Like ask(), but parses the reply as JSON (LLMs sometimes add extra text)."""
    text = ask(system + "\nReply with ONLY a JSON object, no other text.", user, max_tokens)
    text = re.sub(r"```(?:json)?", "", text)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"no JSON in reply: {text[:100]!r}")
    return json.loads(text[start:end + 1])
