from sqlalchemy import Column, Integer, String, Text, ForeignKey, BigInteger
from sqlalchemy.orm import relationship
from src.app.modules.messages.infrastructure.db.models import Base

class Room(Base):
    __tablename__ = "rooms"
    id = Column(Integer, primary_key=True)
    location_id = Column(Integer, ForeignKey("locations.id", ondelete="CASCADE"))
    name = Column(Text, nullable=False)
    tg_group_id = Column(BigInteger, nullable=False)
    qr_token = Column(String, unique=True, nullable=False)
    location = relationship("Location", back_populates="rooms")