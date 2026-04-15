"""filters.py — custom aiogram filters."""
from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery
import database as db


class IsAdmin(BaseFilter):
    """True if the sender is in ADMIN_IDS or admins table."""
    async def __call__(self, event) -> bool:
        uid = None
        if isinstance(event, Message):
            uid = event.from_user.id if event.from_user else None
        elif isinstance(event, CallbackQuery):
            uid = event.from_user.id if event.from_user else None
        if uid is None:
            return False
        return db.is_admin(uid)


class HasLanguage(BaseFilter):
    """True if user already has a language set (not first start)."""
    async def __call__(self, event: Message) -> bool:
        uid = event.from_user.id if event.from_user else None
        if not uid:
            return False
        user = db.get_user(uid)
        return user is not None and user["language"] in ("ru", "kz")
