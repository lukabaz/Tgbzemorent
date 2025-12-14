from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ContextTypes
from utils.redis_client import redis_client
from utils.logger import logger
from utils.telegram_utils import retry_on_timeout
from utils.translations import translations

LEAD_TTL = int(60 * 60 * 24 * 90)  # 3 месяца

# Сохранение данных пользователя в Redis
def save_lead(chat_id: int, data: dict):
    key = f"lead:{chat_id}"
    redis_client.hset(key, mapping=data)
    redis_client.expire(key, LEAD_TTL)
    logger.info(f"🧲 Lead saved: {key}")

# Получение данных пользователя из Redis
def get_user_data(chat_id: int):
    key = f"lead:{chat_id}"
    return redis_client.hgetall(key)

# Определение языка пользователя
def get_user_language(update: Update, user_data: dict) -> str:
    lang = user_data.get('language', update.effective_user.language_code[:2])
    logger.info(f"Selected language for chat_id={update.effective_chat.id}: {lang}")
    return lang if lang in ['ru', 'en'] else 'en'

# Клавиатура настроек / поддержки
def get_settings_keyboard(lang: str):
    return ReplyKeyboardMarkup([
        [KeyboardButton(translations['settings_button'][lang], web_app={"url": "https://realtorsclientfilters.netlify.app/#"})],
        [KeyboardButton(translations['support_button'][lang], web_app={"url": "https://realtorclientfilters.netlify.app/#/support"})]
    ], resize_keyboard=True)

# =========================
# /start — основной вход
# =========================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_data = get_user_data(chat_id)

    if not user_data:
        save_lead(chat_id, {
            "telegram_id": str(chat_id),
            "language": update.effective_user.language_code[:2],
            "username": update.effective_user.username or "",
            "user_agent": "telegram_bot",
        })
        user_data = get_user_data(chat_id)

    lang = get_user_language(update, user_data)
    welcome_text = translations["welcome"][lang]

    async def send():
        return await context.bot.send_message(
            chat_id=chat_id,
            text=welcome_text,
            reply_markup=get_settings_keyboard(lang)
        )

    await retry_on_timeout(send, chat_id=chat_id, message_text=welcome_text)

# =========================
# Welcome новый пользователь
# =========================
async def welcome_new_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cm = update.my_chat_member
    if cm.chat.type == "private" and cm.new_chat_member.status == "member":
        chat_id = cm.chat.id
        user_data = get_user_data(chat_id)

        if not user_data:
            save_lead(chat_id, {
                "telegram_id": str(chat_id),
                "language": update.effective_user.language_code[:2],
                "username": update.effective_user.username or "",
                "user_agent": "telegram_bot"
            })
            user_data = get_user_data(chat_id)

        lang = get_user_language(update, user_data)
        welcome_text = translations['welcome'][lang]

        async def send_welcome():
            return await context.bot.send_message(
                chat_id=chat_id,
                text=welcome_text,
                reply_markup=get_settings_keyboard(lang)
            )

        await retry_on_timeout(send_welcome, chat_id=chat_id, message_text=welcome_text)

# =========================
# Обработка текстовых кнопок
# =========================
async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = update.message.text
    user_data = get_user_data(chat_id)
    lang = get_user_language(update, user_data)

    # Здесь можно добавить обработку текстовых кнопок
    logger.info(f"👆 Button pressed: {text} by {chat_id}")
    async def send_response():
        return await context.bot.send_message(chat_id=chat_id, text=f"Вы нажали: {text}")
    await retry_on_timeout(send_response, chat_id=chat_id, message_text=text)


