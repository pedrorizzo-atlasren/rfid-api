from pydantic import BaseModel
from typing import Optional


class RegisterProduct(BaseModel):
    product: str
    product_type: str
    name: str
    part_number: str
    manufacturer: str
    price: Optional[float] = None
    datasheetURL: Optional[str] = None
    description: Optional[str] = None
    ncm: Optional[str] = None
