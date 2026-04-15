import logging
from aiogram import Router
from aiogram.types import InlineQuery
from database import get_user, list_tests
from services.share_service import build_inline_result

logger = logging.getLogger(__name__)
router = Router()


@router.inline_query()
async def inline_query_handler(query: InlineQuery):
    user_id = query.from_user.id
    search = query.query.strip()
    db_user = get_user(user_id)
    lang = db_user.get("language", "ru") if db_user else "ru"
    tests = list_tests(language=lang, status_filter="active", limit=20)
    if search:
        tests = [t for t in tests if search.lower() in t["title"].lower()]
    results = []
    for test in tests[:15]:
        result = build_inline_result(test, lang)
        if result:
            results.append(result)
    await query.answer(results, cache_time=30, is_personal=True)
