import uuid
import os
from dotenv import load_dotenv

from src.app.modules.messages.application.schemas import Feedback, RoomInfo
from src.app.modules.messages.infrastructure.db.repos import (
    RoomRepo,
    LocationRepo,
    MessageRepo,
    AdminRepo
)
from src.utils import send_telegram_message


load_dotenv()

FORM_URL = os.getenv("FORM_URL")

def handle_send_feedback(token: str, feedback: Feedback, room_repo: RoomRepo, message_repo: MessageRepo):
    room = room_repo.get_by_token(token)
    if not room:
        raise ValueError("Room not found")

    _ = message_repo.create(room_id=room.id, text=feedback.text)

    tg_msg = (
        f"\U0001F6A8 Новое сообщение!\n"
        f"\U0001F4CD Адрес: {room.location.address}\n"
        f"\U0001F3E0 Помещение: {room.name}\n"
        f"\u2709\uFE0F Сообщение: {feedback.text}"
    )
    send_telegram_message(room.tg_group_id, tg_msg)

    return {"status": "ok"}


def handle_get_room_info(token: str, room_repo: RoomRepo) -> RoomInfo:
    room = room_repo.get_by_token(token)
    if not room:
        raise ValueError("Room not found")
    return RoomInfo(address=room.location.address, name=room.name)


def handle_create_room(address: str, name: str, tg_group_id: int, location_repo: LocationRepo, room_repo: RoomRepo):
    location = location_repo.get_by_address(address)
    if not location:
        location = location_repo.create(address)

    token = uuid.uuid4().hex[:8]
    room = room_repo.create(location_id=location.id, name=name, tg_group_id=tg_group_id, token=token)
    qr_link = f"{FORM_URL}/room/{token}"
    return {
        "qr_token": token,
        "qr_link": qr_link,
    }


def handle_admin_auth(tg_user_id: str, admin_repo: AdminRepo):
    admin = admin_repo.is_admin(tg_user_id)
    return {"authorized": bool(admin)}


def handle_add_location(address: str, location_repo: LocationRepo):
    if location_repo.get_by_address(address):
        raise Exception
    location_repo.create(address)
    return {"status": "ok"}


def handle_list_locations(location_repo: LocationRepo):
    return [l.address for l in location_repo.list()]


def handle_rooms_by_location(address: str, location_repo: LocationRepo):
    location = location_repo.get_by_address(address)
    if not location:
        raise Exception
    return [{"name": r.name, "qr_token": r.qr_token} for r in location.rooms]
