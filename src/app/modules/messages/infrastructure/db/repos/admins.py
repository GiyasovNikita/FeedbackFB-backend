from sqlalchemy.orm import Session
from src.app.modules.messages.infrastructure.db.models import Admin

class AdminRepo:
    def __init__(self, db: Session):
        self.db = db

    def is_admin(self, username: str) -> bool:
        return self.db.query(Admin).filter(Admin.username == username).first() is not None
