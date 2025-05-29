from fastapi import APIRouter, Depends, Form, HTTPException, Query
from sqlalchemy.orm import Session

from src.app.modules.messages.application.schemas import Feedback, RoomInfo
from src.app.modules.messages.application.services.feedback_service import (
    handle_send_feedback,
    handle_get_room_info,
    handle_create_room,
    handle_admin_auth,
    handle_add_location, handle_list_locations, handle_rooms_by_location
)
from src.app.modules.messages.infrastructure.db.session import get_db

router = APIRouter(prefix="/feedback", tags=["Feedback"])

@router.post("/{token}")
def send_feedback(token: str, feedback: Feedback, db: Session = Depends(get_db)):
    return handle_send_feedback(token, feedback, db)

@router.get("/room/{token}", response_model=RoomInfo)
def get_room_info(token: str, db: Session = Depends(get_db)):
    return handle_get_room_info(token, db)

@router.post("/admin/create_room")
def create_room(
    address: str = Form(...),
    name: str = Form(...),
    tg_group_id: int = Form(...),
    db: Session = Depends(get_db)
):
    return handle_create_room(address, name, tg_group_id, db)

@router.get("/admin/is_authorized/{tg_user_id}")
def is_authorized(
        tg_user_id: int,
        db: Session = Depends(get_db)
):
    return handle_admin_auth(tg_user_id, db)


@router.post("/admin/add_location")
def add_location(address: str = Form(...), db: Session = Depends(get_db)):
    try:
        return handle_add_location(address, db)
    except Exception:
        raise HTTPException(status_code=400, detail="Адрес уже существует")

@router.get("/admin/locations")
def list_locations(
        db: Session = Depends(get_db)
):
    return handle_list_locations(db)

@router.get("/admin/rooms/by_location")
def rooms_by_location(
        address: str = Query(...),
        db: Session = Depends(get_db)
):
    try:
        return handle_rooms_by_location(address, db)
    except Exception:
        raise HTTPException(status_code=404, detail="Адрес не найден")