import asyncio
import json
import logging
import random
import sqlite3
from datetime import datetime
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
import database as db
from config import DB_PATH, PAUSE_AFTER_MISSED, DEFAULT_QUESTION_TIME

logger = logging.getLogger(__name__)

_timers = {}
_q_message_ids = {}


async def start_attempt(message: Message, user_id: int, test_id: int,
                         state: FSMContext, daily_question_ids=None,
                         daily_task_id=None) -> None:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    user = conn.execute("SELECT language FROM users WHERE telegram_id=?", (user_id,)).fetchone()
    lang = user["language"] if user else "ru"
    conn.close()

    if test_id:
        test = db.get_test(test_id)
        if not test:
            await message.answer("❌ Тест не найден.")
            return
        questions = db.get_questions(test_id)
        if not questions:
            await message.answer("❌ В тесте нет вопросов.")
            return
        q_ids = [q["id"] for q in questions]
        q_count = test.get("question_count", 0)
        if q_count and q_count < len(q_ids):
            q_ids = random.sample(q_ids, q_count)
        if test.get("shuffle_questions", True):
            random.shuffle(q_ids)
        time_per_q = test.get("time_per_question", DEFAULT_QUESTION_TIME)
        show_answers = test.get("show_answers", False)
    else:
        q_ids = daily_question_ids or []
        time_per_q = DEFAULT_QUESTION_TIME
        show_answers = False
        test = {"id": None, "shuffle_options": True, "show_answers": False,
                "time_per_question": time_per_q, "first_attempt_only": True,
                "show_explanations": False}

    prev_count = db.count_user_attempts(user_id, test_id or 0)
    is_first = prev_count == 0

    attempt_id = db.create_attempt(
        user_id=user_id,
        test_id=test_id or 0,
        question_order=q_ids,
        is_first=is_first,
        language=lang,
    )
    db.update_attempt(attempt_id, {"is_counted": 1})

    if daily_task_id:
        await state.update_data(daily_attempt_id=attempt_id, daily_task_id=daily_task_id)

    await send_question(message.bot, attempt_id, message.chat.id, test, lang)


async def send_question(bot: Bot, attempt_id: int, chat_id: int, test, lang: str = "ru") -> None:
    attempt = db.get_attempt(attempt_id)
    if not attempt or attempt["status"] != "active":
        return
    question_order = json.loads(attempt["question_order"])
    idx = attempt["current_question_index"]
    if idx >= len(question_order):
        await finish_attempt(bot, attempt_id, chat_id, test, lang)
        return
    qid = question_order[idx]
    question = db.get_question(qid)
    options = db.get_options(qid)
    if not question or not options:
        db.update_attempt(attempt_id, {
            "current_question_index": idx + 1,
            "skipped_answers": attempt["skipped_answers"] + 1,
        })
        await send_question(bot, attempt_id, chat_id, test, lang)
        return
    opts_list = list(options)
    if test.get("shuffle_options", True):
        random.shuffle(opts_list)
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    btns = [[InlineKeyboardButton(
        text=f"{chr(65+i)}) {o['text'][:60]}",
        callback_data=f"ans:{attempt_id}:{qid}:{o['id']}"
    )] for i, o in enumerate(opts_list)]
    kb = InlineKeyboardMarkup(inline_keyboard=btns)
    time_per_q = test.get("time_per_question", DEFAULT_QUESTION_TIME)
    text = (f"❓ Вопрос {idx+1}/{len(question_order)}\n\n"
            f"<b>{question['text']}</b>\n\n"
            f"⏱ {time_per_q} сек")
    if attempt_id in _q_message_ids:
        try:
            await bot.edit_message_reply_markup(chat_id, _q_message_ids[attempt_id], reply_markup=None)
        except Exception:
            pass
    try:
        msg = await bot.send_message(chat_id, text, reply_markup=kb, parse_mode="HTML", protect_content=True)
        _q_message_ids[attempt_id] = msg.message_id
    except TelegramBadRequest as e:
        logger.error("send_question error: %s", e)
        return
    db.update_attempt(attempt_id, {"pause_time": datetime.utcnow().isoformat()})
    if time_per_q:
        _cancel_timer(attempt_id)
        task = asyncio.create_task(_question_timer(bot, attempt_id, chat_id, test, lang, time_per_q))
        _timers[attempt_id] = task


async def _question_timer(bot: Bot, attempt_id: int, chat_id: int, test, lang: str, seconds: int) -> None:
    await asyncio.sleep(seconds)
    attempt = db.get_attempt(attempt_id)
    if not attempt or attempt["status"] != "active":
        return
    question_order = json.loads(attempt["question_order"])
    idx = attempt["current_question_index"]
    if idx >= len(question_order):
        return
    qid = question_order[idx]
    if db.has_answered(attempt_id, qid):
        return
    db.save_answer(attempt_id, qid, None, False, seconds * 1000, topic="")
    missed = attempt["missed_questions_counter"] + 1
    db.update_attempt(attempt_id, {
        "current_question_index": idx + 1,
        "skipped_answers": attempt["skipped_answers"] + 1,
        "missed_questions_counter": missed,
    })
    try:
        await bot.send_message(chat_id, "⏰ Время вышло!", protect_content=True)
    except Exception:
        pass
    if missed >= PAUSE_AFTER_MISSED:
        db.update_attempt(attempt_id, {"paused": 1, "missed_questions_counter": 0})
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="▶️ Продолжить", callback_data=f"pause:continue:{attempt_id}")],
            [InlineKeyboardButton(text="⏹ Завершить", callback_data=f"pause:finish:{attempt_id}")]
        ])
        try:
            await bot.send_message(chat_id, "⏸ Пауза! Вы пропустили несколько вопросов.", reply_markup=kb)
        except Exception:
            pass
        return
    await send_question(bot, attempt_id, chat_id, test, lang)


def _cancel_timer(attempt_id: int) -> None:
    task = _timers.pop(attempt_id, None)
    if task and not task.done():
        task.cancel()


async def handle_answer(bot: Bot, attempt_id: int, question_id: int,
                         option_id: int, chat_id: int, test) -> None:
    attempt = db.get_attempt(attempt_id)
    if not attempt or attempt["status"] != "active":
        return
    if db.has_answered(attempt_id, question_id):
        return
    _cancel_timer(attempt_id)
    start_iso = attempt.get("pause_time")
    start_ts = datetime.fromisoformat(start_iso) if start_iso else datetime.utcnow()
    ms = int((datetime.utcnow() - start_ts).total_seconds() * 1000)
    question = db.get_question(question_id)
    options = db.get_options(question_id)
    correct_opt = next((o for o in options if o["is_correct"]), None)
    is_correct = bool(correct_opt and correct_opt["id"] == option_id)
    db.save_answer(attempt_id, question_id, option_id, is_correct, ms,
                   topic=question["topic"] if question else "")
    attempt = db.get_attempt(attempt_id)
    lang = attempt.get("language", "ru")
    correct_n = attempt["correct_answers"] + (1 if is_correct else 0)
    wrong_n = attempt["wrong_answers"] + (0 if is_correct else 1)
    db.update_attempt(attempt_id, {
        "correct_answers": correct_n,
        "wrong_answers": wrong_n,
        "missed_questions_counter": 0,
        "current_question_index": attempt["current_question_index"] + 1,
    })
    feedback = "✅ Правильно!" if is_correct else "❌ Неверно!"
    if test.get("show_explanations") and question and question.get("explanation"):
        feedback += f"\n\n💡 {question['explanation']}"
    if attempt_id in _q_message_ids:
        try:
            await bot.edit_message_reply_markup(chat_id, _q_message_ids[attempt_id], reply_markup=None)
        except Exception:
            pass
    try:
        await bot.send_message(chat_id, feedback, parse_mode="HTML", protect_content=True)
    except Exception:
        pass
    await send_question(bot, attempt_id, chat_id, test, lang)


async def resume_attempt(bot: Bot, attempt_id: int, chat_id: int, test) -> None:
    attempt = db.get_attempt(attempt_id)
    if not attempt:
        return
    lang = attempt.get("language", "ru")
    db.update_attempt(attempt_id, {"paused": 0, "missed_questions_counter": 0})
    await send_question(bot, attempt_id, chat_id, test, lang)


async def finish_attempt(bot: Bot, attempt_id: int, chat_id: int, test, lang: str = "ru") -> None:
    _cancel_timer(attempt_id)
    attempt = db.get_attempt(attempt_id)
    if not attempt:
        return
    db.update_attempt(attempt_id, {
        "status": "finished",
        "end_time": datetime.utcnow().isoformat(),
    })
    correct = attempt["correct_answers"]
    wrong = attempt["wrong_answers"]
    skipped = attempt["skipped_answers"]
    total = correct + wrong + skipped
    pct = round(correct / total * 100, 1) if total else 0
    if pct >= 90:
        grade = "🏆 Отлично!"
    elif pct >= 70:
        grade = "✅ Хорошо!"
    elif pct >= 50:
        grade = "⚠️ Удовлетворительно"
    else:
        grade = "❌ Нужно повторить"
    text = (f"📊 <b>Результат</b>\n\n"
            f"✅ Правильных: {correct}\n"
            f"❌ Неправильных: {wrong}\n"
            f"⏭ Пропущено: {skipped}\n"
            f"📈 Результат: {pct}%\n\n"
            f"{grade}")
    try:
        await bot.send_message(chat_id, text, parse_mode="HTML", protect_content=True)
    except Exception as e:
        logger.error("finish_attempt: %s", e)
    weak_topics = db.get_weak_topics(attempt["user_id"], lang)
    if weak_topics:
        topics_str = "\n".join(f"  • {tp}" for tp in weak_topics[:5])
        try:
            await bot.send_message(chat_id,
                f"📚 Слабые темы — повторите:\n{topics_str}", protect_content=True)
        except Exception:
            pass
    asyncio.create_task(_check_achievements(bot, attempt["user_id"]))


async def _check_achievements(bot: Bot, user_id: int) -> None:
    try:
        stats = db.get_user_stats(user_id)
        mapping = {
            "first_test": stats.get("total_attempts", 0) >= 1,
            "test_10": stats.get("total_attempts", 0) >= 10,
            "test_50": stats.get("total_attempts", 0) >= 50,
        }
        for code, cond in mapping.items():
            if cond:
                granted = db.grant_achievement(user_id, code)
                if granted:
                    try:
                        await bot.send_message(user_id, f"🏅 Новое достижение: {code}!")
                    except Exception:
                        pass
    except Exception as e:
        logger.error("_check_achievements: %s", e)
