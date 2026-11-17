import pathlib

def patch(path, old, new):
    p = pathlib.Path(path)
    text = p.read_text()
    assert old in text, f"Could not find the text to replace in {path}:\n{old}"
    p.write_text(text.replace(old, new, 1))
    print("patched", path)

patch("concierge.py",
      '            reply = ask(PLAIN_SYSTEM, f"Delivery info: {delivery_text}\\nCustomer: {message}")\n',
      '            reply = delivery_text      # the logistics tool already wrote the answer\n')

patch("concierge.py",
      '        trace.append(("routing", f"intent = {plan[\'intent\']}"))\n',
      '        trace.append(("routing", f"intent = {plan[\'intent\']}"))\n'
      '        if plan.get("fallback"):\n'
      '            trace.append(("fallback", "Language model unavailable - using basic rules, '
      'so preferences cannot be understood or saved"))\n')

patch("app.py",
      '    "revised": ("✏️", "Revised"),\n',
      '    "revised": ("✏️", "Revised"),\n    "fallback": ("⚠️", "Basic mode"),\n')
patch("app.py",
      '        elif kind == "revised":\n',
      '        elif kind == "fallback":\n'
      '            st.caption(f"⚠️ **Basic mode** · {detail}")\n'
      '        elif kind == "revised":\n')

patch("app.py",
      '                st.error(f"{type(e).__name__}: {str(e)[:300]}")\n',
      '                st.error(f"{type(e).__name__}: {str(e)[:300]}")\n'
      '                st.session_state.history.append({"role": "assistant", "trace": [], "latency": 0,\n'
      '                    "content": f"⚠️ Error: {type(e).__name__}: {str(e)[:200]}"})\n')
