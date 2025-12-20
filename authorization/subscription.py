# authorization/subscription.py
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ContextTypes
from utils.logger import logger
from utils.telegram_utils import retry_on_timeout
from utils.translations import translations



def get_settings_keyboard(lang: str):
    return ReplyKeyboardMarkup([
        [KeyboardButton(translations['settings_button'][lang], web_app={"url": "https://realtorclientfilters.netlify.app/#/"})],
        [KeyboardButton(translations['support_button'][lang], web_app={"url": "https://realtorclientfilters.netlify.app/#/support"})]
    ], resize_keyboard=True)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Приветственное сообщение и клавиатура для Telegram WebApp.
    Кнопки ведут сразу на фронт с initData.
    """
    chat_id = update.effective_chat.id
    #lang = get_user_language(update, user_data)
    lang = update.effective_user.language_code[:2] if update.effective_user.language_code[:2] in ['ru', 'en'] else 'en'
    welcome_text = translations["welcome"][lang]
    
    keyboard = get_settings_keyboard(lang)

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
    return

