from aiohttp import web
import time
import asyncio
import os
import orjson
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, PreCheckoutQueryHandler, ChatMemberHandler, CommandHandler
from exchanges.SubscriptionManager import SymbolSubscriptionManager

from utils.logger import logger
from authorization.subscription import welcome_new_user, handle_buttons, successful_payment, pre_checkout
from authorization.support import handle_support_text
from authorization.webhook import webhook_update
from exchanges.binance import binance_ws
from exchanges.bybit import bybit_ws
from exchanges.okx import okx_ws
from config import WEBHOOK_URL, SUPPORT_CHAT_ID


async def handle(request):
    start_time = time.time()
    json_data = await request.json(loads=orjson.loads)
    update = Update.de_json(json_data, request.app["bot_app"].bot)
    # 👇 Логируем chat ID, если есть
    if update.message:
        chat = update.message.chat
        logger.warning(f"🆔 Incoming message from chat: {chat.id} ({chat.type}) - {chat.title or chat.username}")
    elif update.callback_query:
        chat = update.callback_query.message.chat
        logger.warning(f"🆔 Callback from chat: {chat.id} ({chat.type}) - {chat.title or chat.username}")
    else:
        logger.warning("📥 Received update with no message/chat info")
    await request.app["bot_app"].process_update(update)
    end_time = time.time()
    logger.debug(f"📊 Webhook processing time: {end_time - start_time:.2f} seconds")
    return web.Response(text="OK")

async def home(_: web.Request):
    return web.Response(text="Bot is running")

async def main():
    logger.info("🚀 Telegram bot starting...")
    # Initialize subscription manager
    subscription_manager = SymbolSubscriptionManager()

    # Инициализация приложения Telegram
    app = Application.builder().token(os.getenv("TELEGRAM_TOKEN")).build()
    app.subscription_manager = subscription_manager

    # Регистрируем хендлеры
    app.add_handler(MessageHandler(
        filters.Chat(SUPPORT_CHAT_ID) & filters.TEXT & ~filters.COMMAND,
        handle_support_text
    ))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, webhook_update))
    app.add_handler(ChatMemberHandler(welcome_new_user, ChatMemberHandler.MY_CHAT_MEMBER))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))
    app.add_handler(PreCheckoutQueryHandler(pre_checkout))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_buttons))

    # Устанавливаем вебхук
    await app.bot.set_webhook(ZEMO_WEBHOOK_URL)
    logger.info(f"🌐 Webhook set on {ZEMO_WEBHOOK_URL}")
    
    # aiohttp-приложение
    aio_app = web.Application()
    aio_app["bot_app"] = app
    aio_app.router.add_post(f"/{os.getenv('TELEGRAM_TOKEN')}", handle)
    aio_app.router.add_get("/", home)

    runner = web.AppRunner(aio_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", int(os.getenv("PORT", 4012)))
    await site.start()

    logger.info(f"🚀 Bot running on port: {os.getenv('PORT', 4012)}")

    # Инициализация и запуск Telegram-приложения
    await app.initialize()
    await app.start()
    await asyncio.Event().wait()  # Задержка, чтобы бот не завершался

if __name__ == "__main__":
    asyncio.run(main())