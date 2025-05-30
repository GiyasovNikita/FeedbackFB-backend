from sqlalchemy.orm import Session
from src.app.modules.messages.infrastructure.db.models import Room

class RoomRepo:
    def __init__(self, db: Session):
        self.db = db

    def get_by_token(self, token: str):
        return self.db.query(Room).filter(Room.qr_token == token).first()

    def create(self, location_id: int, name: str, tg_group_id: int, token: str):
        room = Room(location_id=location_id, name=name, tg_group_id=tg_group_id, qr_token=token)
        self.db.add(room)
        self.db.commit()
        self.db.refresh(room)
        return room

    def get_by_id(self, room_id: int):
        return self.db.query(Room).filter(Room.id == room_id).first()

    def list_by_location(self, location_id: int):
        return self.db.query(Room).filter(Room.location_id == location_id).all()
