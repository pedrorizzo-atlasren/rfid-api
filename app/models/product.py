# app/models.py

from sqlalchemy import Column, Integer, Text, Numeric
from database import Base

class Product(Base):
    __tablename__ = "products"          # nome da tabela no Postgres

    product_id   = Column(Integer, primary_key=True, index=True)
    product      = Column(Text,   nullable=False)
    manufacturer = Column(Text,   nullable=False)
    part_number  = Column(Text,   nullable=False, unique=True)
    description  = Column(Text,   nullable=True)
    ncm          = Column(Text,   nullable=True)
    datasheet    = Column(Text,   nullable=True)   # armazena URL ou caminho
    qtde         = Column(Integer, nullable=False, default=0)
    type         = Column(Text,   nullable=True)
    price        = Column(Numeric(12, 2), nullable=True)
