from sqlalchemy.orm import Session
from src.app.modules.messages.infrastructure.db.models import Location

class LocationRepo:
    def __init__(self, db: Session):
        self.db = db

    def get_by_address(self, address: str):
        return self.db.query(Location).filter(Location.address == address).first()

    def create(self, address: str):
        location = Location(address=address)
        self.db.add(location)
        self.db.commit()
        self.db.refresh(location)
        return location

    def list(self):
        return self.db.query(Location).all()
