import logging
import sqlite3
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from filters import IsAdmin
from database import (
    get_user, create_test, get_test, list_tests, delete_test,
    add_question, add_option, get_questions, count_questions,
    get_subjects, create_subject, delete_subject, list_tests_by_subject
)
from services.text_import_service import import_questions_from_text
from config import DB_PATH

logger = logging.getLogger(__name__)
router = Router()


class CreateTest(StatesGroup):
    title = State()
    subject = State()
    time_per_question = State()


class AddSubject(StatesGroup):
    name = State()


class ImportText(StatesGroup):
    waiting_test_id = State()
    waiting_text = State()


# ── Панель администратора ──────────────────────────

@router.message(IsAdmin(), F.text == "/admin")
@router.callback_query(IsAdmin(), F.data == "admin_panel")
async def admin_panel(update, state: FSMContext):
    await state.clear()
    if isinstance(update, CallbackQuery):
        send = update.message.edit_text
        await update.answer()
    else:
        send = update.answer

    from keyboards import admin_panel_kb
    await send("🛠 <b>Панель администратора</b>", reply_markup=admin_panel_kb(), parse_mode="HTML")


# ── Создание теста ─────────────────────────────────

@router.callback_query(IsAdmin(), F.data == "admin_create_test")
async def cb_create_test(cq: CallbackQuery, state: FSMContext):
    await state.set_state(CreateTest.title)
    await cq.message.edit_text("📝 Введите <b>название</b> теста:", parse_mode="HTML")
    await cq.answer()


@router.message(IsAdmin(), CreateTest.title)
async def got_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text.strip())
    subjects = get_subjects()
    if not subjects:
        await message.answer(
            "❌ Разделов нет. Сначала создайте раздел через /admin → 📂 Разделы"
        )
        await state.clear()
        return
    btns = [[InlineKeyboardButton(text=s["name"], callback_data=f"pick_subj_{s['id']}")] for s in subjects]
    btns.append([InlineKeyboardButton(text="❌ Отмена", callback_data="admin_panel")])
    await message.answer(
        "📂 Выберите <b>раздел</b>:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=btns),
        parse_mode="HTML"
    )
    await state.set_state(CreateTest.subject)


btns = [[InlineKeyboardButton(text=s["name"], callback_data=f"pick_subject_{s['id']}_{s['name']}")] for s in subjects]
@router.callback_query(IsAdmin(), F.data.startswith("pick_subj_"))
async def got_subject(cq: CallbackQuery, state: FSMContext):
    subject_id = int(cq.data.split("_")[-1])
    from database import get_subjects
    subjects = get_subjects()
    subject = next((s for s in subjects if s["id"] == subject_id), None)
    subject_name = subject["name"] if subject else "Неизвестно"
    await state.update_data(subject=subject_name)
    await cq.message.edit_text(
        f"⏱ Введите <b>время на вопрос</b> (секунды, например 30):",
        parse_mode="HTML"
    )
    await state.set_state(CreateTest.time_per_question)
    await cq.answer()


@router.message(IsAdmin(), CreateTest.time_per_question)
async def got_time(message: Message, state: FSMContext):
    try:
        time_sec = int(message.text.strip())
        if time_sec < 5 or time_sec > 300:
            await message.answer("❌ Введите число от 5 до 300")
            return
    except ValueError:
        await message.answer("❌ Введите число (например: 30)")
        return

    data = await state.get_data()
    test_id = create_test(
        title=data["title"],
        subject=data["subject"],
        time_per_question=time_sec,
        status="active",
        language="ru",
        shuffle_questions=1,
        shuffle_options=1,
        allow_group=1,
        created_by=message.from_user.id
    )
    await state.clear()

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Импорт текстом", callback_data=f"import_text_{test_id}")],
        [InlineKeyboardButton(text="◀️ В панель", callback_data="admin_panel")],
    ])
    await message.answer(
        f"✅ <b>Тест создан!</b>\n\n"
        f"📚 {data['title']}\n"
        f"📂 {data['subject']}\n"
        f"⏱ {time_sec} сек/вопрос\n\n"
        f"Теперь добавьте вопросы:",
        reply_markup=kb,
        parse_mode="HTML"
    )


# ── Импорт вопросов текстом ────────────────────────

@router.callback_query(IsAdmin(), F.data.startswith("import_text_"))
async def cb_import_text(cq: CallbackQuery, state: FSMContext):
    test_id = int(cq.data.split("_")[-1])
    await state.update_data(import_test_id=test_id)
    await state.set_state(ImportText.waiting_text)
    await cq.message.edit_text(
        "📋 <b>Вставьте вопросы</b> в формате:\n\n"
        "<code>Вопрос?\n"
        "A) Вариант 1\n"
        "B) Вариант 2 *\n"
        "C) Вариант 3\n"
        "D) Вариант 4</code>\n\n"
        "Звёздочка * после правильного ответа.\n"
        "Вопросы разделяйте пустой строкой.\n\n"
        "Когда закончите — нажмите кнопку ниже или напишите /done",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_panel")]
        ]),
        parse_mode="HTML"
    )
    await cq.answer()


@router.message(IsAdmin(), ImportText.waiting_text)
async def got_import_text(message: Message, state: FSMContext):
    data = await state.get_data()
    test_id = data.get("import_test_id")
    if not test_id:
        await state.clear()
        return

    raw = message.text.strip()
    ok, errors, error_list = import_questions_from_text(test_id, raw, imported_by=message.from_user.id)

    # Update question count
    q_count = count_questions(test_id)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE tests SET question_count=? WHERE id=?", (q_count, test_id))
    conn.commit()
    conn.close()

    text = f"✅ Добавлено вопросов: <b>{ok}</b>\n"
    if errors:
        text += f"❌ Ошибок: {errors}\n"
        if error_list:
            text += "\n".join(f"• {e}" for e in error_list[:5])

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить ещё", callback_data=f"import_text_{test_id}")],
        [InlineKeyboardButton(text="✅ Готово", callback_data="admin_my_tests")],
    ])
    await message.answer(text, reply_markup=kb, parse_mode="HTML")
    await state.clear()


@router.callback_query(IsAdmin(), F.data == "admin_import_text")
async def cb_admin_import_text(cq: CallbackQuery, state: FSMContext):
    tests = list_tests(status_filter="active", limit=30)
    if not tests:
        await cq.answer("Нет тестов. Сначала создайте тест.", show_alert=True)
        return
    btns = [[InlineKeyboardButton(text=t["title"][:40], callback_data=f"import_text_{t['id']}")] for t in tests]
    btns.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_panel")])
    await cq.message.edit_text(
        "Выберите тест для импорта:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=btns)
    )
    await cq.answer()


# ── Мои тесты ─────────────────────────────────────

@router.callback_query(IsAdmin(), F.data == "admin_my_tests")
async def cb_my_tests(cq: CallbackQuery):
    tests = list_tests(status_filter="active", limit=50)
    if not tests:
        await cq.message.edit_text(
            "📭 Тестов нет.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="➕ Создать тест", callback_data="admin_create_test")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_panel")],
            ])
        )
        await cq.answer()
        return

    btns = []
    for t in tests:
        q = count_questions(t["id"])
        btns.append([InlineKeyboardButton(
            text=f"📚 {t['title'][:30]} ({q} вопр.)",
            callback_data=f"admin_test_{t['id']}"
        )])
    btns.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_panel")])
    await cq.message.edit_text(
        "📋 <b>Мои тесты:</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=btns),
        parse_mode="HTML"
    )
    await cq.answer()


@router.callback_query(IsAdmin(), F.data.startswith("admin_test_"))
async def cb_test_manage(cq: CallbackQuery):
    test_id = int(cq.data.split("_")[-1])
    test = get_test(test_id)
    if not test:
        await cq.answer("Не найден")
        return
    q = count_questions(test_id)
    text = (
        f"📚 <b>{test['title']}</b>\n"
        f"📂 {test.get('subject') or '—'}\n"
        f"❓ Вопросов: {q}\n"
        f"⏱ {test.get('time_per_question', 30)} сек/вопрос\n"
        f"📊 Статус: {test.get('status', 'active')}"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Добавить вопросы", callback_data=f"import_text_{test_id}")],
        [InlineKeyboardButton(text="🗑 Удалить тест", callback_data=f"delete_test_{test_id}")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_my_tests")],
    ])
    await cq.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await cq.answer()


@router.callback_query(IsAdmin(), F.data.startswith("delete_test_"))
async def cb_delete_test(cq: CallbackQuery):
    test_id = int(cq.data.split("_")[-1])
    delete_test(test_id)
    await cq.answer("✅ Тест удалён!")
    await cb_my_tests(cq)


# ── Разделы ────────────────────────────────────────

@router.callback_query(IsAdmin(), F.data == "admin_notes")
@router.callback_query(IsAdmin(), F.data == "admin_subjects")
async def cb_subjects(cq: CallbackQuery):
    subjects = get_subjects()
    text = "📂 <b>Разделы:</b>\n\n"
    btns = []
    if subjects:
        for s in subjects:
            q_count = len(list_tests_by_subject(s["name"]))
            text += f"• {s['name']} ({q_count} тестов)\n"
            btns.append([InlineKeyboardButton(
                text=f"🗑 Удалить: {s['name'][:25]}",
                callback_data=f"delete_subject_{s['id']}"
            )])
    else:
        text += "Разделов нет."

    btns.append([InlineKeyboardButton(text="➕ Добавить раздел", callback_data="add_subject")])
    btns.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_panel")])
    await cq.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=btns), parse_mode="HTML")
    await cq.answer()


@router.callback_query(IsAdmin(), F.data == "add_subject")
async def cb_add_subject(cq: CallbackQuery, state: FSMContext):
    await state.set_state(AddSubject.name)
    await cq.message.edit_text(
        "📂 Введите название нового раздела:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_subjects")]
        ])
    )
    await cq.answer()


@router.message(IsAdmin(), AddSubject.name)
async def got_subject_name(message: Message, state: FSMContext):
    name = message.text.strip()
    create_subject(name)
    await state.clear()
    await message.answer(f"✅ Раздел <b>{name}</b> создан!", parse_mode="HTML")


@router.callback_query(IsAdmin(), F.data.startswith("delete_subject_"))
async def cb_delete_subject(cq: CallbackQuery):
    subject_id = int(cq.data.split("_")[-1])
    delete_subject(subject_id)
    await cq.answer("✅ Раздел удалён!")
    await cb_subjects(cq)


# ── Статистика ─────────────────────────────────────

@router.callback_query(IsAdmin(), F.data == "admin_stats")
async def cb_stats(cq: CallbackQuery):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    users = conn.execute("SELECT COUNT(*) as cnt FROM users").fetchone()["cnt"]
    tests = conn.execute("SELECT COUNT(*) as cnt FROM tests WHERE status='active'").fetchone()["cnt"]
    attempts = conn.execute("SELECT COUNT(*) as cnt FROM test_attempts WHERE status='finished'").fetchone()["cnt"]
    today = conn.execute(
        "SELECT COUNT(*) as cnt FROM users WHERE date(created_at)=date('now')"
    ).fetchone()["cnt"]
    conn.close()
    text = (
        f"📊 <b>Статистика</b>\n\n"
        f"👥 Пользователей: {users}\n"
        f"🆕 Сегодня: {today}\n"
        f"📚 Активных тестов: {tests}\n"
        f"✅ Завершённых попыток: {attempts}"
    )
    await cq.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_panel")]
        ]),
        parse_mode="HTML"
    )
    await cq.answer()


# ── Заглушки для остальных кнопок ─────────────────

@router.callback_query(IsAdmin(), F.data.in_([
    "admin_give_access", "admin_premium", "admin_block",
    "admin_channels", "admin_export", "admin_tournaments",
    "admin_ref_bonuses", "admin_daily_settings", "admin_hw",
    "admin_poll_import", "admin_run_quiz"
]))
async def cb_stub(cq: CallbackQuery):
    await cq.answer("🚧 Функция в разработке", show_alert=True)
