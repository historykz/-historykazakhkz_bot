import asyncio
import json
import logging
import random
import sqlite3
from datetime import datetime
from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
import database as db
from config import DB_PATH, DEFAULT_QUESTION_TIME

logger = logging.getLogger(__name__)

_timers = {}
_poll_message_ids = {}


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
    else:
        q_ids = daily_question_ids or []
        time_per_q = DEFAULT_QUESTION_TIME
        test = {"id": None, "shuffle_options": True,
                "time_per_question": time_per_q}

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

    if lang == "ru":
        await message.answer(
            f"🎯 <b>Тест начинается!</b>\n"
            f"Вопросов: {len(q_ids)}\n"
            f"Время на вопрос: {time_per_q} сек\n\n"
            f"Под каждым вопросом есть кнопки ⏸ и ⏹",
            parse_mode="HTML"
        )
    else:
        await message.answer(
            f"🎯 <b>Тест басталды!</b>\n"
            f"Сұрақ: {len(q_ids)}\n"
            f"Уақыт: {time_per_q} сек\n\n"
            f"Әр сұрақ астында ⏸ және ⏹ батырмалары бар",
            parse_mode="HTML"
        )

    await send_poll_question(message.bot, attempt_id, message.chat.id, test, lang)


async def send_poll_question(bot: Bot, attempt_id: int, chat_id: int,
                              test, lang: str = "ru") -> None:
    attempt = db.get_attempt(attempt_id)
    if not attempt or attempt["status"] != "active":
        return
    if attempt.get("paused"):
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
        await send_poll_question(bot, attempt_id, chat_id, test, lang)
        return

    opts_list = list(options)
    if test.get("shuffle_options", True):
        random.shuffle(opts_list)

    correct_idx = next((i for i, o in enumerate(opts_list) if o["is_correct"]), 0)
    option_texts = [o["text"][:100] for o in opts_list]

    time_per_q = test.get("time_per_question", DEFAULT_QUESTION_TIME)
    question_text = f"❓ {idx+1}/{len(question_order)}\n\n{question['text']}"
    if len(question_text) > 300:
        question_text = question_text[:297] + "..."

    try:
        msg = await bot.send_poll(
            chat_id=chat_id,
            question=question_text,
            options=option_texts,
            type="quiz",
            correct_option_id=correct_idx,
            is_anonymous=False,
            open_period=time_per_q,
            protect_content=True,
            explanation=question.get("explanation") or None,
        )
        _poll_message_ids[attempt_id] = {
            "message_id": msg.message_id,
            "poll_id": msg.poll.id,
            "question_id": qid,
            "correct_idx": correct_idx,
            "opts": opts_list,
            "chat_id": chat_id,
        }
    except Exception as e:
        logger.error("send_poll error: %s", e)
        await bot.send_message(chat_id, f"❌ Ошибка: {e}")
        return

    db.update_attempt(attempt_id, {"pause_time": datetime.utcnow().isoformat()})

    # Кнопки паузы и завершения
    pause_text = "⏸ Пауза" if lang == "ru" else "⏸ Үзіліс"
    finish_text = "⏹ Завершить" if lang == "ru" else "⏹ Аяқтау"
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=pause_text, callback_data=f"tp_{attempt_id}"),
        InlineKeyboardButton(text=finish_text, callback_data=f"tf_{attempt_id}"),
    ]])
    try:
        await bot.send_message(chat_id, "⏱", reply_markup=kb)
    except Exception:
        pass

    # Таймер авто-переход
    _cancel_timer(attempt_id)
    task = asyncio.create_task(
        _poll_timer(bot, attempt_id, chat_id, test, lang, qid, time_per_q + 2)
    )
    _timers[attempt_id] = task


async def _poll_timer(bot: Bot, attempt_id: int, chat_id: int, test,
                      lang: str, question_id: int, seconds: int) -> None:
    await asyncio.sleep(seconds)
    attempt = db.get_attempt(attempt_id)
    if not attempt or attempt["status"] != "active":
        return
    if attempt.get("paused"):
        return
    if db.has_answered(attempt_id, question_id):
        return
    db.save_answer(attempt_id, question_id, None, False, seconds * 1000, topic="")
    db.update_attempt(attempt_id, {
        "current_question_index": attempt["current_question_index"] + 1,
        "skipped_answers": attempt["skipped_answers"] + 1,
    })
    await send_poll_question(bot, attempt_id, chat_id, test, lang)


def _cancel_timer(attempt_id: int) -> None:
    task = _timers.pop(attempt_id, None)
    if task and not task.done():
        task.cancel()


async def handle_poll_answer(bot: Bot, poll_id: str, user_id: int,
                              option_id: int, chat_id: int) -> None:
    attempt_id = None
    poll_data = None
    for aid, data in list(_poll_message_ids.items()):
        if data.get("poll_id") == poll_id:
            attempt_id = aid
            poll_data = data
            break

    if not attempt_id or not poll_data:
        return

    attempt = db.get_attempt(attempt_id)
    if not attempt or attempt["status"] != "active":
        return
    if attempt["user_id"] != user_id:
        return
    if attempt.get("paused"):
        return

    question_id = poll_data["question_id"]
    if db.has_answered(attempt_id, question_id):
        return

    _cancel_timer(attempt_id)

    correct_idx = poll_data["correct_idx"]
    is_correct = (option_id == correct_idx)
    opts = poll_data["opts"]
    chosen_opt = opts[option_id] if option_id < len(opts) else None
    chosen_id = chosen_opt["id"] if chosen_opt else None

    start_iso = attempt.get("pause_time")
    start_ts = datetime.fromisoformat(start_iso) if start_iso else datetime.utcnow()
    ms = int((datetime.utcnow() - start_ts).total_seconds() * 1000)

    question = db.get_question(question_id)
    db.save_answer(attempt_id, question_id, chosen_id, is_correct, ms,
                   topic=question.get("topic", "") if question else "")

    db.update_attempt(attempt_id, {
        "correct_answers": attempt["correct_answers"] + (1 if is_correct else 0),
        "wrong_answers": attempt["wrong_answers"] + (0 if is_correct else 1),
        "missed_questions_counter": 0,
        "current_question_index": attempt["current_question_index"] + 1,
    })

    _poll_message_ids.pop(attempt_id, None)

    await asyncio.sleep(1.5)
    attempt = db.get_attempt(attempt_id)
    if not attempt or attempt.get("paused"):
        return

    lang = attempt.get("language", "ru")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    test_row = conn.execute("SELECT * FROM tests WHERE id=?", (attempt["test_id"],)).fetchone()
    conn.close()
    test = dict(test_row) if test_row else {}

    await send_poll_question(bot, attempt_id, chat_id, test, lang)


async def handle_answer(bot: Bot, attempt_id: int, question_id: int,
                         option_id: int, chat_id: int, test) -> None:
    attempt = db.get_attempt(attempt_id)
    if not attempt:
        return
    lang = attempt.get("language", "ru")
    await finish_attempt(bot, attempt_id, chat_id, test, lang)


async def resume_attempt(bot: Bot, attempt_id: int, chat_id: int, test) -> None:
    attempt = db.get_attempt(attempt_id)
    if not attempt:
        return
    lang = attempt.get("language", "ru")
    db.update_attempt(attempt_id, {"paused": 0, "missed_questions_counter": 0})
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    test_row = conn.execute("SELECT * FROM tests WHERE id=?", (attempt["test_id"],)).fetchone()
    conn.close()
    test = dict(test_row) if test_row else test
    await send_poll_question(bot, attempt_id, chat_id, test, lang)


async def finish_attempt(bot: Bot, attempt_id: int, chat_id: int,
                          test, lang: str = "ru") -> None:
    _cancel_timer(attempt_id)
    _poll_message_ids.pop(attempt_id, None)

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
        grade = "🏆 Отлично!" if lang == "ru" else "🏆 Өте жақсы!"
    elif pct >= 70:
        grade = "✅ Хорошо!" if lang == "ru" else "✅ Жақсы!"
    elif pct >= 50:
        grade = "⚠️ Удовлетворительно" if lang == "ru" else "⚠️ Қанағаттанарлық"
    else:
        grade = "❌ Нужно повторить" if lang == "ru" else "❌ Қайталау керек"

    if lang == "ru":
        text = (
            f"📊 <b>Результат теста</b>\n\n"
            f"✅ Правильных: {correct}\n"
            f"❌ Неправильных: {wrong}\n"
            f"⏭ Пропущено: {skipped}\n"
            f"📈 Результат: {pct}%\n\n"
            f"{grade}"
        )
    else:
        text = (
            f"📊 <b>Тест нәтижесі</b>\n\n"
            f"✅ Дұрыс: {correct}\n"
            f"❌ Қате: {wrong}\n"
            f"⏭ Өткізілді: {skipped}\n"
            f"📈 Нәтиже: {pct}%\n\n"
            f"{grade}"
        )

    try:
        await bot.send_message(chat_id, text, parse_mode="HTML")
    except Exception as e:
        logger.error("finish_attempt: %s", e)

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
                        await bot.send_message(user_id, f"🏅 Новое достижение!")
                    except Exception:
                        pass
    except Exception as e:
        logger.error("_check_achievements: %s", e)
