#  config.py
import os
# from dotenv import load_dotenv
# load_dotenv()
SUPPORT_CHAT_ID = -1002977168139
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
REDIS_URL = os.getenv("REDIS_URL")
ZEMO_WEBHOOK_URL = f"https://{os.getenv('VERCEL_URL', 'localhost:3001')}/{TELEGRAM_TOKEN}"  # Vercel auto VERCEL_URL, fallback for local
PORT = int(os.getenv("PORT", 3001))  # Vercel PORT auto
MONGO_URI = os.getenv("MONGO_URI")

if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN not found")
if not REDIS_URL:
    raise ValueError("REDIS_URL not found")
if not MONGO_URI:
    raise ValueError("MONGO_URI не найден в переменных окружения")



