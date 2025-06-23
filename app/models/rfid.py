from pydantic import BaseModel

class RFIDTag(BaseModel):
    epc: str
    channel: int
    last_seen: int
    seen_count: int
    antenna: int