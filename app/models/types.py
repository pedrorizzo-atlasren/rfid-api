from sqlalchemy import Column, Integer, Text
from database import Base
from sqlalchemy.orm import relationship


class Type(Base):
    __tablename__ = "types"

    type_id     = Column(Integer, primary_key=True, index=True)
    type        = Column(Text, nullable=False)
    description = Column(Text)

    
    products = relationship(
        "Product",
        back_populates="type_obj",
        passive_deletes=True,
    )
