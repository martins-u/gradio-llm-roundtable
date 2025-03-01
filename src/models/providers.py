from enum import Enum

class Provider(str, Enum):
    ANTHROPIC = "Anthropic"
    OPENROUTER = "OpenRouter"
    OPENAI = "OpenAI"

class ChatMode(str, Enum):
    STANDARD = "Standard Chat"
    ROUND_TABLE = "Round Table"