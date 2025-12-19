# authorization/subscription.py
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ContextTypes
from utils.logger import logger
from utils.telegram_utils import retry_on_timeout
from utils.translations import translations
import urllib.parse
import orjson

def build_webapp_url(base_url: str, tg_user: dict) -> str:
    """
    Формирует URL фронтенда с initData для Telegram WebApp.
    """
    params = {"user": orjson.dumps(tg_user).decode("utf-8")}
    return f"{base_url}?{urllib.parse.urlencode(params)}"

def get_settings_keyboard(lang: str, tg_user: dict):
    base_url = "https://realtorclientfilters.netlify.app/#/"
    webapp_url_main = build_webapp_url(base_url, tg_user)
    webapp_url_support = build_webapp_url(base_url + "support", tg_user)

    return ReplyKeyboardMarkup([
        [KeyboardButton(translations['settings_button'][lang], web_app={"url": webapp_url_main})],
        [KeyboardButton(translations['support_button'][lang], web_app={"url": webapp_url_support})]
    ], resize_keyboard=True)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Приветственное сообщение и клавиатура для Telegram WebApp.
    Кнопки ведут сразу на фронт с initData.
    """
    chat_id = update.effective_chat.id

    tg_user = {
        "id": update.effective_user.id,
        "username": update.effective_user.username or None,
        "first_name": update.effective_user.first_name or "",
        "last_name": update.effective_user.last_name or "",
        "photo_url": None  # ← Временно None, фото из WebApp initData
    }

    lang = update.effective_user.language_code[:2] if update.effective_user.language_code[:2] in ['ru', 'en'] else 'en'
    welcome_text = translations["welcome"][lang]

    keyboard = get_settings_keyboard(lang, tg_user)

    async def send():
        return await context.bot.send_message(
            chat_id=chat_id,
            text=welcome_text,
            reply_markup=keyboard
        )

    await retry_on_timeout(send, chat_id=chat_id, message_text=welcome_text)
    logger.info(f"👋 Sent welcome message and WebApp keyboard to chat_id={chat_id}")

async def welcome_new_user(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """
    Новый пользователь через my_chat_member.
    """
    cm = update.my_chat_member
    if cm.chat.type != "private" or cm.new_chat_member.status != "member":
        return
    logger.info(f"👤 User allowed the bot: chat_id={cm.chat.id}")

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Минимальные изменения — все кнопки ведут на WebApp, действия на фронте.
    """
    chat_id = update.effective_chat.id
    text = update.message.text

    tg_user = {
        "id": update.effective_user.id,
        "username": update.effective_user.username or None,
        "first_name": update.effective_user.first_name or "",
        "last_name": update.effective_user.last_name or "",
        "photo_url": update.effective_user.photo_url or None
    }

    lang = update.effective_user.language_code[:2] if update.effective_user.language_code[:2] in ['ru', 'en'] else 'en'

    if text in [translations['settings_button'][lang], translations['support_button'][lang]]:
        base_url = "https://realtorclientfilters.netlify.app/#/"
        if text == translations['support_button'][lang]:
            base_url += "support"

        webapp_url = build_webapp_url(base_url, tg_user)

        async def send():
            return await context.bot.send_message(
                chat_id=chat_id,
                text="Открываем WebApp...",
                reply_markup=ReplyKeyboardMarkup(
                    [[KeyboardButton(text, web_app={"url": webapp_url})]],
                    resize_keyboard=True
                )
            )
        await retry_on_timeout(send, chat_id=chat_id)
        logger.info(f"🔗 Sent WebApp link for chat_id={chat_id}, button={text}")



