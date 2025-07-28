from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class RegisterEvent(BaseModel):
    item_id: str
    log_id: int
    description: str

class EventOut(BaseModel):
    log_id: int
    item_id: str
    status: str
    timestamp: datetime
    registered: bool
    description: Optional[str]

    class Config:
        orm_mode = True