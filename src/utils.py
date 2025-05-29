import requests
from dotenv import load_dotenv
import os

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

def send_telegram_message(chat_id: int, message: str):
    data = {
        "chat_id": chat_id,
        "text": message
    }
    try:
        response = requests.post(TELEGRAM_API_URL, data=data)
        response.raise_for_status()
    except requests.RequestException as e:
        print("Telegram error:", e)
