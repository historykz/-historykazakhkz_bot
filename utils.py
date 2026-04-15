import random
import logging
from datetime import datetime
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest

logger = logging.getLogger(__name__)


def shuffle_list(lst: list) -> list:
    out = list(lst)
    random.shuffle(out)
    return out


def compute_level(pct: float, lang: str = "ru") -> str:
    if pct >= 85:
        return "🏆 Отлично" if lang == "ru" else "🏆 Өте жақсы"
    elif pct >= 70:
        return "✅ Хорошо" if lang == "ru" else "✅ Жақсы"
    elif pct >= 55:
        return "📊 Средне" if lang == "ru" else "📊 Орташа"
    elif pct >= 40:
        return "⚠️ Ниже среднего" if lang == "ru" else "⚠️ Орташадан төмен"
    else:
        return "❌ Нужно повторить" if lang == "ru" else "❌ Қайталау керек"


def format_result_text(lang: str, correct: int, wrong: int, skipped: int,
                        score=0, attempt_num=1, is_counted=True,
                        rank=0, weak_topics=None) -> str:
    total = correct + wrong + skipped
    pct = round(correct / total * 100, 1) if total else 0
    level = compute_level(pct, lang)
    if lang == "ru":
        text = (
            f"📊 <b>Результат теста</b>\n\n"
            f"✅ Правильных: {correct}\n"
            f"❌ Неправильных: {wrong}\n"
            f"⏭ Пропущено: {skipped}\n"
            f"📈 Результат: {pct}%\n"
            f"🎯 Уровень: {level}\n"
            f"🔢 Попытка: #{attempt_num}\n"
        )
        if not is_counted:
            text += "ℹ️ Попытка не засчитана в рейтинг\n"
        if rank > 0:
            text += f"🏅 Ваше место: #{rank}\n"
        if weak_topics:
            topics_str = "\n".join(f"  • {tp}" for tp in weak_topics[:5])
            text += f"\n📚 Слабые темы:\n{topics_str}"
    else:
        text = (
            f"📊 <b>Тест нәтижесі</b>\n\n"
            f"✅ Дұрыс: {correct}\n"
            f"❌ Қате: {wrong}\n"
            f"⏭ Өткізілді: {skipped}\n"
            f"📈 Нәтиже: {pct}%\n"
            f"🎯 Деңгей: {level}\n"
            f"🔢 Әрекет: #{attempt_num}\n"
        )
        if rank > 0:
            text += f"🏅 Орыныңыз: #{rank}\n"
    return text


def build_test_card_text(test, lang: str) -> str:
    lines = [
        f"📚 <b>{test.get('title', '')}</b>",
        f"📝 {test.get('description', '')}" if test.get('description') else "",
        f"🔹 Предмет: {test.get('subject') or '—'}",
        f"🔹 Категория: {test.get('category') or '—'}",
        f"🔹 Язык: {'🇷🇺 Русский' if test.get('language') == 'ru' else '🇰🇿 Қазақша'}",
        f"🔹 Тип: {test.get('test_type', '')}",
        f"❓ Вопросов: {test.get('question_count') or 'все'}",
        f"⏰ Время на вопрос: {test.get('time_per_question', 30)} сек",
    ]
    if test.get('is_paid'):
        lines.append(f"💰 Платный: {test.get('price', 0)} тенге")
    if test.get('deadline'):
        lines.append(f"📅 Дедлайн: {test.get('deadline')}")
    return "\n".join(l for l in lines if l)


def build_note_card_text(note, lang: str) -> str:
    paid_label = "🆓 Бесплатный" if lang == "ru" else "🆓 Тегін"
    if note.get("is_premium"):
        paid_label = "👑 Premium"
    elif note.get("is_paid"):
        paid_label = f"💰 Платный ({note.get('price', 0)} тенге)"
    lines = [
        f"📖 <b>{note.get('title', '')}</b>",
        f"{note.get('description', '')}" if note.get('description') else "",
        f"🔹 Предмет: {note.get('subject') or '—'}",
        f"🔹 Язык: {'🇷🇺' if note.get('language') == 'ru' else '🇰🇿'}",
        paid_label,
    ]
    return "\n".join(l for l in lines if l)


async def safe_delete(bot: Bot, chat_id: int, message_id: int) -> None:
    try:
        await bot.delete_message(chat_id, message_id)
    except TelegramBadRequest:
        pass


def parse_text_questions(raw: str) -> tuple:
    import re
    questions = []
    errors = []
    blocks = re.split(r"\n\s*\n", raw.strip())
    merged = []
    buf = ""
    for block in blocks:
        block = block.strip()
        if not block:
            continue
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
            errors.append(f"Мало строк: {block[:60]}")
            continue
        question_text = lines[0]
        options = []
        correct_idx = -1
        opt_pattern = re.compile(r"^([ABCDabcdАБВГабвг])[).]\s*(.+)$")
        for line in lines[1:]:
            is_correct = line.endswith("*")
            clean_line = line.rstrip("* ").strip()
            m = opt_pattern.match(clean_line)
            if m:
                opt_text = m.group(2).strip()
                options.append({"text": opt_text, "is_correct": is_correct})
                if is_correct:
                    correct_idx = len(options) - 1
        if len(options) < 2:
            errors.append(f"Мало вариантов: {question_text[:60]}")
            continue
        if correct_idx < 0:
            errors.append(f"Нет правильного ответа (*): {question_text[:60]}")
            continue
        questions.append({"text": question_text, "options": options})
    return questions, errors


def today_str() -> str:
    return datetime.utcnow().date().isoformat()
