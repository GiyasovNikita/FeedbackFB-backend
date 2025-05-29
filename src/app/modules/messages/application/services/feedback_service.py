from sqlalchemy.orm import Session
from io import BytesIO
import base64
import qrcode
import uuid

from src.app.modules.messages.infrastructure.db.models import Room, Location, Message, Admin
from src.app.modules.messages.application.schemas import Feedback, RoomInfo
from src.utils import send_telegram_message


def handle_send_feedback(token: str, feedback: Feedback, db: Session):
    room = db.query(Room).filter(Room.qr_token == token).first()
    if not room:
        raise ValueError("Room not found")

    message = Message(room_id=room.id, text=feedback.text)
    db.add(message)
    db.commit()

    tg_msg = (
        f"\U0001F6A8 Новое сообщение!\n"
        f"\U0001F4CD Адрес: {room.location.address}\n"
        f"\U0001F3E0 Помещение: {room.name}\n"
        f"\u2709\uFE0F Сообщение: {feedback.text}"
    )
    send_telegram_message(room.tg_group_id, tg_msg)

    return {"status": "ok"}


def handle_get_room_info(token: str, db: Session) -> RoomInfo:
    room = db.query(Room).filter(Room.qr_token == token).first()
    if not room:
        raise ValueError("Room not found")
    return RoomInfo(address=room.location.address, name=room.name)


def handle_create_room(address: str, name: str, tg_group_id: int, db: Session):
    location = db.query(Location).filter(Location.address == address).first()
    if not location:
        location = Location(address=address)
        db.add(location)
        db.commit()
        db.refresh(location)

    token = str(uuid.uuid4())[:8]
    room = Room(location_id=location.id, name=name, tg_group_id=tg_group_id, qr_token=token)
    db.add(room)
    db.commit()

    qr_link = f"https://yourdomain.com/feedback?token={token}"
    img = qrcode.make(qr_link)
    buf = BytesIO()
    img.save(buf, format='PNG')
    encoded_img = base64.b64encode(buf.getvalue()).decode("utf-8")

    return {
        "qr_token": token,
        "qr_link": qr_link,
        "qr_image_base64": encoded_img,
    }

def handle_admin_auth(tg_user_id: str, db: Session):
    admin = db.query(Admin).filter(Admin.username == str(tg_user_id)).first()
    return {"authorized": bool(admin)}


def handle_add_location(address: str, db: Session):
    if db.query(Location).filter(Location.address == address).first():
        raise Exception
    location = Location(address=address)
    db.add(location)
    db.commit()
    return {"status": "ok"}

def handle_list_locations(db: Session):
    return [l.address for l in db.query(Location).all()]

def handle_rooms_by_location(address: str, db: Session):
    location = db.query(Location).filter(Location.address == address).first()
    if not location:
        raise Exception
    return [{"name": r.name, "qr_token": r.qr_token} for r in location.rooms]