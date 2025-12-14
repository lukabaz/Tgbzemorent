import os
import asyncio
from fastapi import FastAPI, Request, HTTPException
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, ChatMemberHandler, filters
import orjson
from authorization.subscription import welcome_new_user, start_command, handle_buttons
from authorization.webhook import webhook_update
from authorization.support import handle_support_text
from utils.logger import logger
from config import TELEGRAM_TOKEN, SUPPORT_CHAT_ID

#app = FastAPI(docs_url="docs", redoc_url=None, openapi_url=None)
app = FastAPI()

async def build_application():
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    await application.initialize()

    # Хендлер поддержки
    application.add_handler(MessageHandler(
        filters.Chat(SUPPORT_CHAT_ID) & filters.TEXT & ~filters.COMMAND,
        handle_support_text
    ))

    # WebApp данные
    application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, webhook_update))

    # Новый пользователь
    application.add_handler(ChatMemberHandler(welcome_new_user, ChatMemberHandler.MY_CHAT_MEMBER))

    # /start
    application.add_handler(CommandHandler("start", start_command))

    # Текстовые кнопки
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_buttons))

    return application

@app.post("/telegram-webhook")
async def telegram_webhook(request: Request):
    try:
        body = await request.body()
        update_json = orjson.loads(body)

        application = await build_application()
        update = Update.de_json(update_json, application.bot)

        logger.info(f"📩 Incoming update: {orjson.dumps(update_json).decode('utf-8')}")
        await application.process_update(update)

        # Shutdown без задержки, Serverless
        async def shutdown_later(app, delay: float = 0.0):
            if delay > 0:
                await asyncio.sleep(delay)
            await app.shutdown()

        is_new_user = getattr(update, "my_chat_member", None) and update.my_chat_member.new_chat_member.status in ["member", "administrator"]
        asyncio.create_task(shutdown_later(application, delay=5.0 if is_new_user else 2.0))

        return {"ok": True}

    except Exception as e:
        logger.exception(f"Telegram webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 3001)))