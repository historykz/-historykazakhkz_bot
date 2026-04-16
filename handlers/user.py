import logging
import sqlite3
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
import database as db
from keyboards import paid_test_kb, subscribe_kb
from config import MANAGER_USERNAME, PAGE_SIZE, DB_PATH
from services.subscription_service import check_all_channels
from services.test_runner import start_attempt, handle_answer, resume_attempt, finish_attempt
from utils import build_test_card_text

logger = logging.getLogger(__name__)
router = Router()


@router.message(F.text.in_(["📚 Тесты", "📚 Тесттер"]))
async def btn_tests(message: Message):
    user = db.get_user(message.from_user.id)
    lang = user.get("language", "ru") if user else "ru"
    await show_catalog(message, lang, "regular")


@router.message(F.text.in_(["📝 Пробники", "📝 Сынақтар"]))
async def btn_probniki(message: Message):
    user = db.get_user(message.from_user.id)
    lang = user.get("language", "ru") if user else "ru"
    await show_catalog(message, lang, "probnik")


@router.message(F.text.in_(["🧠 Викторины", "🧠 Викториналар"]))
async def btn_quizzes(message: Message):
    user = db.get_user(message.from_user.id)
    lang = user.get("language", "ru") if user else "ru"
    await show_catalog(message, lang, "quiz")


async def show_catalog(message, lang, test_type, page=0):
    tests = db.list_tests(language=lang, test_type=test_type, status_filter="active",
                          limit=PAGE_SIZE, offset=page * PAGE_SIZE)
    if not tests:
        await message.answer("📭 Тестов пока нет." if lang == "ru" else "📭 Тест жоқ.")
        return
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    b = InlineKeyboardBuilder()
    for test in tests:
        label = f"{'🔒' if test['is_paid'] else '📚'} {test['title']}"
        b.button(text=label, callback_data=f"test:card:{test['id']}")
    b.adjust(1)
    await message.answer(
        "📚 Выберите тест:" if lang == "ru" else "📚 Тест таңдаңыз:",
        reply_markup=b.as_markup()
    )


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
        await message.answer("❌ Тест не найден." if lang == "ru" else "❌ Тест табылмады.")
        return
    text = build_test_card_text(test, lang)
    if test.get("is_paid") and not db.has_test_access(message.chat.id, test_id):
        await message.answer(
            text + f"\n\n💰 Платный: {test.get('price', 0)} тг\nДоступ: @{MANAGER_USERNAME}",
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
            text="📨 Поделиться ссылкой" if lang == "ru" else "📨 Сілтемемен бөлісу",
            callback_data=f"test:share:{test_id}"
        )],
    ])
    await message.answer(text, reply_markup=kb, parse_mode="HTML")


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
    if test.get("is_paid") and not db.has_test_access(call.from_user.id, test_id):
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
    if test.get("attempt_limit", 0) > 0:
        cnt = db.count_user_attempts(call.from_user.id, test_id)
        if cnt >= test["attempt_limit"]:
            await call.message.answer(
                f"❌ Лимит попыток исчерпан ({test['attempt_limit']})."
                if lang == "ru" else
                f"❌ Әрекет лимиті таусылды ({test['attempt_limit']})."
            )
            return
    await start_attempt(call.message, call.from_user.id, test_id, state)


@router.callback_query(F.data.startswith("test:share:"))
async def cb_share_test(call: CallbackQuery, bot: Bot):
    test_id = int(call.data.split(":")[2])
    me = await bot.get_me()
    link = f"https://t.me/{me.username}?start=test_{test_id}"
    user = db.get_user(call.from_user.id)
    lang = user.get("language", "ru") if user else "ru"
    await call.answer()
    await call.message.answer(
        f"📨 {'Ссылка на тест' if lang == 'ru' else 'Тест сілтемесі'}:\n\n{link}"
    )


@router.callback_query(F.data.startswith("test:check_access:"))
async def cb_check_access(call: CallbackQuery):
    test_id = int(call.data.split(":")[2])
    user = db.get_user(call.from_user.id)
    lang = user.get("language", "ru") if user else "ru"
    if db.has_test_access(call.from_user.id, test_id):
        await call.answer("✅ Доступ открыт!" if lang == "ru" else "✅ Қолжетімділік ашылды!", show_alert=True)
    else:
        await call.answer("❌ Доступа нет." if lang == "ru" else "❌ Қолжетімділік жоқ.", show_alert=True)


@router.callback_query(F.data.startswith("sub:check:"))
async def cb_check_sub(call: CallbackQuery, bot: Bot):
    test_id = int(call.data.split(":")[2])
    user = db.get_user(call.from_user.id)
    lang = user.get("language", "ru") if user else "ru"
    missing = await check_all_channels(bot, call.from_user.id, test_id)
    if missing:
        await call.answer("❌ Вы не подписались!" if lang == "ru" else "❌ Жазылмадыңыз!", show_alert=True)
    else:
        await call.answer("✅ Подписка подтверждена!" if lang == "ru" else "✅ Жазылым расталды!", show_alert=True)


@router.message(F.text.in_(["📊 Мои результаты", "📊 Нәтижелерім"]))
async def btn_my_results(message: Message):
    uid = message.from_user.id
    user = db.get_user(uid)
    lang = user.get("language", "ru") if user else "ru"
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT ta.id, t.title, ta.correct_answers, ta.wrong_answers,
               ta.skipped_answers, ta.attempt_number, ta.is_counted
        FROM test_attempts ta JOIN tests t ON t.id=ta.test_id
        WHERE ta.user_id=? AND ta.status='finished'
        ORDER BY ta.id DESC LIMIT 20
    """, (uid,)).fetchall()
    conn.close()
    if not rows:
        await message.answer("📭 Результатов пока нет." if lang == "ru" else "📭 Нәтиже жоқ.")
        return
    lines = []
    for row in rows:
        total = row["correct_answers"] + row["wrong_answers"] + row["skipped_answers"]
        pct = round(row["correct_answers"] / total * 100, 1) if total else 0
        mark = "✅" if row["is_counted"] else "🔄"
        lines.append(f"{mark} <b>{row['title']}</b>\n   {row['correct_answers']}/{total} ({pct}%)")
    await message.answer("\n\n".join(lines), parse_mode="HTML")
