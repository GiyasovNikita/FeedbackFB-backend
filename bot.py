import asyncio
import logging
import requests
from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart, Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, BufferedInputFile
from io import BytesIO
import qrcode
from dotenv import load_dotenv
import os

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_BASE = os.getenv("API_BASE")
FORM_URL = os.getenv("FORM_URL")

if not BOT_TOKEN or not API_BASE:
    raise ValueError("Не заданы переменные окружения BOT_TOKEN или API_BASE")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

logging.basicConfig(level=logging.INFO)

# FSM-состояния
class CreateState(StatesGroup):
    choosing_action = State()
    adding_address = State()
    choosing_address = State()
    entering_room_name = State()
    entering_group_id = State()

class RoomQueryState(StatesGroup):
    choosing_location = State()

# Проверка прав администратора
async def is_admin(user_id: int) -> bool:
    try:
        r = requests.get(f"{API_BASE}/admin/is_authorized/{user_id}")
        return r.json().get("authorized", False)
    except Exception:
        return False

@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "👋 Привет! Я бот для управления помещениями и обратной связью.\n\n"
        "📌 Доступные команды:\n"
        "/create — создать адрес или помещение\n"
        "/rooms — список комнат по адресам\n"
        "/qr <token> — получить ссылку на форму по токену\n\n"
    )


@dp.message(Command("create"))
async def cmd_create(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return await message.answer("У вас нет доступа.")
    buttons = [[KeyboardButton(text="Адрес")], [KeyboardButton(text="Комната")]]
    markup = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
    await message.answer("Что вы хотите создать?", reply_markup=markup)
    await state.set_state(CreateState.choosing_action)

@dp.message(CreateState.choosing_action)
async def choose_action(message: Message, state: FSMContext):
    text = message.text.lower()
    if text == "адрес":
        await state.set_state(CreateState.adding_address)
        await message.answer("Введите новый адрес:", reply_markup=ReplyKeyboardRemove())
    elif text == "комната":
        try:
            r = requests.get(f"{API_BASE}/admin/locations")
            locations = r.json()
            if not locations:
                return await message.answer("Нет доступных адресов. Сначала добавьте адрес.", reply_markup=ReplyKeyboardRemove())
            buttons = [[KeyboardButton(text=addr)] for addr in locations]
            markup = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
            await state.set_state(CreateState.choosing_address)
            await message.answer("Выберите адрес:", reply_markup=markup)
        except Exception as e:
            await message.answer(f"Ошибка: {e}")
    else:
        await message.answer("Пожалуйста, выберите: Адрес или Комната")

@dp.message(CreateState.adding_address)
async def add_address(message: Message, state: FSMContext):
    address = message.text
    try:
        r = requests.post(f"{API_BASE}/admin/add_location", data={"address": address})
        if r.status_code == 200:
            await message.answer("✅ Адрес успешно добавлен!", reply_markup=ReplyKeyboardRemove())
        else:
            await message.answer("Ошибка при добавлении адреса.", reply_markup=ReplyKeyboardRemove())
    except Exception as e:
        await message.answer(f"Ошибка: {e}", reply_markup=ReplyKeyboardRemove())
    await state.clear()

@dp.message(CreateState.choosing_address)
async def choose_address(message: Message, state: FSMContext):
    await state.update_data(address=message.text)
    await state.set_state(CreateState.entering_room_name)
    await message.answer("Введите название комнаты:", reply_markup=ReplyKeyboardRemove())

@dp.message(CreateState.entering_room_name)
async def enter_room_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(CreateState.entering_group_id)
    await message.answer("Введите Telegram Group ID:")

@dp.message(CreateState.entering_group_id)
async def enter_group_id(message: Message, state: FSMContext):
    await state.update_data(tg_group_id=message.text)
    data = await state.get_data()
    try:
        r = requests.post(f"{API_BASE}/admin/create_room", data={
            "address": data["address"],
            "name": data["name"],
            "tg_group_id": int(data["tg_group_id"])
        })
        result = r.json()
        await message.answer(f"✅ Комната создана!\n🏢 Адрес: {data['address']}\n📌 Название: {data['name']}\n🔗 QR: {result['qr_link']}")
    except Exception as e:
        await message.answer(f"Ошибка: {e}")
    await state.clear()

@dp.message(Command("rooms"))
async def cmd_rooms(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return await message.answer("У вас нет доступа.")
    try:
        r = requests.get(f"{API_BASE}/admin/locations")
        addresses = r.json()
        if not addresses:
            return await message.answer("Нет адресов в системе.")
        buttons = [[KeyboardButton(text=addr)] for addr in addresses]
        markup = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
        await state.set_state(RoomQueryState.choosing_location)
        await message.answer("Выберите адрес:", reply_markup=markup)
    except Exception as e:
        await message.answer(f"Ошибка: {e}")

@dp.message(RoomQueryState.choosing_location)
async def show_rooms(message: Message, state: FSMContext):
    address = message.text
    try:
        r = requests.get(f"{API_BASE}/admin/rooms/by_location", params={"address": address})
        rooms = r.json()
        if not rooms:
            await message.answer("По этому адресу нет комнат.", reply_markup=ReplyKeyboardRemove())
        else:
            text = f"🏢 {address}\n"
            for room in rooms:
                text += f"• {room['name']} — token: `{room['qr_token']}`\n"
            await message.answer(text, parse_mode="Markdown", reply_markup=ReplyKeyboardRemove())
    except Exception as e:
        await message.answer(f"Ошибка: {e}", reply_markup=ReplyKeyboardRemove())
    await state.clear()

@dp.message(Command("qr"))
async def cmd_qr(message: Message):
    if not await is_admin(message.from_user.id):
        return await message.answer("У вас нет доступа.")

    args = message.text.split()
    if len(args) != 2:
        return await message.answer("Используйте: /qr <token>")
    token = args[1]

    try:
        r = requests.get(f"{API_BASE}/room/{token}")
        if r.status_code == 404:
            return await message.answer("Токен не найден.")

        room = r.json()
        link = f"{FORM_URL}/feedback/{token}"

        # Генерация QR
        qr = qrcode.make(link)
        buf = BytesIO()
        qr.save(buf, format="PNG")
        buf.seek(0)

        photo = BufferedInputFile(buf.getvalue(), filename="qr.png")

        caption = (
            f"🏠 <b>{room['name']}</b>\n"
            f"📍 {room['address']}\n"
            f"🔗 <a href=\"{link}\">Открыть форму</a>"
        )

        await bot.send_photo(
            chat_id=message.chat.id,
            photo=photo,
            caption=caption,
            parse_mode="HTML"
        )

    except Exception as e:
        await message.answer(f"Ошибка: {e}")


async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
