from sqlalchemy import Column, Integer, Text
from sqlalchemy.orm import relationship

from src.app.modules.messages.infrastructure.db.models import Base

class Location(Base):
    __tablename__ = "locations"
    id = Column(Integer, primary_key=True)
    address = Column(Text, nullable=False)
    rooms = relationship("Room", back_populates="location")