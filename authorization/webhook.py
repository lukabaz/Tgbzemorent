# authorization/webhook
import orjson
from telegram import Update
from telegram.ext import ContextTypes
from config import SUPPORT_CHAT_ID
from utils.logger import logger
from utils.redis_client import redis_client
from utils.telegram_utils import retry_on_timeout
from utils.translations import translations

INACTIVITY_TTL = int(1.2 * 30 * 24 * 60 * 60)  # 1.2 месяца

def safe_int(value, default=0):
    try:
        return int(str(value).replace(" ", ""))
    except (ValueError, TypeError):
        return default

async def webhook_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.web_app_data:
        return

    user_id = update.effective_user.id
    try:
        payload = orjson.loads(update.message.web_app_data.data)
        logger.debug(f"📩 Received Web App data for user_id={user_id}: {payload}")

        user_data = redis_client.hgetall(f"zemo:{user_id}")
        lang = user_data.get("language", update.effective_user.language_code[:2])
        lang = lang if lang in ['ru', 'en'] else 'en'

        data_type = payload.get("type")

        if data_type == "support":
            message = (payload.get("message") or "").strip()
            if not message:
                error_text = translations['support_empty'][lang]
                async def send_error():
                    return await context.bot.send_message(chat_id=user_id, text=error_text)
                await retry_on_timeout(send_error)
                return

            forward_text = (
                f"📨 Новый вопрос от пользователя {update.effective_user.first_name or ''} "
                f"(@{update.effective_user.username or 'нет'})\n"
                f"ID пользователя: {user_id}\n\n{message}"
            )
            async def send_to_support():
                return await context.bot.send_message(SUPPORT_CHAT_ID, forward_text)
            await retry_on_timeout(send_to_support)

            response_text = translations['support_sent'][lang]
            async def send_confirmation():
                return await context.bot.send_message(chat_id=user_id, text=response_text)
            await retry_on_timeout(send_confirmation)

    except Exception as e:
        logger.error(f"❌ Error processing Web App data for user_id={user_id}: {e}", exc_info=True)
        error_text = translations['processing_error'][lang]
        async def send_error():
            return await context.bot.send_message(chat_id=user_id, text=error_text)
        await retry_on_timeout(send_error)