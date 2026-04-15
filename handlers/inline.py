import logging
from aiogram import Router
from aiogram.types import (
    InlineQuery, InlineQueryResultArticle,
    InputTextMessageContent, InlineKeyboardMarkup, InlineKeyboardButton
)
from database import get_user, list_tests, get_test, count_questions

logger = logging.getLogger(__name__)
router = Router()


@router.inline_query()
async def inline_query_handler(query: InlineQuery):
    user_id = query.from_user.id
    search = query.query.strip()
    db_user = get_user(user_id)
    lang = db_user.get("language", "ru") if db_user else "ru"

    # Если запрос начинается с test_ — показываем конкретный тест
    if search.startswith("test_"):
        test_id_str = search.replace("test_", "")
        if test_id_str.isdigit():
            test = get_test(int(test_id_str))
            if test:
                results = [_build_test_result(test, lang)]
                await query.answer(results, cache_time=10, is_personal=True)
                return

    # Иначе показываем список тестов
    tests = list_tests(language=lang, status_filter="active", limit=20)
    if search:
        tests = [t for t in tests if search.lower() in t["title"].lower()]

    results = [_build_test_result(t, lang) for t in tests[:15]]
    await query.answer(results or [], cache_time=30, is_personal=True)


def _build_test_result(test, lang: str):
    test_id = test["id"]
    title = test.get("title", "")
    q_count = test.get("question_count") or "?"
    time_per_q = test.get("time_per_question", 30)
    test_type = test.get("test_type", "regular")

    if lang == "ru":
        text = (
            f"📚 <b>{title}</b>\n\n"
            f"❓ Вопросов: {q_count}\n"
            f"⏱ {time_per_q} сек/вопрос\n"
            f"📋 Тип: {test_type}\n\n"
            f"Нажмите <b>«Пройти тест»</b> чтобы начать!"
        )
        btn_text = "▶️ Пройти тест"
        desc = f"❓ {q_count} вопросов • ⏱ {time_per_q} сек"
    else:
        text = (
            f"📚 <b>{title}</b>\n\n"
            f"❓ Сұрақ: {q_count}\n"
            f"⏱ {time_per_q} сек/сұрақ\n\n"
            f"<b>«Тест тапсыру»</b> батырмасын басыңыз!"
        )
        btn_text = "▶️ Тест тапсыру"
        desc = f"❓ {q_count} сұрақ • ⏱ {time_per_q} сек"

    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text=btn_text,
            url=f"https://t.me/historykazakhkz_bot?start=test_{test_id}"
        )
    ]])

    return InlineQueryResultArticle(
        id=f"test_{test_id}",
        title=title,
        description=desc,
        input_message_content=InputTextMessageContent(
            message_text=text,
            parse_mode="HTML",
        ),
        reply_markup=kb,
    )
