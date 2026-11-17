"""
BONUS: The Concierge UI  (Streamlit)
Run:  streamlit run app.py
Shows the agent's "thinking" (routing, memory recall, reflection) next to each answer.
Note: Qdrant local mode allows ONE program at a time - close chat_cli.py first.
"""

import streamlit as st

from memory.long_term import LongTermMemory, COLLECTION
from concierge import Concierge

USER_ID = "customer_001"

st.set_page_config(page_title="Kapruka Gift Concierge", page_icon="🎁")

# What each trace event looks like on screen
ICONS = {
    "routing": ("🧭", "Router"),
    "memory_saved": ("💾", "Memory saved"),
    "memory_found": ("🧠", "Memory found"),
    "catalog_search": ("🔎", "Catalog search"),
    "delivery_check": ("🚚", "Delivery check"),
    "reflection": ("🔍", "Reflection"),
    "revised": ("✏️", "Revised"),
}


@st.cache_resource(show_spinner="Loading the Kapruka catalog memory...")
def load_long_term():
    """Loaded ONCE and shared (Streamlit re-runs this script on every click)."""
    lt = LongTermMemory()
    if not lt.client.collection_exists(COLLECTION):
        lt.build_from_catalog("data/catalog.json")
    return lt


def show_chips(trace):
    """The little 'Memory found' badges from the whiteboard sketch."""
    for kind, detail in trace:
        if kind == "memory_found":
            st.caption(f"🧠 **Memory found** · {detail}")
        elif kind == "revised":
            st.caption(f"✏️ **Revised** · I changed my first pick after checking it")


def show_trace(trace):
    for kind, detail in trace:
        icon, label = ICONS.get(kind, ("•", kind))
        st.markdown(f"{icon} **{label}:** {detail}")


# ---------------- session state (one per browser tab) ----------------
if "bot" not in st.session_state:
    st.session_state.bot = Concierge(load_long_term())
    st.session_state.history = []      # [{"role", "content", "trace", "latency"}]
bot = st.session_state.bot

st.title("🎁 Kapruka Gift Concierge")
st.caption("I remember your loved ones' tastes and allergies, and double-check every gift.")

# ---------------- past messages ----------------
for m in st.session_state.history:
    with st.chat_message(m["role"]):
        if m["role"] == "assistant":
            show_chips(m["trace"])
        st.markdown(m["content"])
        if m["role"] == "assistant":
            with st.expander(f"How I decided ({m['latency']}s)"):
                show_trace(m["trace"])

# ---------------- new message ----------------
text = st.chat_input("e.g. I need a cake for my wife's birthday, deliver to Kandy")
if text:
    st.session_state.history.append({"role": "user", "content": text})
    with st.chat_message("user"):
        st.markdown(text)

    with st.chat_message("assistant"):
        out = None
        with st.status("Thinking...", expanded=True) as status:
            try:
                out = bot.handle(USER_ID, text)
                show_trace(out["trace"])
                status.update(label="Done thinking", state="complete", expanded=False)
            except Exception as e:
                status.update(label="Something went wrong", state="error")
                st.error(f"{type(e).__name__}: {str(e)[:300]}")

        if out:
            show_chips(out["trace"])
            if out["status"] == "none_safe":
                st.warning(out["reply"])
            else:
                st.markdown(out["reply"])
            st.caption(f"⏱ {out['latency_s']}s")
            st.session_state.history.append({"role": "assistant", "content": out["reply"],
                                             "trace": out["trace"], "latency": out["latency_s"]})

# ---------------- sidebar: what the bot remembers (semantic memory) ----------------
with st.sidebar:
    st.header("🧠 What I remember")
    people = bot.semantic.list_recipients(USER_ID)
    if not people:
        st.caption("Nothing yet. Tell me about someone you buy gifts for.")
    for who in people:
        p = bot.semantic.get_profile(USER_ID, who)
        with st.expander(who.title(), expanded=True):
            if p["allergies"]:
                st.markdown("⚠️ **Allergic to:** " + ", ".join(p["allergies"]))
            if p["likes"]:
                st.markdown("❤️ **Likes:** " + ", ".join(p["likes"]))
            if p["dislikes"]:
                st.markdown("👎 **Dislikes:** " + ", ".join(p["dislikes"]))
            if p.get("city"):
                st.markdown("📍 " + p["city"])
            for o in p["past_orders"]:
                st.markdown(f"🎂 {o['year']}: {o['name']}")

    st.divider()
    if st.button("New conversation"):
        bot.short_term.clear()
        bot.current_recipient = None
        st.session_state.history = []
        st.rerun()
    if st.button("Rebuild catalog index"):
        load_long_term().build_from_catalog("data/catalog.json")
        st.success("Catalog re-indexed.")
