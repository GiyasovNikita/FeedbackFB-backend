import asyncio
import logging
import requests
from functools import wraps
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


async def is_admin(user_id: int) -> bool:
    try:
        r = requests.get(f"{API_BASE}/admin/is_authorized/{user_id}")
        r.raise_for_status()
        data = r.json()
        return data.get("authorized", False)
    except requests.exceptions.RequestException:
        return None


def admin_required(handler):
    @wraps(handler)
    async def wrapper(message: Message, *args, **kwargs):
        is_user_admin = await is_admin(message.from_user.id)
        if is_user_admin is None:
            await message.answer("⚠️ Сервер временно недоступен. Попробуйте позже.")
            return
        if not is_user_admin:
            await message.answer("У вас нет доступа.")
            return
        return await handler(message, *args, **kwargs)

    return wrapper

def make_qr_bytes(link: str) -> BytesIO:
    qr = qrcode.make(link)
    buf = BytesIO()
    qr.save(buf, format="PNG")
    buf.seek(0)
    return buf

@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "👋 Привет! Я бот для управления помещениями и обратной связью.\n\n"
        "📌 Доступные команды:\n"
        "/create — создать адрес или помещение\n"
        "/rooms — список комнат по адресам\n"
        "/qr <token> — получить ссылку на форму по токену\n"
        "/cancel — отменить текущее действие\n"
        "/help — полная инструкция по использованию\n"
        "/getgroupid — узнать Telegram group id\n"
    )

@dp.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Действие отменено.", reply_markup=ReplyKeyboardRemove())

@dp.message(Command("create"))
@admin_required
async def cmd_create(message: Message, state: FSMContext):
    buttons = [[KeyboardButton(text="Адрес")], [KeyboardButton(text="Помещение")]]
    markup = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
    await message.answer("Что вы хотите создать?", reply_markup=markup)
    await state.set_state(CreateState.choosing_action)

@dp.message(CreateState.choosing_action)
@admin_required
async def choose_action(message: Message, state: FSMContext):
    text = message.text.lower()
    if text == "адрес":
        await state.set_state(CreateState.adding_address)
        await message.answer("Введите новый адрес:", reply_markup=ReplyKeyboardRemove())
    elif text == "помещение":
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
        await message.answer("Пожалуйста, выберите: Адрес или Помещение")

@dp.message(CreateState.adding_address)
@admin_required
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
@admin_required
async def choose_address(message: Message, state: FSMContext):
    await state.update_data(address=message.text)
    await state.set_state(CreateState.entering_room_name)
    await message.answer("Введите название помещения:", reply_markup=ReplyKeyboardRemove())

@dp.message(CreateState.entering_room_name)
@admin_required
async def enter_room_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(CreateState.entering_group_id)
    await message.answer("Введите Telegram Group ID:")

@dp.message(CreateState.entering_group_id)
@admin_required
async def enter_group_id(message: Message, state: FSMContext):
    group_id_input = message.text.strip()

    if group_id_input.startswith('-'):
        group_id = group_id_input
    else:
        group_id = f'-{group_id_input}'

    if not group_id.lstrip('-').isdigit():
        await message.answer("ID группы должен быть числом (или начинаться с минуса)!")
        return

    await state.update_data(tg_group_id=group_id)
    data = await state.get_data()
    try:
        r = requests.post(f"{API_BASE}/admin/create_room", data={
            "address": data["address"],
            "name": data["name"],
            "tg_group_id": int(group_id)
        })
        result = r.json()
        link = result['qr_link']
        qr_buf = make_qr_bytes(link)
        photo = BufferedInputFile(qr_buf.getvalue(), filename="qr.png")
        caption = (
            f"✅ Помещение создано!\n"
            f"📍 Адрес: {data['address']}\n"
            f"📌 Название: {data['name']}\n"
            f"🔗 <a href=\"{link}\">Открыть форму</a>"
        )
        await message.answer_photo(
            photo=photo,
            caption=caption,
            parse_mode="HTML",
            reply_markup=ReplyKeyboardRemove()
        )
    except Exception as e:
        await message.answer(f"Ошибка: {e}")
    await state.clear()

@dp.message(Command("rooms"))
@admin_required
async def cmd_rooms(message: Message, state: FSMContext):
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
@admin_required
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
@admin_required
async def cmd_qr(message: Message):
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

        qr_buf = make_qr_bytes(link)
        photo = BufferedInputFile(qr_buf.getvalue(), filename="qr.png")

        caption = (
            f"📌 <b>{room['name']}</b>\n"
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

@dp.message(Command("getgroupid"))
async def cmd_getgroupid(message: Message):
    if message.chat.type in ("group", "supergroup"):
        await message.answer(
            f"ID этой группы: <code>{message.chat.id}</code>\n"
            "Скопируйте этот номер и используйте его при создании комнаты в системе.\n"
            "⚠️ Для супергрупп id всегда начинается с минуса.",
            parse_mode="HTML"
        )
    else:
        await message.answer(
            "Эта команда работает только в группах.\n"
            "Добавьте бота в нужную группу и отправьте команду там, чтобы узнать её id."
        )


@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "<b>Полная инструкция по использованию бота</b> 🤖\n\n"
        "<b>1. Для чего этот бот?</b>\n"
        "Бот позволяет создавать адреса и помещения, генерировать QR-коды для обратной связи, а также управлять этими объектами через Telegram.\n\n"
        "<b>2. Основные команды:</b>\n"
        "• /start — краткая справка о возможностях бота\n"
        "• /help — полная инструкция по использованию\n"
        "• /create — создать новый адрес или помещение (требуется доступ администратора)\n"
        "• /rooms — получить список всех комнат по выбранному адресу (админ)\n"
        "• /qr &lt;token&gt; — получить QR-код и ссылку на форму обратной связи по токену комнаты (админ)\n"
        "• /getgroupid — узнать Telegram group id\n"
        "• /cancel — отменить текущее действие и сбросить состояние бота\n\n"
        "<b>3. Как создать новый адрес?</b>\n"
        "• Введите команду /create\n"
        "• Выберите «Адрес» и введите новый адрес текстом.\n"
        "• Если всё успешно — адрес появится в списке доступных для выбора при создании помещения.\n\n"
        "<b>4. Как создать новое помещение?</b>\n"
        "• Введите команду /create\n"
        "• Выберите «Помещение»\n"
        "• Выберите адрес из списка\n"
        "• Введите название комнаты\n"
        "• Введите Telegram group id (с минусом, например -123456789; бот автоматически добавит минус, если вы его не указали)\n"
        "• После успешного создания вы получите QR-код и ссылку на форму обратной связи для этой комнаты.\n\n"
        "<b>5. Как узнать Telegram group id?</b>\n"
        "• Добавьте этого бота в нужную группу Telegram\n"
        "• Введите команду /getgroupid или отправьте любое сообщение в группе — бот пришлёт вам id. Либо воспользуйтесь сторонним ботом, например @userinfobot.\n\n"
        "<b>6. Как получить QR-код и ссылку повторно?</b>\n"
        "• Используйте команду /qr &lt;token&gt;, где &lt;token&gt; — уникальный код комнаты, который вы можете узнать из команды /rooms.\n"
        "• Бот отправит вам QR-картинку и ссылку на форму.\n\n"
        "<b>7. Как посмотреть все комнаты по адресу?</b>\n"
        "• Используйте команду /rooms\n"
        "• Выберите нужный адрес из списка\n"
        "• Бот пришлёт список комнат с их названиями и токенами.\n\n"
        "<b>8. Как отменить действие?</b>\n"
        "• В любой момент введите /cancel — текущее состояние сбросится, клавиатура пропадёт.\n\n"
        "<b>9. Прочее</b>\n"
        "• Если бот пишет «У вас нет доступа», значит вы не являетесь администратором.\n"
        "• Для получения доступа обратитесь к ответственному администратору или поддержке.\n"
        "• Если возникла ошибка или бот не отвечает — попробуйте /cancel, /start, или свяжитесь с поддержкой.\n"
        "\n<b>Спасибо за использование бота!</b>"
        , parse_mode="HTML"
    )

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
