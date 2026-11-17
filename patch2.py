import pathlib

def patch(path, old, new):
    p = pathlib.Path(path)
    text = p.read_text()
    assert old in text, f"Could not find the text to replace in {path}:\n{old}"
    p.write_text(text.replace(old, new, 1))
    print("patched", path)

patch("llm.py", "max_output_tokens=max_tokens))",
      "max_output_tokens=max(max_tokens, 2048)))")
patch("llm.py", "return r.text\n", 'return r.text or ""\n')
patch("llm.py", '    start, end = text.find("{"), text.rfind("}")\n',
      '    start, end = text.find("{"), text.rfind("}")\n'
      '    if start == -1 or end == -1:\n'
      '        raise ValueError(f"no JSON in reply: {text[:100]!r}")\n')
patch("agents/router.py",
      'elif any(w in m for w in ["deliver", "shipping", "reach"]):',
      'elif any(w in m for w in ["deliver", "shipping", "reach"]) and not any(\n'
      '            w in m for w in ["cake", "gift", "flower", "chocolate", "buy", "need", "basket", "hamper"]):')
patch("concierge.py", 'Keep it under 80 words."""',
      'Never claim a product is nut-free, vegan, etc. unless its description says so.\n'
      'If no products are listed, say you could not find a match.\n'
      'Keep it under 80 words."""')
