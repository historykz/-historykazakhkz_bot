"""middlewares.py — bot middlewares."""
import time
import logging
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update, Message, CallbackQuery
import database as db
from locales import get_text as t
from config import SPAM_COOLDOWN_SECONDS, BUTTON_COOLDOWN_SECONDS

logger = logging.getLogger(__name__)

# in-memory cooldown store: {user_id: last_action_ts}
_last_action: Dict[int, float] = {}
_last_button: Dict[int, float] = {}


class RegisterUserMiddleware(BaseMiddleware):
    """Auto-register / upsert user on every update."""
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user:
            db.upsert_user(
                tg_id=user.id,
                username=user.username or "",
                full_name=user.full_name or "",
            )
            data["user_lang"] = db.get_user_language(user.id)
        return await handler(event, data)


class BlockedUserMiddleware(BaseMiddleware):
    """Silently stop processing for blocked users."""
    async def __call__(self, handler, event: TelegramObject, data: Dict[str, Any]) -> Any:
        user = data.get("event_from_user")
        if user and db.is_blocked(user.id):
            lang = data.get("user_lang", "ru")
            if isinstance(event, Message):
                await event.answer(t("blocked", lang))
            elif isinstance(event, CallbackQuery):
                await event.answer(t("blocked", lang), show_alert=True)
            return
        return await handler(event, data)


class AntiSpamMiddleware(BaseMiddleware):
    """Rate-limit message spam and button spam separately."""
    async def __call__(self, handler, event: TelegramObject, data: Dict[str, Any]) -> Any:
        user = data.get("event_from_user")
        if not user:
            return await handler(event, data)
        now = time.monotonic()
        lang = data.get("user_lang", "ru")

        if isinstance(event, Message):
            last = _last_action.get(user.id, 0)
            if now - last < SPAM_COOLDOWN_SECONDS:
                # allow /start and /admin to pass through
                text = event.text or ""
                if not text.startswith("/"):
                    await event.answer(t("spam_warning", lang))
                    return
            _last_action[user.id] = now

        elif isinstance(event, CallbackQuery):
            last = _last_button.get(user.id, 0)
            if now - last < BUTTON_COOLDOWN_SECONDS:
                await event.answer(t("spam_warning", lang), show_alert=False)
                return
            _last_button[user.id] = now

        return await handler(event, data)
