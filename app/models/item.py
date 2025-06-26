# models/item.py
from sqlalchemy import (
    Column, Integer, Text, TIMESTAMP, ForeignKey
)
from sqlalchemy.orm import relationship
from database import Base
# from models.logs import Log
# from models.product import Product

class Item(Base):
    __tablename__ = "items"

    item_id     = Column(Integer, primary_key=True, index=True)
    product_id  = Column(
        Integer,
        ForeignKey("products.product_id", ondelete="RESTRICT"),
        nullable=False,
    )
    location    = Column(Text)
    status      = Column(Text)    # ex.: 'baixa', 'saida', etc.
    status_desc = Column(Text)
    ts          = Column(
        TIMESTAMP(timezone=True),
        server_default="now()",
        nullable=False
    )

    # Relação com logs
    logs = relationship(
        "Log",
        back_populates="item",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    product = relationship(
        "Product",
        back_populates="items",
        passive_deletes=True,
        cascade="all, delete"
    )
