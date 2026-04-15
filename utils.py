"""utils.py — shared utility helpers."""
import random
import json
import logging
from datetime import datetime
from typing import Optional
from aiogram import Bot
from aiogram.types import Message
from aiogram.exceptions import TelegramBadRequest

logger = logging.getLogger(__name__)


def shuffle_list(lst: list) -> list:
    out = list(lst)
    random.shuffle(out)
    return out


def compute_level(pct: float, lang: str) -> str:
    from locales import get_text as t
    if pct >= 85:
        return t("level_excellent", lang)
    elif pct >= 70:
        return t("level_above_avg", lang)
    elif pct >= 55:
        return t("level_average", lang)
    elif pct >= 40:
        return t("level_below_avg", lang)
    else:
        return t("level_low", lang)


def format_result_text(lang: str, correct: int, wrong: int, skipped: int,
                        score: int, attempt_num: int, is_counted: bool,
                        rank: int, weak_topics: list) -> str:
    from locales import get_text as t
    total = correct + wrong + skipped
    pct = round(correct / total * 100, 1) if total else 0
    level = compute_level(pct, lang)
    lines = [
        t("test_result_title", lang),
        t("result_correct", lang, n=correct),
        t("result_wrong",   lang, n=wrong),
        t("result_skipped", lang, n=skipped),
        t("result_score",   lang, score=score),
        t("result_percent", lang, pct=pct),
        t("result_level",   lang, level=level),
        t("result_attempt_num", lang, n=attempt_num),
        t("result_counted", lang) if is_counted else t("result_not_counted", lang),
    ]
    if rank > 0:
        lines.append(t("result_rank", lang, rank=rank))
    if weak_topics:
        topics_str = "\n".join(f"  • {tp}" for tp in weak_topics)
        lines.append(t("result_weak_topics", lang, topics=topics_str))
    return "\n".join(lines)


def build_test_card_text(test, lang: str) -> str:
    """Build a human-readable test card."""
    lines = [
        f"📚 <b>{test['title']}</b>",
        f"📝 {test['description']}" if test['description'] else "",
        f"🔹 Предмет: {test['subject_id'] or '—'}",
        f"🔹 Класс: {test['class_num']}",
        f"🔹 Категория: {test['category_id'] or '—'}",
        f"🔹 Язык: {'🇷🇺 Русский' if test['language']=='ru' else '🇰🇿 Қазақша'}",
        f"🔹 Тип: {test['test_type']}",
        f"❓ Вопросов: {test['question_count'] or 'все'}",
        f"⏱ Время на вопрос: {test['question_time_sec']} сек",
    ]
    if test['is_paid']:
        lines.append(f"💰 Платный: {test['price']} тенге")
    if test['deadline']:
        lines.append(f"📅 Дедлайн: {test['deadline']}")
    return "\n".join(l for l in lines if l)


def build_note_card_text(note, lang: str) -> str:
    paid_label = "🆓 Бесплатный"
    if note["is_premium"]:
        paid_label = "👑 Premium"
    elif note["is_paid"]:
        paid_label = f"💰 Платный ({note['price']} тенге)"
    lines = [
        f"📖 <b>{note['title']}</b>",
        f"{note['description']}" if note['description'] else "",
        f"🔹 Язык: {'🇷🇺' if note['language']=='ru' else '🇰🇿'}",
        paid_label,
    ]
    return "\n".join(l for l in lines if l)


async def safe_delete(bot: Bot, chat_id: int, message_id: int) -> None:
    try:
        await bot.delete_message(chat_id, message_id)
    except TelegramBadRequest:
        pass


async def safe_edit_text(message: Message, text: str, **kwargs) -> None:
    try:
        await message.edit_text(text, **kwargs)
    except TelegramBadRequest:
        pass


def parse_text_questions(raw: str) -> tuple[list, list]:
    """
    Parse multiple questions from raw text.
    Returns (questions_list, errors_list).
    Each question: {text, options: [(letter, text)], correct_idx}
    """
    import re
    questions = []
    errors = []
    # Split by blank line between questions
    blocks = re.split(r"\n\s*\n", raw.strip())

    # merge single-line blocks that got split incorrectly
    merged: list[str] = []
    buf = ""
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        # check if block has option lines
        lines = block.splitlines()
        has_options = any(re.match(r"^[ABCDАБВГabcdабвг][).]", l.strip()) for l in lines)
        if not has_options and buf:
            buf += "\n\n" + block
        else:
            if buf:
                merged.append(buf)
            buf = block
    if buf:
        merged.append(buf)

    for block in merged:
        lines = [l.strip() for l in block.splitlines() if l.strip()]
        if len(lines) < 3:
            errors.append(f"Слишком мало строк: {block[:60]}")
            continue

        question_text = lines[0]
        options = []
        correct_idx = -1
        opt_pattern = re.compile(
            r"^([ABCDabcdАБВГабвг])[).]\s*(.+)$"
        )
        for line in lines[1:]:
            is_correct = line.endswith("*")
            clean_line = line.rstrip("* ").strip()
            m = opt_pattern.match(clean_line)
            if m:
                opt_text = m.group(2).strip()
                options.append(opt_text)
                if is_correct:
                    correct_idx = len(options) - 1
            else:
                # try without letter prefix (rare)
                errors.append(f"Не распознана опция: {line[:60]}")

        if len(options) < 2:
            errors.append(f"Мало вариантов: {question_text[:60]}")
            continue
        if correct_idx < 0:
            errors.append(f"Нет правильного ответа (*): {question_text[:60]}")
            continue
        if correct_idx >= len(options):
            errors.append(f"Ошибка индекса правильного ответа: {question_text[:60]}")
            continue

        questions.append({
            "text": question_text,
            "options": options,
            "correct_idx": correct_idx,
        })

    return questions, errors


def today_str() -> str:
    return datetime.utcnow().date().isoformat()
