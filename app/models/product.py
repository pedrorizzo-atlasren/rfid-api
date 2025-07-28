# app/models.py

from sqlalchemy import Column, Integer, Text, Numeric, ForeignKey
from database import Base
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector


class Product(Base):
    __tablename__ = "products"          # nome da tabela no Postgres

    product_id   = Column(Integer, primary_key=True, index=True)
    product      = Column(Text,   nullable=False)
    manufacturer = Column(Text,   nullable=False)
    part_number  = Column(Text,   nullable=False)
    description  = Column(Text,   nullable=True)
    datasheet    = Column(Text,   nullable=True)   # armazena URL ou caminho
    price        = Column(Numeric(12, 2), nullable=True)
    embedding    = Column(Vector(1536), nullable=True)

    type_id = Column(Integer, ForeignKey("types.type_id", ondelete="SET NULL"))
    # ncm_id  = Column(Integer, ForeignKey("ncm.ncm_id", ondelete="SET NULL"))

    type_obj = relationship("Type", back_populates="products")
    # ncm_obj  = relationship("NCM",  back_populates="products")

    items = relationship(
        "Item",
        back_populates="product",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
