import logging
import sqlite3
import json
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from database import get_user, get_user_streak, get_setting
from services.daily_service import get_or_create_daily_task, user_completed_today
from services.test_runner import start_attempt
from keyboards import back_kb
from utils import today_str
from config import DB_PATH

logger = logging.getLogger(__name__)
router = Router()


@router.message(F.text.contains("Daily ENT"))
@router.callback_query(F.data == "section_daily")
async def show_daily(update):
    if isinstance(update, CallbackQuery):
        user_id = update.from_user.id
        send = update.message.edit_text
        await update.answer()
    else:
        user_id = update.from_user.id
        send = update.answer
    db_user = get_user(user_id)
    lang = db_user.get("language", "ru") if db_user else "ru"
    enabled = get_setting("daily_enabled") or "1"
    if enabled != "1":
        await send("📅 Daily ENT временно недоступен." if lang=="ru" else "📅 Daily ENT уақытша қолжетімді емес.")
        return
    already_done = user_completed_today(user_id, lang)
    streak = get_user_streak(user_id)
    task = get_or_create_daily_task(lang)
    streak_emoji = "🔥" if streak["current"] > 0 else "💤"
    text = (f"📅 <b>Daily ENT</b>\n\nПредмет: {task.get('subject','Смешанный')}\nВопросов: {task.get('question_count',10)}\n\n{streak_emoji} Streak: {streak['current']} дней\n🏆 Лучший: {streak['best']} дней"
            if lang=="ru" else
            f"📅 <b>Daily ENT</b>\n\nПән: {task.get('subject','Аралас')}\nСұрақ: {task.get('question_count',10)}\n\n{streak_emoji} Streak: {streak['current']} күн\n🏆 Үздік: {streak['best']} күн")
    if already_done:
        text += "\n\n✅ Вы уже прошли сегодня!" if lang=="ru" else "\n\n✅ Бүгін өттіңіз!"
    btns = []
    if not already_done:
        btns.append([InlineKeyboardButton(text="▶️ Начать Daily ENT" if lang=="ru" else "▶️ Daily ENT бастау", callback_data=f"start_daily_{task['id']}")])
    btns.append([InlineKeyboardButton(text="📊 Мой streak" if lang=="ru" else "📊 Streak", callback_data="daily_streak")])
    btns.append([InlineKeyboardButton(text="🏆 Рейтинг" if lang=="ru" else "🏆 Рейтинг", callback_data="daily_rating")])
    await send(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=btns), parse_mode="HTML")


@router.callback_query(F.data.startswith("start_daily_"))
async def cb_start_daily(cq: CallbackQuery, state: FSMContext):
    task_id = int(cq.data.split("_")[-1])
    db_user = get_user(cq.from_user.id)
    lang = db_user.get("language", "ru") if db_user else "ru"
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    task = conn.execute("SELECT * FROM daily_tasks WHERE id=?", (task_id,)).fetchone()
    conn.close()
    if not task:
        await cq.answer("Задание не найдено" if lang=="ru" else "Тапсырма табылмады")
        return
    if user_completed_today(cq.from_user.id, lang):
        await cq.answer("Вы уже прошли сегодня!" if lang=="ru" else "Бүгін өттіңіз!", show_alert=True)
        return
    question_ids = json.loads(task["question_ids"]) if task["question_ids"] else []
    if not question_ids:
        await cq.answer("Нет вопросов" if lang=="ru" else "Сұрақ жоқ")
        return
    await state.update_data(daily_task_id=task_id, daily_question_ids=question_ids)
    await start_attempt(cq.message, cq.from_user.id, test_id=None, state=state, daily_question_ids=question_ids, daily_task_id=task_id)
    await cq.answer()


@router.callback_query(F.data == "daily_streak")
async def cb_daily_streak(cq: CallbackQuery):
    db_user = get_user(cq.from_user.id)
    lang = db_user.get("language", "ru") if db_user else "ru"
    streak = get_user_streak(cq.from_user.id)
    s = streak["current"]
    best = streak["best"]
    emoji = "🏆" if s>=30 else "🔥" if s>=7 else "⚡" if s>=3 else "✨" if s>=1 else "💤"
    if lang == "ru":
        text = f"📊 Daily Streak\n\n{emoji} Текущий: {s} дней\n🏆 Лучший: {best} дней\n\n"
        text += "Начните сегодня!" if s==0 else f"До 7 дней: {7-s}" if s<7 else f"До 30 дней: {30-s}" if s<30 else "Отлично!"
    else:
        text = f"📊 Daily Streak\n\n{emoji} Ағымдағы: {s} күн\n🏆 Үздік: {best} күн"
    await cq.message.edit_text(text, reply_markup=back_kb("section_daily"))
    await cq.answer()


@router.callback_query(F.data == "daily_rating")
async def cb_daily_rating(cq: CallbackQuery):
    db_user = get_user(cq.from_user.id)
    lang = db_user.get("language", "ru") if db_user else "ru"
    today = today_str()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT u.full_name, dr.correct_answers, dr.percentage
        FROM daily_results dr
        JOIN users u ON dr.user_id = u.telegram_id
        WHERE dr.task_date = ?
        ORDER BY dr.percentage DESC LIMIT 10
    """, (today,)).fetchall()
    conn.close()
    text = f"🏆 Рейтинг Daily — {today}\n\n" if lang=="ru" else f"🏆 Daily рейтинг — {today}\n\n"
    if rows:
        for i, row in enumerate(rows, 1):
            medal = ["🥇","🥈","🥉"][i-1] if i<=3 else f"{i}."
            text += f"{medal} {row['full_name']} — {row['percentage']:.0f}%\n"
    else:
        text += "Никто не прошёл сегодня." if lang=="ru" else "Бүгін өткен жоқ."
    await cq.message.edit_text(text, reply_markup=back_kb("section_daily"))
    await cq.answer()
