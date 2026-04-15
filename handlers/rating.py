import logging
import sqlite3
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database import get_user
from config import DB_PATH
from keyboards import back_kb

logger = logging.getLogger(__name__)
router = Router()


@router.message(F.text.in_(["🏆 Рейтинг", "🏆 Рейтинг"]))
@router.callback_query(F.data == "section_rating")
async def show_rating_menu(update):
    if isinstance(update, CallbackQuery):
        user_id = update.from_user.id
        send = update.message.edit_text
        await update.answer()
    else:
        user_id = update.from_user.id
        send = update.answer
    db_user = get_user(user_id)
    lang = db_user.get("language", "ru") if db_user else "ru"
    text = "🏆 Рейтинги\n\nВыберите:" if lang=="ru" else "🏆 Рейтингтер\n\nТаңдаңыз:"
    btns = [
        [InlineKeyboardButton(text="🌐 Общий" if lang=="ru" else "🌐 Жалпы", callback_data="rating_global")],
        [InlineKeyboardButton(text="📅 Неделя" if lang=="ru" else "📅 Апта", callback_data="rating_week")],
        [InlineKeyboardButton(text="📆 Месяц" if lang=="ru" else "📆 Ай", callback_data="rating_month")],
        [InlineKeyboardButton(text="📅 Daily", callback_data="daily_rating")],
        [InlineKeyboardButton(text="⚔️ Дуэли" if lang=="ru" else "⚔️ Дуэль", callback_data="rating_duels")],
    ]
    await send(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))


@router.callback_query(F.data.in_(["rating_global", "rating_week", "rating_month"]))
async def cb_rating(cq: CallbackQuery):
    db_user = get_user(cq.from_user.id)
    lang = db_user.get("language", "ru") if db_user else "ru"
    scope = cq.data.replace("rating_", "")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    if scope == "global":
        rows = conn.execute("""
            SELECT u.full_name, u.telegram_id,
                   MAX(a.correct_answers*100.0/NULLIF(a.correct_answers+a.wrong_answers+a.skipped_answers,0)) as best_pct
            FROM test_attempts a JOIN users u ON a.user_id=u.telegram_id
            WHERE a.status='finished' AND a.is_counted=1
            GROUP BY a.user_id ORDER BY best_pct DESC LIMIT 10
        """).fetchall()
        title = "🌐 Общий рейтинг" if lang=="ru" else "🌐 Жалпы рейтинг"
    elif scope == "week":
        rows = conn.execute("""
            SELECT u.full_name, u.telegram_id,
                   AVG(a.correct_answers*100.0/NULLIF(a.correct_answers+a.wrong_answers+a.skipped_answers,0)) as best_pct
            FROM test_attempts a JOIN users u ON a.user_id=u.telegram_id
            WHERE a.status='finished' AND a.is_counted=1 AND a.end_time>=datetime('now','-7 days')
            GROUP BY a.user_id ORDER BY best_pct DESC LIMIT 10
        """).fetchall()
        title = "📅 Рейтинг недели" if lang=="ru" else "📅 Апта рейтингі"
    else:
        rows = conn.execute("""
            SELECT u.full_name, u.telegram_id,
                   AVG(a.correct_answers*100.0/NULLIF(a.correct_answers+a.wrong_answers+a.skipped_answers,0)) as best_pct
            FROM test_attempts a JOIN users u ON a.user_id=u.telegram_id
            WHERE a.status='finished' AND a.is_counted=1 AND a.end_time>=datetime('now','-30 days')
            GROUP BY a.user_id ORDER BY best_pct DESC LIMIT 10
        """).fetchall()
        title = "📆 Рейтинг месяца" if lang=="ru" else "📆 Ай рейтингі"
    conn.close()
    text = f"{title}\n\n"
    if rows:
        my_rank = None
        for i, row in enumerate(rows, 1):
            medal = ["🥇","🥈","🥉"][i-1] if i<=3 else f"{i}."
            pct = row["best_pct"] or 0
            text += f"{medal} {row['full_name']} — {pct:.1f}%\n"
            if row["telegram_id"] == cq.from_user.id:
                my_rank = i
        text += f"\n📍 Ваше место: #{my_rank}" if my_rank else ("\n📍 Вас нет в топ-10." if lang=="ru" else "\n📍 Топ-10-да жоқсыз.")
    else:
        text += "Нет данных." if lang=="ru" else "Деректер жоқ."
    await cq.message.edit_text(text, reply_markup=back_kb("section_rating"))
    await cq.answer()


@router.callback_query(F.data == "rating_duels")
async def cb_rating_duels(cq: CallbackQuery):
    db_user = get_user(cq.from_user.id)
    lang = db_user.get("language", "ru") if db_user else "ru"
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT u.full_name, COUNT(d.id) as wins
        FROM duels d JOIN users u ON d.winner_id=u.telegram_id
        WHERE d.status='finished'
        GROUP BY d.winner_id ORDER BY wins DESC LIMIT 10
    """).fetchall()
    conn.close()
    text = "⚔️ Рейтинг дуэлей\n\n" if lang=="ru" else "⚔️ Дуэль рейтингі\n\n"
    if rows:
        for i, row in enumerate(rows, 1):
            medal = ["🥇","🥈","🥉"][i-1] if i<=3 else f"{i}."
            text += f"{medal} {row['full_name']} — {row['wins']} побед\n"
    else:
        text += "Дуэлей пока нет." if lang=="ru" else "Дуэль жоқ."
    await cq.message.edit_text(text, reply_markup=back_kb("section_rating"))
    await cq.answer()
