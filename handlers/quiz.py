import logging
import sqlite3
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database import get_user, get_test, get_active_group_quiz, create_group_quiz, join_group_quiz
from services.group_quiz_service import launch_group_quiz, handle_group_answer, resume_group_quiz, finish_group_quiz
from config import DB_PATH

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data.startswith("group_start_"))
async def cb_group_start(cq: CallbackQuery):
    test_id = int(cq.data.split("_")[-1])
    user_id = cq.from_user.id
    db_user = get_user(user_id)
    lang = db_user.get("language", "ru") if db_user else "ru"
    if cq.message.chat.type == "private":
        await cq.answer("Только в группах!" if lang=="ru" else "Тек топтарда!", show_alert=True)
        return
    existing = get_active_group_quiz(cq.message.chat.id)
    if existing:
        await cq.answer("Уже идёт викторина!" if lang=="ru" else "Викторина жүріп жатыр!", show_alert=True)
        return
    test = get_test(test_id)
    if not test:
        await cq.answer("Тест не найден")
        return
    if not test.get("allow_group"):
        await cq.answer("Этот тест недоступен для групп." if lang=="ru" else "Топтар үшін жоқ.", show_alert=True)
        return
    quiz_id = create_group_quiz(chat_id=cq.message.chat.id, test_id=test_id, started_by=user_id)
    join_group_quiz(quiz_id, user_id)
    text = f"🎯 <b>{test['title']}</b>\n\nГрупповая викторина!\n\nНажмите «Присоединиться»." if lang=="ru" else f"🎯 <b>{test['title']}</b>\n\nТоптық викторина!\n\nҚосылу батырмасын басыңыз."
    await cq.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✋ Присоединиться" if lang=="ru" else "✋ Қосылу", callback_data=f"quiz_join_{quiz_id}")],
        [InlineKeyboardButton(text="▶️ Запустить" if lang=="ru" else "▶️ Іске қосу", callback_data=f"quiz_launch_{quiz_id}")],
    ]), parse_mode="HTML")
    await cq.answer()


@router.callback_query(F.data.startswith("quiz_join_"))
async def cb_quiz_join(cq: CallbackQuery):
    join_group_quiz(int(cq.data.split("_")[-1]), cq.from_user.id)
    await cq.answer("✅ Присоединились!")


@router.callback_query(F.data.startswith("quiz_launch_"))
async def cb_quiz_launch(cq: CallbackQuery):
    quiz_id = int(cq.data.split("_")[-1])
    db_user = get_user(cq.from_user.id)
    lang = db_user.get("language", "ru") if db_user else "ru"
    conn = sqlite3.connect(DB_PATH)
    count = conn.execute("SELECT COUNT(*) FROM group_quiz_participants WHERE quiz_id=?", (quiz_id,)).fetchone()[0]
    conn.close()
    if count < 2:
        await cq.answer("Нужно минимум 2 участника!" if lang=="ru" else "2 қатысушы керек!", show_alert=True)
        return
    await launch_group_quiz(cq.bot, quiz_id, cq.message.chat.id, lang)
    await cq.answer()


@router.callback_query(F.data.startswith("gquiz_answer_"))
async def cb_group_answer(cq: CallbackQuery):
    parts = cq.data.split("_")
    await handle_group_answer(cq, int(parts[2]), int(parts[3]), int(parts[4]))
    await cq.answer()


@router.callback_query(F.data.startswith("gquiz_resume_"))
async def cb_group_resume(cq: CallbackQuery):
    quiz_id = int(cq.data.split("_")[-1])
    db_user = get_user(cq.from_user.id)
    lang = db_user.get("language", "ru") if db_user else "ru"
    await resume_group_quiz(cq.bot, quiz_id, cq.message.chat.id, lang)
    await cq.answer()


@router.callback_query(F.data.startswith("gquiz_finish_"))
async def cb_group_finish(cq: CallbackQuery):
    quiz_id = int(cq.data.split("_")[-1])
    db_user = get_user(cq.from_user.id)
    lang = db_user.get("language", "ru") if db_user else "ru"
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    quiz = conn.execute("SELECT * FROM group_quizzes WHERE id=?", (quiz_id,)).fetchone()
    conn.close()
    if not quiz:
        await cq.answer("Не найдена")
        return
    is_creator = quiz["started_by"] == cq.from_user.id
    is_admin = False
    try:
        member = await cq.bot.get_chat_member(cq.message.chat.id, cq.from_user.id)
        is_admin = member.status in ("administrator", "creator")
    except Exception:
        pass
    if not is_creator and not is_admin:
        await cq.answer("Только создатель или админ!" if lang=="ru" else "Тек әкімші!", show_alert=True)
        return
    await finish_group_quiz(cq.bot, quiz_id, cq.message.chat.id, lang, forced=True)
    await cq.answer()
