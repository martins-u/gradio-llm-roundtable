from dataclasses import dataclass
from typing import Dict, List, Optional
import os
import logging

logger = logging.getLogger(__name__)

@dataclass
class Config:
    anthropic_api_key: str
    openrouter_api_key: str
    openai_api_key: str
    max_tokens: int = 8192
    models: Dict[str, List[str]] = None
    
    def __post_init__(self):
        if self.models is None:
            self.models = {}
    
    @classmethod
    def load_from_env(cls) -> 'Config':
        config = cls(
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
            openrouter_api_key=os.getenv("OPENROUTER_API_KEY", ""),
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        )
        
        from src.models.providers import Provider
        config.models = {
            Provider.ANTHROPIC: ["claude-3-7-sonnet-20250219", "claude-3-5-sonnet-20241022", "claude-3-opus-20240229"],
            Provider.OPENROUTER: ["deepseek/deepseek-r1"],
            Provider.OPENAI: ["gpt-4o", "o1-preview", "gpt-4.5-preview"]
        }
        
        return config
    
    @classmethod
    def validate_config(cls, config: 'Config') -> bool:
        if not config.anthropic_api_key:
            logger.error("ANTHROPIC_API_KEY environment variable is not set")
            return False
        if not config.openrouter_api_key:
            logger.error("OPENROUTER_API_KEY environment variable is not set")
            return False
        if not config.openai_api_key:
            logger.error("OPENAI_API_KEY environment variable is not set")
            return False
        return True