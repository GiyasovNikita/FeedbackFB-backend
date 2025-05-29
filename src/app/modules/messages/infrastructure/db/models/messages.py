from sqlalchemy import Column, Integer, Text, ForeignKey, TIMESTAMP, func

from src.app.modules.messages.infrastructure.db.models import Base

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True)
    room_id = Column(Integer, ForeignKey("rooms.id", ondelete="CASCADE"))
    text = Column(Text, nullable=False)
    timestamp = Column(TIMESTAMP(timezone=True), server_default=func.now())