from sqlalchemy import Column, Integer, Text
from sqlalchemy.orm import relationship
from database import Base

class NCM(Base):
    __tablename__ = "ncm"

    ncm_id      = Column(Integer, primary_key=True, index=True)
    ncm        = Column(Text, nullable=False, unique=True)
    description = Column(Text)

    products = relationship(
        "Product",
        back_populates="ncm_obj",
        passive_deletes=True,
    )