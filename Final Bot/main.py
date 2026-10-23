"""
main.py — entry point. Starts the bot and the background payment checker.
"""
import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config.settings import settings
from database.db import init_db
from middlewares.throttle import ThrottleMiddleware
from services.tron_checker import payment_checker_loop

from handlers import start, catalog, cart, profile, admin

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s: %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


async def main():
    if not settings.bot_token or settings.bot_token == "your_bot_token_here":
        logger.error("❌ BOT_TOKEN is not set!")
        sys.exit(1)

    await init_db()

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    dp = Dispatcher(storage=MemoryStorage())

    dp.message.middleware(ThrottleMiddleware())
    dp.callback_query.middleware(ThrottleMiddleware())

    dp.include_router(admin.router)   # admin FIRST — so /ban /unban commands aren't intercepted by other routers
    dp.include_router(start.router)
    dp.include_router(catalog.router)
    dp.include_router(cart.router)
    dp.include_router(profile.router)

    checker_task = asyncio.create_task(payment_checker_loop(bot=bot))

    logger.info("🚀 Bot started | %s", settings.shop_name)
    logger.info("💳 USDT: %s", settings.usdt_wallet)
    logger.info("👮 Admins: %s", settings.admin_ids)

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        checker_task.cancel()
        try:
            await checker_task
        except asyncio.CancelledError:
            pass
        await bot.session.close()
        logger.info("Bot stopped.")


if __name__ == "__main__":
    asyncio.run(main())
