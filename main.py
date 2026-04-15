"""
main.py — Точка входа. Инициализация бота, диспетчера, роутеров.
"""

import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from database import init_db

# Handlers
from handlers import common, user, admin, profile, notes, homework
from handlers import daily, duel, rating, quiz, inline, premium, tournament

# Middlewares
from middlewares import RegisterUserMiddleware, BlockedUserMiddleware, AntiSpamMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    # Initialise DB (creates tables if not exists)
    init_db()
    logger.info("Database initialised.")

    # Save bot username to settings for referral links
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    bot_info = await bot.get_me()
    import sqlite3
    from config import DB_PATH
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT OR REPLACE INTO settings(key, value) VALUES('bot_username', ?)",
        (bot_info.username,)
    )
    conn.commit()
    conn.close()
    logger.info(f"Bot: @{bot_info.username}")

    dp = Dispatcher(storage=MemoryStorage())

    # ─── Middlewares (order matters) ───
    # RegisterUserMiddleware runs first — ensures user exists in DB
    dp.message.middleware(RegisterUserMiddleware())
    dp.callback_query.middleware(RegisterUserMiddleware())

    # BlockedUserMiddleware drops all updates from blocked users
    dp.message.middleware(BlockedUserMiddleware())
    dp.callback_query.middleware(BlockedUserMiddleware())

    # AntiSpamMiddleware rate-limits messages and button presses
    dp.message.middleware(AntiSpamMiddleware())
    dp.callback_query.middleware(AntiSpamMiddleware())

    # ─── Routers ───
    # Order: admin first (has IsAdmin filter), then specific handlers, then general
    dp.include_router(admin.router)
    dp.include_router(inline.router)
    dp.include_router(common.router)
    dp.include_router(profile.router)
    dp.include_router(premium.router)
    dp.include_router(notes.router)
    dp.include_router(homework.router)
    dp.include_router(daily.router)
    dp.include_router(duel.router)
    dp.include_router(rating.router)
    dp.include_router(quiz.router)
    dp.include_router(tournament.router)
    dp.include_router(user.router)   # General user handler last (catches remaining callbacks)

    logger.info("Starting bot polling...")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()
        logger.info("Bot stopped.")


if __name__ == "__main__":
    asyncio.run(main())
