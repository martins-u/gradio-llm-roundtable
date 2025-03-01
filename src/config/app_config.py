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
        config.models = {}
        
        # Only add models for providers with valid API keys
        if config.anthropic_api_key:
            config.models[Provider.ANTHROPIC] = ["claude-3-7-sonnet-20250219", "claude-3-5-sonnet-20241022", "claude-3-opus-20240229"]
        
        if config.openrouter_api_key:
            config.models[Provider.OPENROUTER] = ["deepseek/deepseek-r1"]
        
        if config.openai_api_key:
            config.models[Provider.OPENAI] = ["gpt-4o", "o1-preview", "gpt-4.5-preview"]
        
        return config
    
    @classmethod
    def validate_config(cls, config: 'Config') -> bool:
        api_key_count = 0
        if config.anthropic_api_key:
            api_key_count += 1
        else:
            logger.info("ANTHROPIC_API_KEY environment variable is not set")
        if config.openrouter_api_key:
            api_key_count += 1
        else:
            logger.info("OPENROUTER_API_KEY environment variable is not set")
        if config.openai_api_key:
            api_key_count += 1
        else:
            logger.info("OPENAI_API_KEY environment variable is not set")

        if api_key_count == 0:
            logger.error("No API keys are set")
            return False
        return True
        