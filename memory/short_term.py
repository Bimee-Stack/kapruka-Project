"""
Tier 1: SHORT-TERM MEMORY
-------------------------
Just a Python list holding the current conversation.
It forgets old messages once the list gets too long, like a person
only remembering the last few minutes of a chat.
"""


class ShortTermMemory:
    def __init__(self, max_messages=10):
        self.max_messages = max_messages
        self.messages = []          # [{"role": "user", "content": "..."}, ...]

    def add(self, role, content):
        """role is 'user' or 'assistant'."""
        self.messages.append({"role": role, "content": content})
        # keep only the most recent messages
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]

    def get(self):
        return list(self.messages)

    def as_text(self):
        """Chat history as plain text, handy for putting inside a prompt."""
        return "\n".join(f"{m['role']}: {m['content']}" for m in self.messages)

    def clear(self):
        self.messages = []
