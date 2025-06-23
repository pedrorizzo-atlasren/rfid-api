from pydantic import BaseModel

class RegisterEvent(BaseModel):
    epc: str
    timestamp: float
    status: str
    reason: str