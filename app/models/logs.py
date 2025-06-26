from sqlalchemy import Column, Integer, Text, Boolean, TIMESTAMP, ForeignKey
from sqlalchemy.orm import relationship
from database import Base
# from models.item import Item

class Log(Base):
    __tablename__ = "logs"

    log_id     = Column(Integer, primary_key=True, index=True)
    item_id    = Column(Integer, ForeignKey("items.item_id", ondelete="CASCADE"), nullable=False)
    status     = Column(Text, nullable=False)
    timestamp  = Column(TIMESTAMP(timezone=True), nullable=False)
    registered = Column(Boolean, default=False, nullable=False)
    description = Column(Text, nullable=True)

    # relacionamento opcional para facilitar joins
    item       = relationship("Item", back_populates="logs")
