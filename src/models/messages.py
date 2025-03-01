from typing import List, Optional
from pydantic import BaseModel, Field

class Message(BaseModel):
    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str = Field(..., min_length=1)
    source: Optional[str] = None  # Source of the message (model name) for round table discussions
    
    @classmethod
    def validate_messages(cls, messages: List['Message']) -> bool:
        if not messages:
            return True
            
        # First message should be from user
        if messages[0].role != "user":
            return False
            
        # Messages should alternate between user and assistant in standard mode
        # In round table mode, we may have multiple assistant messages in a row (from different models)
        for i in range(1, len(messages)):
            if messages[i].role == "user" and messages[i-1].role == "user":
                return False
                
        return True