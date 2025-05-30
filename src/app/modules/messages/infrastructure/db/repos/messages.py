from sqlalchemy.orm import Session
from src.app.modules.messages.infrastructure.db.models import Message

class MessageRepo:
    def __init__(self, db: Session):
        self.db = db

    def create(self, room_id: int, text: str):
        message = Message(room_id=room_id, text=text)
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        return message

    def list_by_room(self, room_id: int):
        return self.db.query(Message).filter(Message.room_id == room_id).all()
