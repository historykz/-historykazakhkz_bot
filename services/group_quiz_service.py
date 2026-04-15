import asyncio
import json
import logging
import random
import sqlite3
from datetime import datetime
from aiogram import Bot
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
import database as db
from config import DB_PATH

logger = logging.getLogger(__name__)
GROUP_QUESTION_TIME = 30
PAUSE_AFTER_MISSED = 2
_timers = {}


async def launch_group_quiz(bot: Bot, quiz_id: int, chat_id: int, lang: str = "ru") -> None:
    for n in [3, 2, 1]:
        try:
            await bot.send_message(chat_id, f"⚔️ Викторина начинается через {n}...")
        except Exception:
            pass
        await asyncio.sleep(1)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE group_quizzes SET status='active', started_at=? WHERE id=?",
                 (datetime.utcnow().isoformat(), quiz_id))
    conn.commit()
    conn.close()
    await send_group_question(bot, quiz_id, chat_id, lang)


async def send_group_question(bot: Bot, quiz_id: int, chat_id: int, lang: str = "ru") -> None:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    quiz = conn.execute("SELECT * FROM group_quizzes WHERE id=?", (quiz_id,)).fetchone()
    conn.close()
    if not quiz or quiz["status"] != "active":
        return
    q_order = json.loads(quiz["question_order"]) if quiz["question_order"] else []
    idx = quiz["current_q_index"]
    if idx >= len(q_order):
        await finish_group_quiz(bot, quiz_id, chat_id, lang)
        return
    qid = q_order[idx]
    q = db.get_question(qid)
    opts = db.get_options(qid)
    if not q or not opts:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("UPDATE group_quizzes SET current_q_index=? WHERE id=?", (idx+1, quiz_id))
        conn.commit()
        conn.close()
        await send_group_question(bot, quiz_id, chat_id, lang)
        return
    opts_list = list(opts)
    random.shuffle(opts_list)
    text = f"❓ Вопрос {idx+1}/{len(q_order)}\n\n<b>{q['text']}</b>\n\n⏱ {GROUP_QUESTION_TIME} сек"
    btns = [[InlineKeyboardButton(
        text=f"{chr(65+i)}) {o['text'][:50]}",
        callback_data=f"gquiz_answer_{quiz_id}_{qid}_{i}"
    )] for i, o in enumerate(opts_list)]
    kb = InlineKeyboardMarkup(inline_keyboard=btns)
    try:
        await bot.send_message(chat_id, text, reply_markup=kb, parse_mode="HTML", protect_content=True)
    except Exception as e:
        logger.error("send_group_question: %s", e)
        return
    _cancel_timer(quiz_id)
    task = asyncio.create_task(_group_timer(bot, quiz_id, qid, chat_id, lang, GROUP_QUESTION_TIME))
    _timers[quiz_id] = task


async def _group_timer(bot: Bot, quiz_id: int, question_id: int, chat_id: int, lang: str, seconds: int) -> None:
    await asyncio.sleep(seconds)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    quiz = conn.execute("SELECT * FROM group_quizzes WHERE id=?", (quiz_id,)).fetchone()
    conn.close()
    if not quiz or quiz["status"] != "active":
        return
    missed = quiz["missed_counter"] + 1
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE group_quizzes SET current_q_index=?, missed_counter=? WHERE id=?",
                 (quiz["current_q_index"]+1, missed, quiz_id))
    conn.commit()
    conn.close()
    if missed >= PAUSE_AFTER_MISSED:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("UPDATE group_quizzes SET paused=1, missed_counter=0 WHERE id=?", (quiz_id,))
        conn.commit()
        conn.close()
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="▶️ Продолжить", callback_data=f"gquiz_resume_{quiz_id}")],
            [InlineKeyboardButton(text="⏹ Завершить", callback_data=f"gquiz_finish_{quiz_id}")]
        ])
        try:
            await bot.send_message(chat_id, "⏸ Пауза! Нажмите «Продолжить».", reply_markup=kb)
        except Exception:
            pass
        return
    await send_group_question(bot, quiz_id, chat_id, lang)


def _cancel_timer(quiz_id: int) -> None:
    task = _timers.pop(quiz_id, None)
    if task and not task.done():
        task.cancel()


async def handle_group_answer(cq: CallbackQuery, quiz_id: int, question_id: int, option_idx: int) -> None:
    if db.has_answered_group_question(quiz_id, cq.from_user.id, question_id):
        await cq.answer("Вы уже ответили!")
        return
    opts = list(db.get_options(question_id))
    if option_idx >= len(opts):
        return
    chosen = opts[option_idx]
    is_correct = bool(chosen["is_correct"])
    db.save_answered_group_question(quiz_id, cq.from_user.id, question_id, is_correct)
    if is_correct:
        db.add_group_quiz_score(quiz_id, cq.from_user.id, 1)
    await cq.answer("✅ Правильно!" if is_correct else "❌ Неверно!")


async def resume_group_quiz(bot: Bot, quiz_id: int, chat_id: int, lang: str = "ru") -> None:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE group_quizzes SET paused=0, missed_counter=0 WHERE id=?", (quiz_id,))
    conn.commit()
    conn.close()
    await send_group_question(bot, quiz_id, chat_id, lang)


async def finish_group_quiz(bot: Bot, quiz_id: int, chat_id: int, lang: str = "ru", forced: bool = False) -> None:
    _cancel_timer(quiz_id)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE group_quizzes SET status='finished', finished_at=? WHERE id=?",
                 (datetime.utcnow().isoformat(), quiz_id))
    conn.commit()
    conn.close()
    top = db.group_quiz_top(quiz_id)
    text = "🏆 Результаты викторины!\n\n"
    if top:
        for i, row in enumerate(top, 1):
            medal = ["🥇","🥈","🥉"][i-1] if i<=3 else f"{i}."
            text += f"{medal} {row.get('full_name','?')} — {row.get('score',0)} очков\n"
        text += f"\n🎉 Победитель: {top[0].get('full_name','?')}!"
    else:
        text += "Нет результатов."
    try:
        await bot.send_message(chat_id, text)
    except Exception as e:
        logger.error("finish_group_quiz: %s", e)
