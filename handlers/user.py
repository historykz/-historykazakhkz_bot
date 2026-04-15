import json
import logging
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

import database as db
from keyboards import test_card_kb, paid_test_kb, subscribe_kb, main_menu_kb, back_kb
from locales import get_text as t
from config import MANAGER_USERNAME, PAGE_SIZE
from services.subscription_service import check_all_channels
from services.test_runner import start_attempt, handle_answer, resume_attempt, finish_attempt
from utils import build_test_card_text

logger = logging.getLogger(__name__)
router = Router()


@router.message(F.text.in_(["📚 Тесты", "📚 Тесттер"]))
async def btn_tests(message: Message):
    user = db.get_user(message.from_user.id)
    lang = user.get("language", "ru") if user else "ru"
    await show_catalog(message, lang, "regular", page=0)


@router.message(F.text.in_(["📝 Пробники", "📝 Сынақтар"]))
async def btn_probniki(message: Message):
    user = db.get_user(message.from_user.id)
    lang = user.get("language", "ru") if user else "ru"
    await show_catalog(message, lang, "probnik", page=0)


@router.message(F.text.in_(["🧠 Викторины", "🧠 Викториналар"]))
async def btn_quizzes(message: Message):
    user = db.get_user(message.from_user.id)
    lang = user.get("language", "ru") if user else "ru"
    await show_catalog(message, lang, "quiz", page=0)


async def show_catalog(message, lang, test_type, page=0):
    tests = db.list_tests(language=lang, test_type=test_type, status_filter="active",
                          limit=PAGE_SIZE, offset=page * PAGE_SIZE)
    if not tests:
        await message.answer(t("test_not_found", lang))
        return
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    b = InlineKeyboardBuilder()
    for test in tests:
        label = f"{'🔒' if test['is_paid'] else '📚'} {test['title']}"
        b.button(text=label, callback_data=f"test:card:{test['id']}")
    b.adjust(1)
    await message.answer(t("main_menu", lang), reply_markup=b.as_markup())


@router.callback_query(F.data.startswith("test:card:"))
async def cb_test_card(call: CallbackQuery):
    test_id = int(call.data.split(":")[2])
    user = db.get_user(call.from_user.id)
    lang = user.get("language", "ru") if user else "ru"
    await call.answer()
    await show_test_card(call.message, test_id, lang)


async def show_test_card(message, test_id, lang):
    test = db.get_test(test_id)
    if not test:
        await message.answer(t("test_not_found", lang))
        return
    if test["language"] != lang:
        await message.answer(t("wrong_language_test", lang))
        return
    text = build_test_card_text(test, lang)
    user_id = message.chat.id
    if test["is_paid"] and not db.has_test_access(user_id, test_id):
        await message.answer(
            text + "\n\n" + t("paid_test_card", lang, price=test["price"], manager=MANAGER_USERNAME),
            reply_markup=paid_test_kb(lang, test_id, MANAGER_USERNAME),
            parse_mode="HTML", protect_content=True)
        return
    await message.answer(text,
        reply_markup=test_card_kb(lang, test_id, allow_group=bool(test["allow_group"])),
        parse_mode="HTML", protect_content=True)


@router.callback_query(F.data.startswith("test:check_access:"))
async def cb_check_access(call: CallbackQuery):
    test_id = int(call.data.split(":")[2])
    user = db.get_user(call.from_user.id)
    lang = user.get("language", "ru") if user else "ru"
    if db.has_test_access(call.from_user.id, test_id):
        await call.answer(t("access_granted", lang), show_alert=True)
    else:
        await call.answer(t("access_denied", lang), show_alert=True)


@router.callback_query(F.data.startswith("test:start:"))
async def cb_start_test(call: CallbackQuery, bot: Bot, state: FSMContext):
    test_id = int(call.data.split(":")[2])
    user = db.get_user(call.from_user.id)
    lang = user.get("language", "ru") if user else "ru"
    await call.answer()
    test = db.get_test(test_id)
    if not test:
        await call.message.answer(t("test_not_found", lang))
        return
    if test["is_paid"] and not db.has_test_access(call.from_user.id, test_id):
        await call.message.answer(
            t("paid_test_card", lang, price=test["price"], manager=MANAGER_USERNAME),
            reply_markup=paid_test_kb(lang, test_id, MANAGER_USERNAME))
        return
    missing = await check_all_channels(bot, call.from_user.id, test_id)
    if missing:
        await call.message.answer(t("must_subscribe", lang),
            reply_markup=subscribe_kb(lang, missing[0], test_id))
        return
    if test["attempt_limit"] > 0:
        cnt = db.count_user_attempts(call.from_user.id, test_id)
        if cnt >= test["attempt_limit"]:
            await call.message.answer(f"Вы исчерпали лимит попыток ({test['attempt_limit']}).")
            return
    await start_attempt(call.message, call.from_user.id, test_id, state)


@router.callback_query(F.data.startswith("ans:"))
async def cb_answer(call: CallbackQuery, bot: Bot):
    parts = call.data.split(":")
    if len(parts) != 4:
        await call.answer("Устаревшая кнопка", show_alert=True)
        return
    attempt_id = int(parts[1])
    question_id = int(parts[2])
    option_id = int(parts[3])
    attempt = db.get_attempt(attempt_id)
    if not attempt or attempt["user_id"] != call.from_user.id:
        await call.answer("Устаревшая кнопка", show_alert=True)
        return
    if attempt["status"] != "active":
        await call.answer("Тест уже завершён", show_alert=True)
        return
    await call.answer()
    test = db.get_test(attempt["test_id"])
    await handle_answer(bot, attempt_id, question_id, option_id, call.message.chat.id, test)


@router.callback_query(F.data.startswith("pause:"))
async def cb_pause(call: CallbackQuery, bot: Bot):
    parts = call.data.split(":")
    action = parts[1]
    attempt_id = int(parts[2])
    attempt = db.get_attempt(attempt_id)
    if not attempt or attempt["user_id"] != call.from_user.id:
        await call.answer("Устаревшая кнопка", show_alert=True)
        return
    await call.answer()
    test = db.get_test(attempt["test_id"])
    if action == "continue":
        await resume_attempt(bot, attempt_id, call.message.chat.id, test)
    elif action == "finish":
        db.update_attempt(attempt_id, {"status": "finished"})
        await finish_attempt(bot, attempt_id, call.message.chat.id, test)


@router.callback_query(F.data.startswith("sub:check:"))
async def cb_check_sub(call: CallbackQuery, bot: Bot):
    test_id = int(call.data.split(":")[2])
    user = db.get_user(call.from_user.id)
    lang = user.get("language", "ru") if user else "ru"
    missing = await check_all_channels(bot, call.from_user.id, test_id)
    if missing:
        await call.answer(t("sub_fail", lang), show_alert=True)
    else:
        await call.answer(t("sub_ok", lang), show_alert=True)


@router.callback_query(F.data.startswith("test:share:"))
async def cb_share_test(call: CallbackQuery, bot: Bot):
    test_id = int(call.data.split(":")[2])
    me = await bot.get_me()
    link = f"https://t.me/{me.username}?start=test_{test_id}"
    await call.answer()
    await call.message.answer(f"📨 Поделиться тестом:\n\n{link}", protect_content=True)


@router.message(F.text.in_(["📊 Мои результаты", "📊 Нәтижелерім"]))
async def btn_my_results(message: Message):
    uid = message.from_user.id
    user = db.get_user(uid)
    lang = user.get("language", "ru") if user else "ru"
    import sqlite3
    from config import DB_PATH
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT ta.id, t.title, ta.correct_answers, ta.wrong_answers,
               ta.skipped_answers, ta.attempt_number, ta.is_counted
        FROM test_attempts ta
        JOIN tests t ON t.id=ta.test_id
        WHERE ta.user_id=? AND ta.status='finished'
        ORDER BY ta.id DESC LIMIT 20""", (uid,)).fetchall()
    conn.close()
    if not rows:
        await message.answer("Результатов пока нет.")
        return
    lines = []
    for row in rows:
        total = row["correct_answers"] + row["wrong_answers"] + row["skipped_answers"]
        pct = round(row["correct_answers"] / total * 100, 1) if total else 0
        mark = "✅" if row["is_counted"] else "🔄"
        lines.append(f"{mark} <b>{row['title']}</b>\n   {row['correct_answers']}/{total} ({pct}%)")
    await message.answer("\n\n".join(lines), parse_mode="HTML", protect_content=True)
