import logging
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

import database as db
from keyboards import paid_test_kb, subscribe_kb
from config import MANAGER_USERNAME, PAGE_SIZE
from services.subscription_service import check_all_channels
from services.test_runner import start_attempt, handle_answer, resume_attempt, finish_attempt
from utils import build_test_card_text

logger = logging.getLogger(__name__)
router = Router()


# ── Тесты — показать разделы ───────────────────────

@router.message(F.text.in_(["📚 Тесты", "📚 Тесттер"]))
@router.message(F.text.in_(["📝 Пробники", "📝 Сынақтар"]))
@router.message(F.text.in_(["🧠 Викторины", "🧠 Викториналар"]))
async def btn_tests(message: Message):
    user = db.get_user(message.from_user.id)
    lang = user.get("language", "ru") if user else "ru"
    await show_subjects(message, lang)


async def show_subjects(message, lang: str):
    subjects = db.get_subjects()
    if not subjects:
        await message.answer(
            "📭 Разделов пока нет." if lang == "ru" else "📭 Бөлімдер жоқ."
        )
        return
    btns = []
    for s in subjects:
        tests = db.list_tests_by_subject(s["name"], lang)
        count = len(tests)
        btns.append([InlineKeyboardButton(
            text=f"📂 {s['name']} ({count})",
            callback_data=f"subject_{s['id']}_{s['name']}"
        )])
    title = "📚 Выберите раздел:" if lang == "ru" else "📚 Бөлімді таңдаңыз:"
    await message.answer(title, reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))


@router.callback_query(F.data.startswith("subject_"))
async def cb_subject(call: CallbackQuery):
    parts = call.data.split("_", 2)
    subject_name = parts[2]
    user = db.get_user(call.from_user.id)
    lang = user.get("language", "ru") if user else "ru"
    await call.answer()
    tests = db.list_tests_by_subject(subject_name, lang)
    if not tests:
        await call.message.edit_text(
            f"📭 В разделе «{subject_name}» тестов нет."
            if lang == "ru"
            else f"📭 «{subject_name}» бөлімінде тест жоқ.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад" if lang == "ru" else "◀️ Артқа",
                                      callback_data="back_to_subjects")]
            ])
        )
        return
    btns = []
    for test in tests:
        icon = "🔒" if test["is_paid"] else "📚"
        q = test.get("question_count", 0)
        btns.append([InlineKeyboardButton(
            text=f"{icon} {test['title'][:35]} ({q} вопр.)",
            callback_data=f"test:card:{test['id']}"
        )])
    btns.append([InlineKeyboardButton(
        text="◀️ Назад" if lang == "ru" else "◀️ Артқа",
        callback_data="back_to_subjects"
    )])
    await call.message.edit_text(
        f"📂 <b>{subject_name}</b>" if lang == "ru" else f"📂 <b>{subject_name}</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=btns),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "back_to_subjects")
async def cb_back_subjects(call: CallbackQuery):
    user = db.get_user(call.from_user.id)
    lang = user.get("language", "ru") if user else "ru"
    await call.answer()
    subjects = db.get_subjects()
    if not subjects:
        await call.message.edit_text(
            "📭 Разделов нет." if lang == "ru" else "📭 Бөлімдер жоқ."
        )
        return
    btns = []
    for s in subjects:
        tests = db.list_tests_by_subject(s["name"], lang)
        btns.append([InlineKeyboardButton(
            text=f"📂 {s['name']} ({len(tests)})",
            callback_data=f"subject_{s['id']}_{s['name']}"
        )])
    await call.message.edit_text(
        "📚 Выберите раздел:" if lang == "ru" else "📚 Бөлімді таңдаңыз:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=btns)
    )


# ── Карточка теста ─────────────────────────────────

@router.callback_query(F.data.startswith("test:card:"))
async def cb_test_card(call: CallbackQuery):
    test_id = int(call.data.split(":")[2])
    user = db.get_user(call.from_user.id)
    lang = user.get("language", "ru") if user else "ru"
    await call.answer()
    await show_test_card(call.message, test_id, lang)


async def show_test_card(message, test_id: int, lang: str):
    test = db.get_test(test_id)
    if not test:
        await message.answer("❌ Тест не найден." if lang == "ru" else "❌ Тест табылмады.")
        return
    text = build_test_card_text(test, lang)
    user_id = message.chat.id
    if test["is_paid"] and not db.has_test_access(user_id, test_id):
        await message.answer(
            text + f"\n\n💰 Платный: {test.get('price', 0)} тг\nДля доступа: @{MANAGER_USERNAME}",
            reply_markup=paid_test_kb(lang, test_id, MANAGER_USERNAME),
            parse_mode="HTML"
        )
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="▶️ Начать тест" if lang == "ru" else "▶️ Тест бастау",
            callback_data=f"test:start:{test_id}"
        )],
        [InlineKeyboardButton(
            text="📤 Отправить в группу" if lang == "ru" else "📤 Топқа жіберу",
            switch_inline_query=f"test_{test_id}"
        )],
        [InlineKeyboardButton(
            text="📨 Поделиться" if lang == "ru" else "📨 Бөлісу",
            callback_data=f"test:share:{test_id}"
        )],
        [InlineKeyboardButton(
            text="◀️ Назад" if lang == "ru" else "◀️ Артқа",
            callback_data="back_to_subjects"
        )],
    ])
    await message.answer(text, reply_markup=kb, parse_mode="HTML")


# ── Старт теста ────────────────────────────────────

@router.callback_query(F.data.startswith("test:start:"))
async def cb_start_test(call: CallbackQuery, bot: Bot, state: FSMContext):
    test_id = int(call.data.split(":")[2])
    user = db.get_user(call.from_user.id)
    lang = user.get("language", "ru") if user else "ru"
    await call.answer()
    test = db.get_test(test_id)
    if not test:
        await call.message.answer("❌ Тест не найден.")
        return
    if test["is_paid"] and not db.has_test_access(call.from_user.id, test_id):
        await call.message.answer(
            f"💰 Платный тест. Обратитесь: @{MANAGER_USERNAME}",
            reply_markup=paid_test_kb(lang, test_id, MANAGER_USERNAME)
        )
        return
    missing = await check_all_channels(bot, call.from_user.id, test_id)
    if missing:
        await call.message.answer(
            "📢 Подпишитесь на канал:" if lang == "ru" else "📢 Арнаға жазылыңыз:",
            reply_markup=subscribe_kb(lang, missing[0], test_id)
        )
        return
    await start_attempt(call.message, call.from_user.id, test_id, state)


# ── Поделиться ─────────────────────────────────────

@router.callback_query(F.data.startswith("test:share:"))
async def cb_share_test(call: CallbackQuery, bot: Bot):
    test_id = int(call.data.split(":")[2])
    me = await bot.get_me()
    link = f"https://t.me/{me.username}?start=test_{test_id}"
    await call.answer()
    await call.message.answer(f"📨 Ссылка:\n\n{link}")


@router.callback_query(F.data.startswith("test:check_access:"))
async def cb_check_access(call: CallbackQuery):
    test_id = int(call.data.split(":")[2])
    user = db.get_user(call.from_user.id)
    lang = user.get("language", "ru") if user else "ru"
    if db.has_test_access(call.from_user.id, test_id):
        await call.answer("✅ Доступ открыт!" if lang == "ru" else "✅ Қолжетімді!", show_alert=True)
    else:
        await call.answer("❌ Доступа нет." if lang == "ru" else "❌ Жоқ.", show_alert=True)


@router.callback_query(F.data.startswith("sub:check:"))
async def cb_check_sub(call: CallbackQuery, bot: Bot):
    test_id = int(call.data.split(":")[2])
    user = db.get_user(call.from_user.id)
    lang = user.get("language", "ru") if user else "ru"
    missing = await check_all_channels(bot, call.from_user.id, test_id)
    if missing:
        await call.answer("❌ Не подписаны!" if lang == "ru" else "❌ Жазылмадыңыз!", show_alert=True)
    else:
        await call.answer("✅ Подписка подтверждена!" if lang == "ru" else "✅ Расталды!", show_alert=True)


# ── Мои результаты ─────────────────────────────────

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
        ORDER BY ta.id DESC LIMIT 20
    """, (uid,)).fetchall()
    conn.close()
    if not rows:
        await message.answer("📭 Результатов нет." if lang == "ru" else "📭 Нәтиже жоқ.")
        return
    lines = []
    for row in rows:
        total = row["correct_answers"] + row["wrong_answers"] + row["skipped_answers"]
        pct = round(row["correct_answers"] / total * 100, 1) if total else 0
        lines.append(f"✅ <b>{row['title']}</b>\n   {row['correct_answers']}/{total} ({pct}%)")
    await message.answer("\n\n".join(lines), parse_mode="HTML")
