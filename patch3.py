import pathlib

def patch(path, old, new):
    p = pathlib.Path(path)
    text = p.read_text()
    assert old in text, f"Could not find the text to replace in {path}:\n{old}"
    p.write_text(text.replace(old, new, 1))
    print("patched", path)

patch("llm.py",
      '            if not temporary or attempt == retries - 1:\n                raise\n',
      '            if "PerDay" in msg:\n'
      '                print("  [llm] DAILY free quota used up for this model. '
      'Switch LLM_MODEL in .env or wait for the reset (midnight Pacific).")\n'
      '                raise\n'
      '            if not temporary or attempt == retries - 1:\n                raise\n')

patch("agents/reflection.py",
      '    critic_problems = llm_critique(product, profile_text) if profile else []\n',
      '    # the critic costs an LLM call, so only use it when the cheap rule check passed\n'
      '    critic_problems = [] if (rule_problems or not profile) else llm_critique(product, profile_text)\n')

patch("agents/router.py",
      '"repeat_last_order": "last year" in m or "same as" in m}',
      '"repeat_last_order": "last year" in m or "same as" in m,\n           "fallback": True}')

patch("concierge.py",
      '        if plan["intent"] == "preference_update":\n',
      '        if plan.get("fallback") and plan["intent"] == "preference_update":\n'
      '            return self._finish("Sorry, my language model is unavailable right now, so I could '
      'not save that. Please try again later.", trace, start, plan, None)\n\n'
      '        if plan["intent"] == "preference_update":\n')
