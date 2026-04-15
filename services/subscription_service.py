import logging
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
import database as db

logger = logging.getLogger(__name__)
SUBSCRIBED_STATUSES = {"member", "administrator", "creator"}


async def check_subscription(bot: Bot, user_id: int, channel_username: str) -> bool:
    try:
        member = await bot.get_chat_member(
            chat_id=f"@{channel_username.lstrip('@')}",
            user_id=user_id,
        )
        return member.status in SUBSCRIBED_STATUSES
    except TelegramBadRequest as e:
        logger.warning("check_subscription error for %s: %s", channel_username, e)
        return False
    except Exception as e:
        logger.error("Unexpected error: %s", e)
        return False


async def check_all_channels(bot: Bot, user_id: int, test_id: int) -> list:
    channels = db.get_test_channels(test_id)
    not_subscribed = []
    for ch in channels:
        ok = await check_subscription(bot, user_id, ch["channel_username"])
        if not ok:
            not_subscribed.append(ch["channel_username"])
    return not_subscribed
