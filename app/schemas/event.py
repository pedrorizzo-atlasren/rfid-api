from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class RegisterEvent(BaseModel):
    item_id: int
    log_id: int
    description: str

class EventOut(BaseModel):
    log_id: int
    item_id: int
    status: str
    timestamp: datetime
    registered: bool
    description: Optional[str]

    class Config:
        orm_mode = True