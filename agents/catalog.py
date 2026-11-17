"""
CATALOG SPECIALIST  (tool-use for RAG product search)
-----------------------------------------------------
"Tool use" = the LLM decides WHICH tool to call and with WHAT arguments,
and our code actually runs it. Here we have one tool: search_catalog.
"""

from llm import ask_json

TOOL_DESCRIPTION = """Available tool:
 search_catalog(query: str) - semantic search over the Kapruka product catalog.
Reply with JSON: {"tool": "search_catalog", "query": "<short product search phrase, no city names>"}"""


def catalog_specialist(message, long_term, profile=None, last_order=None, avoid=None):
    """Return candidate products from Qdrant. `avoid` = notes about rejected picks."""
    context = f"Customer message: {message}\n"
    if profile:
        context += f"Recipient likes: {profile.get('likes')}\n"
        if profile.get("allergies"):
            context += (f"Recipient is allergic to: {profile['allergies']}. "
                        f"Put words like 'nut free' in the query when relevant.\n")
    if last_order:
        context += f"Previously bought for this recipient: {last_order['name']}\n"
    if avoid:
        context += f"These earlier picks were unsuitable, search differently: {avoid}\n"

    try:
        call = ask_json("You pick the best tool call for a gift search.\n" + TOOL_DESCRIPTION,
                        context)
        query = call.get("query") or message
    except Exception as e:
        print(f"  [catalog] LLM failed ({e}); searching with the raw message")
        query = message

    results = long_term.search(query, limit=5)
    return {"query": query, "results": results}
