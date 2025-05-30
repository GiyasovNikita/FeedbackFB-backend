from fastapi import APIRouter, Depends, Form, HTTPException, Query

from src.app.modules.messages.application.schemas import Feedback, RoomInfo
from src.app.modules.messages.infrastructure.db.repos import (
    get_room_repo,
    get_location_repo,
    get_message_repo,
    get_admin_repo,
    RoomRepo,
    LocationRepo,
    MessageRepo,
    AdminRepo
)
from src.app.modules.messages.application.services.feedback_service import (
    handle_send_feedback,
    handle_get_room_info,
    handle_create_room,
    handle_admin_auth,
    handle_add_location, handle_list_locations, handle_rooms_by_location
)


router = APIRouter(prefix="/feedback", tags=["Feedback"])

@router.post("/{token}")
def send_feedback(
    token: str,
    feedback: Feedback,
    room_repo: RoomRepo = Depends(get_room_repo),
    message_repo: MessageRepo = Depends(get_message_repo)
):
    return handle_send_feedback(token, feedback, room_repo, message_repo)


@router.get("/room/{token}", response_model=RoomInfo)
def get_room_info(
    token: str,
    room_repo: RoomRepo = Depends(get_room_repo)
):
    return handle_get_room_info(token, room_repo)


@router.post("/admin/create_room")
def create_room(
    address: str = Form(...),
    name: str = Form(...),
    tg_group_id: int = Form(...),
    location_repo: LocationRepo = Depends(get_location_repo),
    room_repo: RoomRepo = Depends(get_room_repo)
):
    return handle_create_room(address, name, tg_group_id, location_repo, room_repo)


@router.get("/admin/is_authorized/{tg_user_id}")
def is_authorized(
    tg_user_id: str,
    admin_repo: AdminRepo = Depends(get_admin_repo)
):
    return handle_admin_auth(tg_user_id, admin_repo)

@router.post("/admin/add_location")
def add_location(
    address: str = Form(...),
    location_repo: LocationRepo = Depends(get_location_repo)
):
    try:
        return handle_add_location(address, location_repo)
    except Exception:
        raise HTTPException(status_code=400, detail="Адрес уже существует")

@router.get("/admin/locations")
def list_locations(
    location_repo: LocationRepo = Depends(get_location_repo)
):
    return handle_list_locations(location_repo)

@router.get("/admin/rooms/by_location")
def rooms_by_location(
    address: str = Query(...),
    location_repo: LocationRepo = Depends(get_location_repo)
):
    try:
        return handle_rooms_by_location(address, location_repo)
    except Exception:
        raise HTTPException(status_code=404, detail="Адрес не найден")
