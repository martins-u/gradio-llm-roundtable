import json
import logging
from pathlib import Path
from typing import List, Optional, Tuple

from src.config import PathConfig  
from src.models import ChatSession, SystemPrompt
from src.utils import get_error_details

logger = logging.getLogger(__name__)

class SessionManager:
    def __init__(self):
        self.sessions_dir = PathConfig.SESSIONS_DIR
        self.sessions_dir.mkdir(exist_ok=True)
    
    def save_session(self, session: ChatSession, filename: str) -> str:
        if not session.has_content():
            return "Nothing to save - session is empty"
            
        if not filename.endswith('.json'):
            filename += '.json'
        filepath = self.sessions_dir / filename
        try:
            with filepath.open("w", encoding="utf-8") as f:
                json.dump(session.model_dump(), f, indent=2)
            return f"Session saved to {filename}"
        except Exception as e:
            error_msg = get_error_details(e)
            logger.error(f"Error saving session: {error_msg}")
            raise type(e)(error_msg)

    def load_session(self, filename: str) -> Tuple[ChatSession, str]:
        filepath = self.sessions_dir / filename
        try:
            with filepath.open("r", encoding="utf-8") as f:
                data = json.load(f)
                if not data.get("history"):
                    return ChatSession(), "Session file is empty or invalid"
                session = ChatSession.model_validate(data)
                return session, f"Session loaded from {filename}"
        except Exception as e:
            error_msg = get_error_details(e)
            logger.error(f"Error loading session: {error_msg}")
            raise type(e)(error_msg)

    def list_sessions(self) -> List[str]:
        """List session files ordered by last modification time (newest first)"""
        session_files = self.sessions_dir.glob("*.json")
        return sorted([f.name for f in session_files], 
                      key=lambda x: (self.sessions_dir / x).stat().st_mtime, 
                      reverse=True)

class PromptManager:
    def __init__(self):
        self.prompts_dir = PathConfig.PROMPTS_DIR
        self.prompts_dir.mkdir(exist_ok=True)
    
    def load_prompt(self, filename: str) -> str:
        try:
            with (self.prompts_dir / filename).open('r', encoding='utf-8') as f:
                prompt_data = SystemPrompt.model_validate(json.load(f))
                return prompt_data.prompt
        except Exception as e:
            error_msg = get_error_details(e)
            logger.error(f"Error loading prompt: {error_msg}")
            raise type(e)(error_msg)

    def list_prompts(self) -> List[str]:
        return [f.name for f in self.prompts_dir.glob("*.json")]

    def load_default_prompt(self) -> Optional[str]:
        try:
            if (self.prompts_dir / PathConfig.DEFAULT_PROMPT_FILE).exists():
                return self.load_prompt(PathConfig.DEFAULT_PROMPT_FILE)
            return None
        except Exception as e:
            error_msg = get_error_details(e)
            logger.error(f"Error loading default prompt: {error_msg}")
            return None