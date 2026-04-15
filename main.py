import asyncio
import logging
import sqlite3
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import PollAnswer
from config import BOT_TOKEN
from database import init_db
from handlers import common, user, admin, profile, notes, homework
from handlers import daily, duel, rating, quiz, inline, premium, tournament
from middlewares import RegisterUserMiddleware, BlockedUserMiddleware, AntiSpamMiddleware

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


async def main():
    init_db()
    logger.info("Database initialised.")
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    bot_info = await bot.get_me()
    conn = sqlite3.connect("ent_bot.db")
    conn.execute("INSERT OR REPLACE INTO settings(key, value) VALUES('bot_username', ?)", (bot_info.username,))
    conn.commit()
    conn.close()
    logger.info(f"Bot: @{bot_info.username}")
    dp = Dispatcher(storage=MemoryStorage())

    dp.message.middleware(RegisterUserMiddleware())
    dp.callback_query.middleware(RegisterUserMiddleware())
    dp.message.middleware(BlockedUserMiddleware())
    dp.callback_query.middleware(BlockedUserMiddleware())
    dp.message.middleware(AntiSpamMiddleware())
    dp.callback_query.middleware(AntiSpamMiddleware())

    @dp.poll_answer()
    async def on_poll_answer(poll_answer: PollAnswer):
        from services.test_runner import handle_poll_answer
        try:
            option_id = poll_answer.option_ids[0] if poll_answer.option_ids else 0
            await handle_poll_answer(
                bot=bot,
                poll_id=poll_answer.poll_id,
                user_id=poll_answer.user.id,
                option_id=option_id,
                chat_id=poll_answer.user.id,
            )
        except Exception as e:
            logger.error("poll_answer error: %s", e)

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
    dp.include_router(user.router)

    logger.info("Starting bot polling...")
    try:
        await dp.start_polling(
            bot,
            allowed_updates=["message", "callback_query", "poll_answer", "inline_query"]
        )
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
