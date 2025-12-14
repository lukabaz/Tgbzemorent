# authorization/subscription.py
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ContextTypes
from utils.redis_client import redis_client
from utils.logger import logger
from utils.telegram_utils import retry_on_timeout
from utils.translations import translations  # Импортируем переводы

LEAD_TTL = int(60 * 60 * 24 * 90)  # 3 месяца

def save_lead(chat_id: int, data: dict):
    key = f"lead:{chat_id}"
    redis_client.hset(key, mapping=data)
    redis_client.expire(key, LEAD_TTL)
    logger.info(f"🧲 Lead saved: {key}")    

def get_user_data(chat_id: int):
    key = f"lead:{chat_id}"
    return redis_client.hgetall(key)


def get_user_language(update: Update, user_data: dict) -> str:
    # Приоритет: язык из Redis (WebApp) → language_code → английский
    lang = user_data.get('language', update.effective_user.language_code[:2])
    logger.info(f"Selected language for chat_id={update.effective_chat.id}: {lang}")
    return lang if lang in ['ru', 'en'] else 'en'    

def get_settings_keyboard(lang: str):
    return ReplyKeyboardMarkup([
        [KeyboardButton(translations['settings_button'][lang], web_app={"url": "https://realtorsclientfilters.netlify.app/#"})],
        [KeyboardButton(translations['support_button'][lang], web_app={"url": "https://realtorclientfilters.netlify.app/#/support"})] 
    ], resize_keyboard=True)

async def send_status_message(chat_id: int, context: ContextTypes.DEFAULT_TYPE, text: str, lang: str):
    async def send():
        return await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=get_settings_keyboard(lang))
    await retry_on_timeout(send, chat_id=chat_id, message_text=text)
# =========================
# /start — ОСНОВНОЙ ВХОД
# =========================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    user_data = get_user_data(chat_id)

    if not user_data:
        redis_client.hset(
            f"lead:{chat_id}",
            mapping={
                "telegram_id": str(chat_id),
                "language": update.effective_user.language_code[:2],
                "username": update.effective_user.username or "",
                "user_agent": "telegram_bot",
            }
        )
        redis_client.expire(f"lead:{chat_id}", LEAD_TTL)
        logger.info(f"🟢 Created lead key for user {chat_id}")
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

async def welcome_new_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cm = update.my_chat_member
    if cm.chat.type == "private" and cm.new_chat_member.status == "member": # and cm.old_chat_member.status == "kicked" для проверки на повторное вступление чтобы ограничить поток юзеров.
        user_data = get_user_data(cm.chat.id)
        # Если данных нет — создаем ключ в Redis с telegram_id, language, username и user_agent
        if not user_data:
            redis_client.hset(
                f"lead:{cm.chat.id}",
                mapping={
                    "telegram_id": str(cm.chat.id),
                    "language": update.effective_user.language_code[:2],
                    "username": update.effective_user.username or "",
                    "user_agent": "telegram_bot"
                }
            )
            redis_client.expire(f"lead:{cm.chat.id}", LEAD_TTL)
            logger.info(f"🟢 Created lead key for user {cm.chat.id}")

            # После создания, заново читаем данные
            user_data = get_user_data(cm.chat.id)
        lang = get_user_language(update, user_data)
        welcome_text = translations['welcome'][lang]
        async def send_welcome():
             return await context.bot.send_message(chat_id=cm.chat.id, text=welcome_text, reply_markup=get_settings_keyboard(lang))
        await retry_on_timeout(send_welcome, chat_id=cm.chat.id, message_text=welcome_text)



