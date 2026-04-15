import json
import random
import logging
import sqlite3
from utils import today_str
from config import DB_PATH

logger = logging.getLogger(__name__)
DEFAULT_COUNT = 10


def get_or_create_daily_task(language: str) -> dict:
    today = today_str()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    task = conn.execute(
        "SELECT * FROM daily_tasks WHERE task_date=? AND language=?",
        (today, language)
    ).fetchone()

    if task:
        conn.close()
        return dict(task)

    count = DEFAULT_COUNT
    try:
        setting = conn.execute(
            "SELECT value FROM settings WHERE key='daily_question_count'"
        ).fetchone()
        if setting:
            count = int(setting["value"])
    except Exception:
        pass

    rows = conn.execute("""
        SELECT q.id FROM questions q
        JOIN tests t ON t.id=q.test_id
        WHERE t.language=? AND t.allow_daily=1 AND t.status='active'
        ORDER BY RANDOM() LIMIT ?
    """, (language, count * 3)).fetchall()

    if not rows:
        conn.close()
        return {"id": 0, "question_count": 0, "question_ids": "[]", "subject": "Смешанный"}

    ids = [r["id"] for r in rows]
    random.shuffle(ids)
    ids = ids[:count]

    conn.execute(
        "INSERT INTO daily_tasks (task_date, language, question_ids, question_count) VALUES (?,?,?,?)",
        (today, language, json.dumps(ids), len(ids))
    )
    conn.commit()

    task = conn.execute(
        "SELECT * FROM daily_tasks WHERE task_date=? AND language=?",
        (today, language)
    ).fetchone()
    conn.close()
    return dict(task) if task else {"id": 0, "question_count": count, "question_ids": json.dumps(ids)}


def user_completed_today(user_id: int, language: str = "ru") -> bool:
    today = today_str()
    conn = sqlite3.connect(DB_PATH)
    result = conn.execute(
        "SELECT id FROM daily_results WHERE user_id=? AND task_date=?",
        (user_id, today)
    ).fetchone()
    conn.close()
    return result is not None
