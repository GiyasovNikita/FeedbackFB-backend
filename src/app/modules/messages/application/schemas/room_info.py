from pydantic import BaseModel

class RoomInfo(BaseModel):
    address: str
    name: str