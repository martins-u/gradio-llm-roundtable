from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from src.models.messages import Message
from src.models.providers import ChatMode, Provider

class RoundTableConfig(BaseModel):
    enabled: bool = Field(default=False)
    models: Dict[str, Tuple[Provider, str]] = Field(default_factory=dict)
    chairman_model: Optional[Tuple[Provider, str]] = Field(default=None)
    
    def add_model(self, name: str, provider: Provider, model: str) -> None:
        self.models[name] = (provider, model)
    
    def set_chairman(self, provider: Provider, model: str) -> None:
        self.chairman_model = (provider, model)
    
    def clear_models(self) -> None:
        self.models.clear()
        self.chairman_model = None

class ChatSession(BaseModel):
    system: str = Field(default="You are helpful asistant. Explain in depth.")
    history: List[Message] = Field(default_factory=list)
    round_table: RoundTableConfig = Field(default_factory=RoundTableConfig)
    mode: ChatMode = Field(default=ChatMode.STANDARD)
    
    def add_message(self, role: str, content: str, source: Optional[str] = None) -> None:
        self.history.append(Message(role=role, content=content, source=source))
    
    def clear_history(self) -> None:
        self.history.clear()
    
    def has_content(self) -> bool:
        return len(self.history) > 0
    
    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChatSession':
        # Handle backward compatibility with sessions saved before round table feature
        if 'mode' not in data:
            data['mode'] = ChatMode.STANDARD
        if 'round_table' not in data:
            data['round_table'] = RoundTableConfig().model_dump()
        return cls.model_validate(data)

class SystemPrompt(BaseModel):
    prompt: str