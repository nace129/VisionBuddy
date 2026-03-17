# memory.py — Session memory for VisionBuddy agent

class Memory:
    def __init__(self, max_frames=5, max_messages=10):
        self.frames = []           # last N scene descriptions
        self.messages = []         # conversation history
        self.last_description = "" # last thing spoken
        self.max_frames = max_frames
        self.max_messages = max_messages

    def add_frame(self, raw_vision: str, mode: str):
        """Store a scene frame"""
        self.frames.append({
            "vision": raw_vision[:200],
            "mode": mode
        })
        self.last_description = raw_vision
        # Keep only last N frames
        if len(self.frames) > self.max_frames:
            self.frames.pop(0)

    def add_message(self, role: str, content: str):
        """Store a conversation message"""
        self.messages.append({
            "role": role,
            "content": content
        })
        # Keep only last N messages
        if len(self.messages) > self.max_messages:
            self.messages.pop(0)

    def get_context(self) -> str:
        """Get full conversation context as string"""
        if not self.messages:
            return ""
        lines = []
        for msg in self.messages[-6:]:  # last 6 messages
            role = "User" if msg["role"] == "user" else "VisionBuddy"
            lines.append(f"{role}: {msg['content']}")
        return "\n".join(lines)

    def get_last_scenes(self) -> str:
        """Get recent scene descriptions"""
        if not self.frames:
            return ""
        return " | ".join([f["vision"][:100] for f in self.frames[-3:]])

    def clear(self):
        """Reset everything"""
        self.frames = []
        self.messages = []
        self.last_description = ""

# Single shared instance used across the app
memory = Memory()