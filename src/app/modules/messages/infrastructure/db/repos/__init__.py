from fastapi import Depends
from src.app.modules.messages.infrastructure.db.session import get_db
from .messages import MessageRepo
from .admins import AdminRepo
from .locations import LocationRepo
from .rooms import RoomRepo

def get_room_repo(db=Depends(get_db)):
    return RoomRepo(db)

def get_location_repo(db=Depends(get_db)):
    return LocationRepo(db)

def get_message_repo(db=Depends(get_db)):
    return MessageRepo(db)

def get_admin_repo(db=Depends(get_db)):
    return AdminRepo(db)