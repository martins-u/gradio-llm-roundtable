from pathlib import Path

class PathConfig:
    SESSIONS_DIR = Path("chatbot_sessions")
    PROMPTS_DIR = Path("chatbot_prompts")
    DEFAULT_PROMPT_FILE = "code_guru.json"

    @classmethod
    def ensure_dirs(cls):
        cls.SESSIONS_DIR.mkdir(exist_ok=True)
        cls.PROMPTS_DIR.mkdir(exist_ok=True)