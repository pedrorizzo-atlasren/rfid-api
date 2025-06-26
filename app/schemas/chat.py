from typing import Optional, List, Any
from pydantic import BaseModel

class ChatRequest(BaseModel):
    prompt: str

class ChatResponse(BaseModel):
    session_id: str
    answer: str