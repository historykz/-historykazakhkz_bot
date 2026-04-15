import asyncio
import json
import logging
import random
import sqlite3
from datetime import datetime
from aiogram import Bot
from aiogram.types import CallbackQuery
import database as db
from config import DB_PATH

logger = logging.getLogger(__name__)
DUEL_QUESTIONS_COUNT = 10
DUEL_QUESTION_TIME = 20
BASE_SCORE = 100

_duel_timers = {}
_duel_q_idx = {}


async def start_duel(bot: Bot, duel_id: int) -> None:
    duel = db.get_duel(duel_id)
    if not duel:
        return
    p1, p2 = duel["player1_id"], duel["player2_id"]
    for n in [3, 2, 1]:
        for uid in [p1, p2]:
            try:
                await bot.send_message(uid, f"⚔️ Дуэль начинается через {n}...")
            except Exception:
                pass
        await asyncio.sleep(1)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE duels SET status='active', started_at=? WHERE id=?",
                 (datetime.utcnow().isoformat(), duel_id))
    conn.commit()
    conn.close()
    _duel_q_idx[duel_id] = 0
    await send_duel_question(bot, duel_id)


async def send_duel_question(bot: Bot, duel_id: int) -> None:
    duel = db.get_duel(duel_id)
    if not duel or duel["status"] != "active":
        return
    q_ids = json.loads(duel["question_ids"])
    idx = _duel_q_idx.get(duel_id, 0)
    if idx >= len(q_ids):
        await finish_duel(bot, duel_id)
        return
    qid = q_ids[idx]
    q = db.get_question(qid)
    opts = db.get_options(qid)
    if not q or not opts:
        _duel_q_idx[duel_id] = idx + 1
        await send_duel_question(bot, duel_id)
        return
    opts_list = list(opts)
    random.shuffle(opts_list)
    p1, p2 = duel["player1_id"], duel["player2_id"]
    for uid in [p1, p2]:
        text = f"⚔️ Вопрос {idx+1}/{len(q_ids)}\n\n<b>{q['text']}</b>\n\n⏱ {DUEL_QUESTION_TIME} сек"
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        btns = [[InlineKeyboardButton(
            text=f"{chr(65+i)}) {o['text'][:50]}",
            callback_data=f"duel_answer_{duel_id}_{qid}_{i}"
        )] for i, o in enumerate(opts_list)]
        kb = InlineKeyboardMarkup(inline_keyboard=btns)
        try:
            await bot.send_message(uid, text, reply_markup=kb, parse_mode="HTML", protect_content=True)
        except Exception as e:
            logger.error("send_duel_question to %s: %s", uid, e)
    _cancel_duel_timer(duel_id)
    task = asyncio.create_task(_duel_timer(bot, duel_id, qid, DUEL_QUESTION_TIME))
    _duel_timers[duel_id] = task


async def _duel_timer(bot: Bot, duel_id: int, question_id: int, seconds: int) -> None:
    await asyncio.sleep(seconds)
    duel = db.get_duel(duel_id)
    if not duel or duel["status"] != "active":
        return
    _duel_q_idx[duel_id] = _duel_q_idx.get(duel_id, 0) + 1
    await send_duel_question(bot, duel_id)


def _cancel_duel_timer(duel_id: int) -> None:
    task = _duel_timers.pop(duel_id, None)
    if task and not task.done():
        task.cancel()


async def handle_duel_answer(cq: CallbackQuery, duel_id: int, question_id: int, option_idx: int) -> None:
    duel = db.get_duel(duel_id)
    if not duel or duel["status"] != "active":
        return
    q_ids = json.loads(duel["question_ids"])
    idx = _duel_q_idx.get(duel_id, 0)
    if idx >= len(q_ids) or q_ids[idx] != question_id:
        return
    opts = list(db.get_options(question_id))
    if option_idx >= len(opts):
        return
    chosen = opts[option_idx]
    is_correct = bool(chosen["is_correct"])
    score = BASE_SCORE if is_correct else 0
    db.save_duel_answer(duel_id, cq.from_user.id, question_id, chosen["id"], is_correct, 0, score)
    p1, p2 = duel["player1_id"], duel["player2_id"]
    conn = sqlite3.connect(DB_PATH)
    p1_done = conn.execute("SELECT 1 FROM duel_answers WHERE duel_id=? AND user_id=? AND question_id=?",
                           (duel_id, p1, question_id)).fetchone()
    p2_done = conn.execute("SELECT 1 FROM duel_answers WHERE duel_id=? AND user_id=? AND question_id=?",
                           (duel_id, p2, question_id)).fetchone()
    conn.close()
    if p1_done and p2_done:
        _cancel_duel_timer(duel_id)
        s1 = db.get_duel_score(duel_id, p1)
        s2 = db.get_duel_score(duel_id, p2)
        for uid in [p1, p2]:
            my = s1 if uid == p1 else s2
            opp = s2 if uid == p1 else s1
            try:
                await cq.bot.send_message(uid, f"📊 Счёт: Вы {my} — {opp} Соперник", protect_content=True)
            except Exception:
                pass
        _duel_q_idx[duel_id] = idx + 1
        await asyncio.sleep(1)
        await send_duel_question(cq.bot, duel_id)


async def finish_duel(bot: Bot, duel_id: int) -> None:
    _cancel_duel_timer(duel_id)
    duel = db.get_duel(duel_id)
    if not duel:
        return
    p1, p2 = duel["player1_id"], duel["player2_id"]
    s1 = db.get_duel_score(duel_id, p1)
    s2 = db.get_duel_score(duel_id, p2)
    winner = p1 if s1 > s2 else (p2 if s2 > s1 else None)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE duels SET status='finished', winner_id=?, finished_at=? WHERE id=?",
                 (winner, datetime.utcnow().isoformat(), duel_id))
    conn.commit()
    conn.close()
    for uid in [p1, p2]:
        my = s1 if uid == p1 else s2
        opp = s2 if uid == p1 else s1
        if winner is None:
            text = f"🤝 Ничья! Счёт: {my}:{opp}"
        elif winner == uid:
            text = f"🏆 Вы победили! Счёт: {my}:{opp}"
        else:
            text = f"💀 Вы проиграли. Счёт: {my}:{opp}"
        try:
            await bot.send_message(uid, text, protect_content=True)
        except Exception as e:
            logger.error("finish_duel notify %s: %s", uid, e)
    if winner:
        db.grant_achievement(winner, "duel_win")
    _duel_q_idx.pop(duel_id, None)
