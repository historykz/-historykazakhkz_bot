import logging
import sqlite3
from datetime import datetime
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from database import get_user, list_tournaments, get_tournament_leaderboard, save_tournament_result
from services.test_runner import start_attempt
from config import DB_PATH
from keyboards import back_kb

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == "section_tournaments")
async def show_tournaments(cq: CallbackQuery):
    db_user = get_user(cq.from_user.id)
    lang = db_user.get("language", "ru") if db_user else "ru"
    tours = list_tournaments()
    now = datetime.now().isoformat()[:10]
    text = "🏆 Турниры\n\n" if lang=="ru" else "🏆 Турнирлер\n\n"
    if not tours:
        text += "Турниров нет." if lang=="ru" else "Турнир жоқ."
        await cq.message.edit_text(text, reply_markup=back_kb("section_duel"))
        await cq.answer()
        return
    btns = []
    for t in tours:
        is_active = t["start_date"] <= now <= t["end_date"]
        icon = "🟢" if is_active else ("⚪" if t["end_date"] < now else "🟡")
        btns.append([InlineKeyboardButton(text=f"{icon} {t['title'][:35]}", callback_data=f"tour_card_{t['id']}")])
    await cq.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))
    await cq.answer()


@router.callback_query(F.data.startswith("tour_card_"))
async def cb_tour_card(cq: CallbackQuery):
    tour_id = int(cq.data.split("_")[-1])
    db_user = get_user(cq.from_user.id)
    lang = db_user.get("language", "ru") if db_user else "ru"
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    tour = conn.execute("SELECT * FROM tournaments WHERE id=?", (tour_id,)).fetchone()
    conn.close()
    if not tour:
        await cq.answer("Не найден")
        return
    now = datetime.now().isoformat()[:10]
    is_active = tour["start_date"] <= now <= tour["end_date"]
    status = ("🟢 Активен" if is_active else ("🏁 Завершён" if tour["end_date"] < now else "🟡 Скоро")) if lang=="ru" else ("🟢 Белсенді" if is_active else ("🏁 Аяқталды" if tour["end_date"] < now else "🟡 Жақында"))
    text = (f"🏆 <b>{tour['title']}</b>\n\nСтатус: {status}\nНачало: {tour['start_date']}\nКонец: {tour['end_date']}\nПриз: {tour.get('prize','—')}")
    btns = []
    if is_active:
        btns.append([InlineKeyboardButton(text="▶️ Участвовать" if lang=="ru" else "▶️ Қатысу", callback_data=f"tour_join_{tour_id}")])
    btns.append([InlineKeyboardButton(text="📊 Таблица" if lang=="ru" else "📊 Кесте", callback_data=f"tour_leaderboard_{tour_id}")])
    btns.append([InlineKeyboardButton(text="◀️ Назад" if lang=="ru" else "◀️ Артқа", callback_data="section_tournaments")])
    await cq.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=btns), parse_mode="HTML")
    await cq.answer()


@router.callback_query(F.data.startswith("tour_join_"))
async def cb_tour_join(cq: CallbackQuery, state: FSMContext):
    tour_id = int(cq.data.split("_")[-1])
    db_user = get_user(cq.from_user.id)
    lang = db_user.get("language", "ru") if db_user else "ru"
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    tour = conn.execute("SELECT * FROM tournaments WHERE id=?", (tour_id,)).fetchone()
    conn.close()
    if not tour or not tour["test_id"]:
        await cq.answer("Не найден")
        return
    await state.update_data(tournament_id=tour_id)
    await start_attempt(cq.message, cq.from_user.id, tour["test_id"], state)
    await cq.answer()


@router.callback_query(F.data.startswith("tour_leaderboard_"))
async def cb_tour_leaderboard(cq: CallbackQuery):
    tour_id = int(cq.data.split("_")[-1])
    db_user = get_user(cq.from_user.id)
    lang = db_user.get("language", "ru") if db_user else "ru"
    rows = get_tournament_leaderboard(tour_id)
    text = "🏆 Таблица турнира\n\n" if lang=="ru" else "🏆 Турнир кестесі\n\n"
    if rows:
        for i, row in enumerate(rows, 1):
            medal = ["🥇","🥈","🥉"][i-1] if i<=3 else f"{i}."
            text += f"{medal} {row.get('full_name','?')} — {row.get('score',0)}\n"
    else:
        text += "Участников нет." if lang=="ru" else "Қатысушы жоқ."
    await cq.message.edit_text(text, reply_markup=back_kb(f"tour_card_{tour_id}"))
    await cq.answer()
