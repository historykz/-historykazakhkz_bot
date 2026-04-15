import logging
import sqlite3
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from database import get_user, get_active_duel_for_user, find_waiting_duel, join_duel, create_duel, cancel_duel
from services.duel_service import start_duel, handle_duel_answer
from keyboards import duel_menu_kb, cancel_duel_kb, back_kb
from config import DB_PATH

logger = logging.getLogger(__name__)
router = Router()


@router.message(F.text.in_(["⚔️ Дуэль", "⚔️ Дуэль"]))
@router.callback_query(F.data == "section_duel")
async def show_duel_menu(update):
    if isinstance(update, CallbackQuery):
        user_id = update.from_user.id
        send = update.message.edit_text
        await update.answer()
    else:
        user_id = update.from_user.id
        send = update.answer
    db_user = get_user(user_id)
    lang = db_user.get("language", "ru") if db_user else "ru"
    active = get_active_duel_for_user(user_id)
    if active:
        await send("⚔️ У вас есть активная дуэль!" if lang=="ru" else "⚔️ Белсенді дуэль бар!", reply_markup=back_kb("section_duel"))
        return
    text = "⚔️ <b>Дуэль</b>\n\nСразитесь с другим игроком!" if lang=="ru" else "⚔️ <b>Дуэль</b>\n\nБасқа ойыншымен жарысыңыз!"
    await send(text, reply_markup=duel_menu_kb(lang), parse_mode="HTML")


@router.callback_query(F.data.in_(["duel_quick", "duel_by_subject"]))
async def cb_start_duel_search(cq: CallbackQuery, state: FSMContext):
    db_user = get_user(cq.from_user.id)
    lang = db_user.get("language", "ru") if db_user else "ru"
    active = get_active_duel_for_user(cq.from_user.id)
    if active:
        await cq.answer("У вас уже есть дуэль!" if lang=="ru" else "Белсенді дуэль бар!", show_alert=True)
        return
    if cq.data == "duel_by_subject":
        await cq.message.edit_text("📚 Введите предмет:" if lang=="ru" else "📚 Пәнді еңгізіңіз:")
        await state.set_state("duel_subject_input")
        await cq.answer()
        return
    await _search_duel(cq.message, cq.from_user.id, lang, None, state)
    await cq.answer()


async def _search_duel(message, user_id, lang, subject, state):
    waiting = find_waiting_duel(subject=subject, language=lang)
    if waiting and waiting["player1_id"] != user_id:
        join_duel(waiting["id"], user_id)
        await start_duel(message.bot, waiting["id"])
        return
    duel_id = create_duel(player1_id=user_id, subject=subject, language=lang)
    await state.update_data(waiting_duel_id=duel_id)
    text = "🔍 Ищем соперника...\n\nОжидайте." if lang=="ru" else "🔍 Қарсылас іздеуде...\n\nКүтіңіз."
    await message.answer(text, reply_markup=cancel_duel_kb(lang, duel_id))


@router.callback_query(F.data.startswith("cancel_duel_"))
async def cb_cancel_duel(cq: CallbackQuery, state: FSMContext):
    duel_id = int(cq.data.split("_")[-1])
    db_user = get_user(cq.from_user.id)
    lang = db_user.get("language", "ru") if db_user else "ru"
    cancel_duel(duel_id, cq.from_user.id)
    await state.clear()
    await cq.message.edit_text("❌ Поиск отменён." if lang=="ru" else "❌ Іздеу болдырылмады.", reply_markup=back_kb("section_duel"))
    await cq.answer()


@router.callback_query(F.data.startswith("duel_answer_"))
async def cb_duel_answer(cq: CallbackQuery, state: FSMContext):
    parts = cq.data.split("_")
    duel_id = int(parts[2])
    question_id = int(parts[3])
    option_idx = int(parts[4])
    await handle_duel_answer(cq, duel_id, question_id, option_idx)
    await cq.answer()


@router.callback_query(F.data == "duel_history")
async def cb_duel_history(cq: CallbackQuery):
    db_user = get_user(cq.from_user.id)
    lang = db_user.get("language", "ru") if db_user else "ru"
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    duels = conn.execute("""
        SELECT d.*,
               CASE WHEN d.player1_id=? THEN d.player2_id ELSE d.player1_id END AS opponent_id,
               CASE WHEN d.winner_id=? THEN 1 ELSE 0 END AS won
        FROM duels d
        WHERE (d.player1_id=? OR d.player2_id=?) AND d.status='finished'
        ORDER BY d.finished_at DESC LIMIT 10
    """, (cq.from_user.id,)*4).fetchall()
    conn.close()
    text = "⚔️ История дуэлей\n\n" if lang=="ru" else "⚔️ Дуэль тарихы\n\n"
    if duels:
        wins = sum(1 for d in duels if d["won"])
        text += f"Побед: {wins} / Поражений: {len(duels)-wins}\n\n"
        for d in duels:
            text += ("🏆 Победа" if d["won"] else "💀 Поражение") + "\n"
    else:
        text += "Дуэлей пока нет." if lang=="ru" else "Дуэль жоқ."
    await cq.message.edit_text(text, reply_markup=back_kb("section_duel"))
    await cq.answer()
