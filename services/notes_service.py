import logging
import sqlite3
from config import DB_PATH
import database as db

logger = logging.getLogger(__name__)
NOTE_PAGE_MAX_CHARS = 800


def split_content_to_pages(content: str) -> list:
    pages = []
    while len(content) > NOTE_PAGE_MAX_CHARS:
        split_at = content.rfind("\n", 0, NOTE_PAGE_MAX_CHARS)
        if split_at < 0:
            split_at = NOTE_PAGE_MAX_CHARS
        pages.append(content[:split_at].strip())
        content = content[split_at:].strip()
    if content:
        pages.append(content)
    return pages


def check_note_access(user_id: int, note_id: int) -> str:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    note = conn.execute("SELECT * FROM notes WHERE id=?", (note_id,)).fetchone()
    conn.close()
    if not note:
        return "ok"
    if not note["is_paid"] and not note["is_premium"]:
        return "ok"
    if note["is_premium"]:
        if db.has_premium(user_id):
            return "ok"
        return "premium"
    if note["is_paid"]:
        if db.has_note_access(user_id, note_id):
            return "ok"
        return "paid"
    return "ok"


def auto_check_hw(user_answer: str, keywords: str) -> tuple:
    if not keywords:
        return 5.0, "Автопроверка не настроена."
    kws = [k.strip().lower() for k in keywords.split(",") if k.strip()]
    answer_lower = user_answer.lower()
    found = sum(1 for k in kws if k in answer_lower)
    score = round(found / len(kws) * 10, 1) if kws else 5.0
    missing = [k for k in kws if k not in answer_lower]
    comment = f"Не упомянуты: {', '.join(missing[:3])}" if missing else "Отличный ответ!"
    return score, comment
