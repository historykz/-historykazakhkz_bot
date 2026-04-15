import sqlite3
import json
import logging
from datetime import datetime
from config import DB_PATH

logger = logging.getLogger(__name__)


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = get_conn()
    conn.executescript("""
CREATE TABLE IF NOT EXISTS users (
    telegram_id  INTEGER PRIMARY KEY,
    username     TEXT,
    full_name    TEXT,
    language     TEXT DEFAULT 'ru',
    is_blocked   INTEGER DEFAULT 0,
    created_at   TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS blocked_users (
    telegram_id INTEGER PRIMARY KEY,
    reason TEXT,
    blocked_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS tests (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    subject TEXT DEFAULT '',
    grade TEXT DEFAULT '',
    category TEXT DEFAULT '',
    language TEXT DEFAULT 'ru',
    test_type TEXT DEFAULT 'regular',
    status TEXT DEFAULT 'active',
    is_paid INTEGER DEFAULT 0,
    price INTEGER DEFAULT 0,
    question_count INTEGER DEFAULT 0,
    attempt_limit INTEGER DEFAULT 0,
    first_attempt_only INTEGER DEFAULT 1,
    deadline TEXT,
    shuffle_questions INTEGER DEFAULT 1,
    shuffle_options INTEGER DEFAULT 1,
    show_answers INTEGER DEFAULT 0,
    show_explanations INTEGER DEFAULT 0,
    time_per_question INTEGER DEFAULT 30,
    require_subscription INTEGER DEFAULT 0,
    allow_group INTEGER DEFAULT 1,
    allow_duel INTEGER DEFAULT 0,
    allow_daily INTEGER DEFAULT 0,
    allow_tournament INTEGER DEFAULT 0,
    question_mode TEXT DEFAULT 'inline',
    created_by INTEGER,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS questions (
    id INTEGER PRIMARY KEY,
    test_id INTEGER REFERENCES tests(id) ON DELETE CASCADE,
    text TEXT NOT NULL,
    explanation TEXT DEFAULT '',
    topic TEXT DEFAULT '',
    difficulty INTEGER DEFAULT 1,
    points REAL DEFAULT 1.0,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS question_options (
    id INTEGER PRIMARY KEY,
    question_id INTEGER REFERENCES questions(id) ON DELETE CASCADE,
    text TEXT NOT NULL,
    is_correct INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS test_attempts (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    test_id INTEGER,
    current_question_index INTEGER DEFAULT 0,
    question_order TEXT DEFAULT '[]',
    correct_answers INTEGER DEFAULT 0,
    wrong_answers INTEGER DEFAULT 0,
    skipped_answers INTEGER DEFAULT 0,
    score REAL DEFAULT 0,
    start_time TEXT DEFAULT (datetime('now')),
    end_time TEXT,
    status TEXT DEFAULT 'active',
    paused INTEGER DEFAULT 0,
    missed_questions_counter INTEGER DEFAULT 0,
    pause_time TEXT,
    is_counted INTEGER DEFAULT 0,
    is_first_attempt INTEGER DEFAULT 0,
    attempt_number INTEGER DEFAULT 1,
    language TEXT DEFAULT 'ru',
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS attempt_answers (
    id INTEGER PRIMARY KEY,
    attempt_id INTEGER,
    question_id INTEGER,
    selected_option_id INTEGER,
    is_correct INTEGER DEFAULT 0,
    response_time_ms INTEGER DEFAULT 0,
    topic TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS paid_access (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    test_id INTEGER,
    note_id INTEGER,
    granted_by INTEGER,
    granted_at TEXT DEFAULT (datetime('now')),
    expires_at TEXT
);
CREATE TABLE IF NOT EXISTS premium_users (
    id INTEGER PRIMARY KEY,
    user_id INTEGER UNIQUE,
    granted_at TEXT DEFAULT (datetime('now')),
    expires_at TEXT,
    granted_by INTEGER
);
CREATE TABLE IF NOT EXISTS required_channels (
    id INTEGER PRIMARY KEY,
    channel_username TEXT,
    title TEXT DEFAULT '',
    is_global INTEGER DEFAULT 0,
    test_id INTEGER,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    subject TEXT DEFAULT '',
    category TEXT DEFAULT '',
    language TEXT DEFAULT 'ru',
    topic TEXT DEFAULT '',
    difficulty INTEGER DEFAULT 1,
    is_paid INTEGER DEFAULT 0,
    price INTEGER DEFAULT 0,
    is_premium INTEGER DEFAULT 0,
    created_by_admin INTEGER,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS note_pages (
    id INTEGER PRIMARY KEY,
    note_id INTEGER REFERENCES notes(id) ON DELETE CASCADE,
    page_number INTEGER,
    content TEXT
);
CREATE TABLE IF NOT EXISTS note_homeworks (
    id INTEGER PRIMARY KEY,
    note_id INTEGER,
    homework_type TEXT DEFAULT 'open',
    test_id INTEGER,
    open_task_prompt TEXT DEFAULT '',
    auto_check_enabled INTEGER DEFAULT 0,
    keywords TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS user_notes_progress (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    note_id INTEGER,
    last_page INTEGER DEFAULT 0,
    completed INTEGER DEFAULT 0,
    homework_completed INTEGER DEFAULT 0,
    hw_score REAL DEFAULT 0,
    hw_answer_text TEXT DEFAULT '',
    UNIQUE(user_id, note_id)
);
CREATE TABLE IF NOT EXISTS hw_answers (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    homework_id INTEGER,
    answer_text TEXT,
    score REAL,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS daily_tasks (
    id INTEGER PRIMARY KEY,
    task_date TEXT,
    language TEXT DEFAULT 'ru',
    question_ids TEXT DEFAULT '[]',
    question_count INTEGER DEFAULT 10,
    subject TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(task_date, language)
);
CREATE TABLE IF NOT EXISTS daily_results (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    task_date TEXT,
    correct_answers INTEGER DEFAULT 0,
    wrong_answers INTEGER DEFAULT 0,
    skipped_answers INTEGER DEFAULT 0,
    percentage REAL DEFAULT 0,
    streak INTEGER DEFAULT 0,
    best_streak INTEGER DEFAULT 0,
    completed_at TEXT DEFAULT (datetime('now')),
    UNIQUE(user_id, task_date)
);
CREATE TABLE IF NOT EXISTS duels (
    id INTEGER PRIMARY KEY,
    player1_id INTEGER,
    player2_id INTEGER,
    subject TEXT DEFAULT '',
    language TEXT DEFAULT 'ru',
    question_ids TEXT DEFAULT '[]',
    status TEXT DEFAULT 'searching',
    winner_id INTEGER,
    created_at TEXT DEFAULT (datetime('now')),
    started_at TEXT,
    finished_at TEXT
);
CREATE TABLE IF NOT EXISTS duel_answers (
    id INTEGER PRIMARY KEY,
    duel_id INTEGER,
    user_id INTEGER,
    question_id INTEGER,
    selected_option INTEGER,
    is_correct INTEGER DEFAULT 0,
    response_time_ms INTEGER DEFAULT 0,
    score INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(duel_id, user_id, question_id)
);
CREATE TABLE IF NOT EXISTS group_quizzes (
    id INTEGER PRIMARY KEY,
    test_id INTEGER,
    group_id INTEGER,
    started_by INTEGER,
    status TEXT DEFAULT 'waiting',
    current_q_index INTEGER DEFAULT 0,
    question_order TEXT DEFAULT '[]',
    paused INTEGER DEFAULT 0,
    missed_counter INTEGER DEFAULT 0,
    started_at TEXT,
    finished_at TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS group_quiz_participants (
    id INTEGER PRIMARY KEY,
    quiz_id INTEGER,
    user_id INTEGER,
    score INTEGER DEFAULT 0,
    UNIQUE(quiz_id, user_id)
);
CREATE TABLE IF NOT EXISTS group_quiz_answers (
    id INTEGER PRIMARY KEY,
    quiz_id INTEGER,
    question_id INTEGER,
    user_id INTEGER,
    is_correct INTEGER DEFAULT 0,
    answered_at TEXT DEFAULT (datetime('now')),
    UNIQUE(quiz_id, user_id, question_id)
);
CREATE TABLE IF NOT EXISTS tournaments (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    test_id INTEGER,
    start_date TEXT,
    end_date TEXT,
    prize TEXT DEFAULT '',
    status TEXT DEFAULT 'active',
    created_by INTEGER,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS tournament_results (
    id INTEGER PRIMARY KEY,
    tournament_id INTEGER,
    user_id INTEGER,
    score INTEGER DEFAULT 0,
    percentage REAL DEFAULT 0,
    attempt_id INTEGER,
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(tournament_id, user_id)
);
CREATE TABLE IF NOT EXISTS achievements (
    id INTEGER PRIMARY KEY,
    code TEXT UNIQUE,
    name_ru TEXT,
    name_kz TEXT
);
CREATE TABLE IF NOT EXISTS user_achievements (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    achievement_key TEXT,
    earned_at TEXT DEFAULT (datetime('now')),
    UNIQUE(user_id, achievement_key)
);
CREATE TABLE IF NOT EXISTS referrals (
    id INTEGER PRIMARY KEY,
    referrer_id INTEGER,
    referred_id INTEGER UNIQUE,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS imported_polls (
    id INTEGER PRIMARY KEY,
    test_id INTEGER,
    poll_id TEXT,
    question_text TEXT,
    raw_options TEXT DEFAULT '[]',
    correct_option_id INTEGER DEFAULT -1,
    needs_manual INTEGER DEFAULT 0,
    imported_by INTEGER,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
);
""")
    conn.commit()
    conn.close()
    logger.info("Database initialised.")


# ── Users ──────────────────────────────────────────

def upsert_user(telegram_id: int, username: str, full_name: str):
    conn = get_conn()
    conn.execute("""
        INSERT INTO users(telegram_id, username, full_name)
        VALUES(?,?,?)
        ON CONFLICT(telegram_id) DO UPDATE SET
            username=excluded.username,
            full_name=excluded.full_name
    """, (telegram_id, username, full_name))
    conn.commit()
    conn.close()


def get_user(telegram_id: int):
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE telegram_id=?", (telegram_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def set_user_language(telegram_id: int, lang: str):
    conn = get_conn()
    conn.execute("UPDATE users SET language=? WHERE telegram_id=?", (lang, telegram_id))
    conn.commit()
    conn.close()


def get_user_language(telegram_id: int) -> str:
    user = get_user(telegram_id)
    return user.get("language", "ru") if user else "ru"


def is_blocked(telegram_id: int) -> bool:
    conn = get_conn()
    row = conn.execute("SELECT 1 FROM blocked_users WHERE telegram_id=?", (telegram_id,)).fetchone()
    conn.close()
    return row is not None


def block_user(telegram_id: int):
    conn = get_conn()
    conn.execute("INSERT OR IGNORE INTO blocked_users(telegram_id) VALUES(?)", (telegram_id,))
    conn.commit()
    conn.close()


def unblock_user(telegram_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM blocked_users WHERE telegram_id=?", (telegram_id,))
    conn.commit()
    conn.close()


def is_admin(telegram_id: int) -> bool:
    from config import ADMIN_IDS
    return telegram_id in ADMIN_IDS


# ── Premium ────────────────────────────────────────

def has_premium(telegram_id: int) -> bool:
    conn = get_conn()
    row = conn.execute("SELECT expires_at FROM premium_users WHERE user_id=?", (telegram_id,)).fetchone()
    conn.close()
    if not row:
        return False
    if row["expires_at"] is None:
        return True
    return datetime.fromisoformat(row["expires_at"]) > datetime.utcnow()


def grant_premium(telegram_id: int, granted_by: int, expires_at=None):
    conn = get_conn()
    conn.execute("""
        INSERT INTO premium_users(user_id, granted_by, expires_at)
        VALUES(?,?,?)
        ON CONFLICT(user_id) DO UPDATE SET
            granted_at=datetime('now'), expires_at=excluded.expires_at,
            granted_by=excluded.granted_by
    """, (telegram_id, granted_by, expires_at))
    conn.commit()
    conn.close()


def revoke_premium(telegram_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM premium_users WHERE user_id=?", (telegram_id,))
    conn.commit()
    conn.close()


# ── Access ─────────────────────────────────────────

def has_test_access(telegram_id: int, test_id: int) -> bool:
    if has_premium(telegram_id):
        return True
    conn = get_conn()
    row = conn.execute(
        "SELECT 1 FROM paid_access WHERE user_id=? AND test_id=? AND (expires_at IS NULL OR expires_at > datetime('now'))",
        (telegram_id, test_id)
    ).fetchone()
    conn.close()
    return row is not None


def grant_test_access(telegram_id: int, test_id: int, granted_by: int = 0):
    conn = get_conn()
    conn.execute("INSERT INTO paid_access(user_id, test_id, granted_by) VALUES(?,?,?)",
                 (telegram_id, test_id, granted_by))
    conn.commit()
    conn.close()


def has_note_access(telegram_id: int, note_id: int) -> bool:
    if has_premium(telegram_id):
        return True
    conn = get_conn()
    row = conn.execute(
        "SELECT 1 FROM paid_access WHERE user_id=? AND note_id=? AND (expires_at IS NULL OR expires_at > datetime('now'))",
        (telegram_id, note_id)
    ).fetchone()
    conn.close()
    return row is not None


def grant_note_access(telegram_id: int, note_id: int, granted_by: int = 0):
    conn = get_conn()
    conn.execute("INSERT INTO paid_access(user_id, note_id, granted_by) VALUES(?,?,?)",
                 (telegram_id, note_id, granted_by))
    conn.commit()
    conn.close()


# ── Tests ──────────────────────────────────────────

def create_test(**kwargs) -> int:
    cols = ", ".join(kwargs.keys())
    phs = ", ".join("?" for _ in kwargs)
    conn = get_conn()
    cur = conn.execute(f"INSERT INTO tests({cols}) VALUES({phs})", list(kwargs.values()))
    test_id = cur.lastrowid
    conn.commit()
    conn.close()
    return test_id


def get_test(test_id: int):
    conn = get_conn()
    row = conn.execute("SELECT * FROM tests WHERE id=?", (test_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def list_tests(language=None, test_type=None, status_filter="active",
               limit=50, offset=0):
    clauses = ["status=?"]
    params = [status_filter]
    if language:
        clauses.append("language=?")
        params.append(language)
    if test_type:
        clauses.append("test_type=?")
        params.append(test_type)
    where = " AND ".join(clauses)
    params += [limit, offset]
    conn = get_conn()
    rows = conn.execute(
        f"SELECT * FROM tests WHERE {where} ORDER BY id DESC LIMIT ? OFFSET ?",
        params
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_test(test_id: int, **kwargs):
    sets = ", ".join(f"{k}=?" for k in kwargs)
    conn = get_conn()
    conn.execute(f"UPDATE tests SET {sets} WHERE id=?", [*kwargs.values(), test_id])
    conn.commit()
    conn.close()


def delete_test(test_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM tests WHERE id=?", (test_id,))
    conn.commit()
    conn.close()


# ── Questions ──────────────────────────────────────

def add_question(test_id: int, text: str, explanation="", topic="",
                 difficulty=1, points=1.0) -> int:
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO questions(test_id, text, explanation, topic, difficulty, points) VALUES(?,?,?,?,?,?)",
        (test_id, text, explanation, topic, difficulty, points)
    )
    qid = cur.lastrowid
    conn.commit()
    conn.close()
    return qid


def add_option(question_id: int, text: str, is_correct: bool) -> int:
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO question_options(question_id, text, is_correct) VALUES(?,?,?)",
        (question_id, text, int(is_correct))
    )
    oid = cur.lastrowid
    conn.commit()
    conn.close()
    return oid


def get_questions(test_id: int):
    conn = get_conn()
    rows = conn.execute("SELECT * FROM questions WHERE test_id=? ORDER BY id", (test_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_question(qid: int):
    conn = get_conn()
    row = conn.execute("SELECT * FROM questions WHERE id=?", (qid,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_options(question_id: int):
    conn = get_conn()
    rows = conn.execute("SELECT * FROM question_options WHERE question_id=? ORDER BY id", (question_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def count_questions(test_id: int) -> int:
    conn = get_conn()
    row = conn.execute("SELECT COUNT(*) as cnt FROM questions WHERE test_id=?", (test_id,)).fetchone()
    conn.close()
    return row["cnt"]


def delete_question(qid: int):
    conn = get_conn()
    conn.execute("DELETE FROM questions WHERE id=?", (qid,))
    conn.commit()
    conn.close()


def update_question(qid: int, **kwargs):
    sets = ", ".join(f"{k}=?" for k in kwargs)
    conn = get_conn()
    conn.execute(f"UPDATE questions SET {sets} WHERE id=?", [*kwargs.values(), qid])
    conn.commit()
    conn.close()


# ── Attempts ───────────────────────────────────────

def create_attempt(user_id: int, test_id: int, question_order: list,
                   is_first: bool, language: str) -> int:
    conn = get_conn()
    row = conn.execute(
        "SELECT COUNT(*) as cnt FROM test_attempts WHERE user_id=? AND test_id=? AND status='finished'",
        (user_id, test_id)
    ).fetchone()
    attempt_num = (row["cnt"] or 0) + 1
    cur = conn.execute("""
        INSERT INTO test_attempts(user_id, test_id, question_order, is_first_attempt,
            attempt_number, language, start_time, status)
        VALUES(?,?,?,?,?,?,datetime('now'),'active')
    """, (user_id, test_id, json.dumps(question_order), int(is_first), attempt_num, language))
    attempt_id = cur.lastrowid
    conn.commit()
    conn.close()
    return attempt_id


def get_attempt(attempt_id: int):
    conn = get_conn()
    row = conn.execute("SELECT * FROM test_attempts WHERE id=?", (attempt_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_active_attempt(user_id: int, test_id: int):
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM test_attempts WHERE user_id=? AND test_id=? AND status='active' LIMIT 1",
        (user_id, test_id)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def update_attempt(attempt_id: int, data: dict):
    sets = ", ".join(f"{k}=?" for k in data)
    conn = get_conn()
    conn.execute(f"UPDATE test_attempts SET {sets} WHERE id=?", [*data.values(), attempt_id])
    conn.commit()
    conn.close()


def save_answer(attempt_id: int, question_id: int, option_id, is_correct: bool,
                ms: int, topic: str = ""):
    conn = get_conn()
    conn.execute("""
        INSERT OR IGNORE INTO attempt_answers
        (attempt_id, question_id, selected_option_id, is_correct, response_time_ms, topic)
        VALUES(?,?,?,?,?,?)
    """, (attempt_id, question_id, option_id, int(is_correct), ms, topic))
    conn.commit()
    conn.close()


def has_answered(attempt_id: int, question_id: int) -> bool:
    conn = get_conn()
    row = conn.execute(
        "SELECT 1 FROM attempt_answers WHERE attempt_id=? AND question_id=?",
        (attempt_id, question_id)
    ).fetchone()
    conn.close()
    return row is not None


def count_user_attempts(user_id: int, test_id: int) -> int:
    conn = get_conn()
    row = conn.execute(
        "SELECT COUNT(*) as cnt FROM test_attempts WHERE user_id=? AND test_id=? AND status='finished'",
        (user_id, test_id)
    ).fetchone()
    conn.close()
    return row["cnt"]


def get_attempt_answers(attempt_id: int):
    conn = get_conn()
    rows = conn.execute("SELECT * FROM attempt_answers WHERE attempt_id=?", (attempt_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Channels ───────────────────────────────────────

def get_global_channels():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM required_channels WHERE is_global=1").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_test_channels(test_id: int):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM required_channels WHERE test_id=? OR is_global=1", (test_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_channel(channel_username: str, title: str = "", is_global: bool = False, test_id=None):
    conn = get_conn()
    conn.execute(
        "INSERT INTO required_channels(channel_username, title, is_global, test_id) VALUES(?,?,?,?)",
        (channel_username, title, int(is_global), test_id)
    )
    conn.commit()
    conn.close()


def list_channels():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM required_channels ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_channel(ch_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM required_channels WHERE id=?", (ch_id,))
    conn.commit()
    conn.close()


# ── Poll drafts ────────────────────────────────────

def save_poll_draft(test_id: int, poll_id: str, question_text: str, options: list,
                    correct_option_id, needs_manual: bool, imported_by: int) -> int:
    conn = get_conn()
    cur = conn.execute("""
        INSERT INTO imported_polls(test_id, poll_id, question_text, raw_options,
            correct_option_id, needs_manual, imported_by)
        VALUES(?,?,?,?,?,?,?)
    """, (test_id, poll_id, question_text, json.dumps(options),
          correct_option_id if correct_option_id is not None else -1,
          int(needs_manual), imported_by))
    draft_id = cur.lastrowid
    conn.commit()
    conn.close()
    return draft_id


def get_poll_drafts_needing_answer(test_id: int):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM imported_polls WHERE test_id=? AND needs_manual=1", (test_id,)
    ).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d["raw_options"] = json.loads(d["raw_options"]) if d["raw_options"] else []
        result.append(d)
    return result


def resolve_poll_draft(draft_id: int, correct_idx: int):
    conn = get_conn()
    row = conn.execute("SELECT * FROM imported_polls WHERE id=?", (draft_id,)).fetchone()
    conn.execute("UPDATE imported_polls SET needs_manual=0, correct_option_id=? WHERE id=?",
                 (correct_idx, draft_id))
    conn.commit()
    conn.close()
    if row:
        return dict(row)
    return None


# ── Ratings ────────────────────────────────────────

def get_leaderboard(language="ru", limit=10):
    conn = get_conn()
    rows = conn.execute("""
        SELECT u.full_name, u.telegram_id,
               MAX(ta.correct_answers*100.0/NULLIF(ta.correct_answers+ta.wrong_answers+ta.skipped_answers,0)) as best_pct
        FROM test_attempts ta JOIN users u ON ta.user_id=u.telegram_id
        WHERE ta.status='finished' AND ta.is_counted=1
        GROUP BY ta.user_id ORDER BY best_pct DESC LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_user_rank(user_id: int, language="ru") -> int:
    lb = get_leaderboard(language, limit=1000)
    for i, row in enumerate(lb, 1):
        if row["telegram_id"] == user_id:
            return i
    return -1


# ── Referrals ──────────────────────────────────────

def record_referral(referrer_id: int, referred_id: int) -> bool:
    if referrer_id == referred_id:
        return False
    conn = get_conn()
    existing = conn.execute("SELECT 1 FROM referrals WHERE referred_id=?", (referred_id,)).fetchone()
    if existing:
        conn.close()
        return False
    conn.execute("INSERT OR IGNORE INTO referrals(referrer_id, referred_id) VALUES(?,?)",
                 (referrer_id, referred_id))
    conn.commit()
    conn.close()
    return True


def count_referrals(telegram_id: int) -> int:
    conn = get_conn()
    row = conn.execute("SELECT COUNT(*) as cnt FROM referrals WHERE referrer_id=?", (telegram_id,)).fetchone()
    conn.close()
    return row["cnt"]


# ── Achievements ───────────────────────────────────

def grant_achievement(telegram_id: int, code: str) -> bool:
    conn = get_conn()
    try:
        conn.execute("INSERT INTO user_achievements(user_id, achievement_key) VALUES(?,?)",
                     (telegram_id, code))
        conn.commit()
        conn.close()
        return True
    except:
        conn.close()
        return False


def get_user_achievements(telegram_id: int):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM user_achievements WHERE user_id=? ORDER BY earned_at", (telegram_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Daily ──────────────────────────────────────────

def get_daily_task(task_date: str, language: str):
    conn = get_conn()
    row = conn.execute("SELECT * FROM daily_tasks WHERE task_date=? AND language=?",
                       (task_date, language)).fetchone()
    conn.close()
    return dict(row) if row else None


def create_daily_task(task_date: str, language: str, question_ids: list,
                      mode: str = "random") -> int:
    conn = get_conn()
    cur = conn.execute(
        "INSERT OR REPLACE INTO daily_tasks(task_date, language, question_ids, question_count) VALUES(?,?,?,?)",
        (task_date, language, json.dumps(question_ids), len(question_ids))
    )
    task_id = cur.lastrowid
    conn.commit()
    conn.close()
    return task_id


def save_daily_result(user_id: int, task_date: str, correct: int, wrong: int,
                      skipped: int, pct: float):
    from datetime import date, timedelta
    yesterday = (date.fromisoformat(task_date) - timedelta(days=1)).isoformat()
    conn = get_conn()
    prev = conn.execute("SELECT streak FROM daily_results WHERE user_id=? AND task_date=?",
                        (user_id, yesterday)).fetchone()
    streak = (prev["streak"] + 1) if prev else 1
    best_row = conn.execute("SELECT MAX(best_streak) as bs FROM daily_results WHERE user_id=?",
                            (user_id,)).fetchone()
    best = max(best_row["bs"] or 0, streak)
    conn.execute("""
        INSERT OR REPLACE INTO daily_results
        (user_id, task_date, correct_answers, wrong_answers, skipped_answers, percentage, streak, best_streak)
        VALUES(?,?,?,?,?,?,?,?)
    """, (user_id, task_date, correct, wrong, skipped, pct, streak, best))
    conn.commit()
    conn.close()


def get_daily_result(user_id: int, task_date: str):
    conn = get_conn()
    row = conn.execute("SELECT * FROM daily_results WHERE user_id=? AND task_date=?",
                       (user_id, task_date)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_streak(user_id: int) -> dict:
    conn = get_conn()
    row = conn.execute(
        "SELECT streak, best_streak FROM daily_results WHERE user_id=? ORDER BY task_date DESC LIMIT 1",
        (user_id,)
    ).fetchone()
    conn.close()
    if not row:
        return {"current": 0, "best": 0}
    return {"current": row["streak"], "best": row["best_streak"]}


# ── Duels ──────────────────────────────────────────

def create_duel(player1_id: int, subject=None, language="ru") -> int:
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO duels(player1_id, subject, language, status) VALUES(?,?,?,'searching')",
        (player1_id, subject or "", language)
    )
    duel_id = cur.lastrowid
    conn.commit()
    conn.close()
    return duel_id


def find_waiting_duel(subject=None, language="ru"):
    conn = get_conn()
    if subject:
        row = conn.execute(
            "SELECT * FROM duels WHERE status='searching' AND subject=? AND language=? LIMIT 1",
            (subject, language)
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT * FROM duels WHERE status='searching' AND language=? LIMIT 1",
            (language,)
        ).fetchone()
    conn.close()
    return dict(row) if row else None


def join_duel(duel_id: int, player2_id: int):
    conn = get_conn()
    conn.execute(
        "UPDATE duels SET player2_id=?, status='active', started_at=datetime('now') WHERE id=?",
        (player2_id, duel_id)
    )
    conn.commit()
    conn.close()


def get_duel(duel_id: int):
    conn = get_conn()
    row = conn.execute("SELECT * FROM duels WHERE id=?", (duel_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def update_duel(duel_id: int, data: dict):
    sets = ", ".join(f"{k}=?" for k in data)
    conn = get_conn()
    conn.execute(f"UPDATE duels SET {sets} WHERE id=?", [*data.values(), duel_id])
    conn.commit()
    conn.close()


def save_duel_answer(duel_id: int, user_id: int, question_id: int, option_id: int,
                     is_correct: bool, ms: int, score: int):
    conn = get_conn()
    conn.execute("""
        INSERT OR IGNORE INTO duel_answers
        (duel_id, user_id, question_id, selected_option, is_correct, response_time_ms, score)
        VALUES(?,?,?,?,?,?,?)
    """, (duel_id, user_id, question_id, option_id, int(is_correct), ms, score))
    conn.commit()
    conn.close()


def get_duel_score(duel_id: int, user_id: int) -> int:
    conn = get_conn()
    row = conn.execute(
        "SELECT COALESCE(SUM(score),0) as total FROM duel_answers WHERE duel_id=? AND user_id=?",
        (duel_id, user_id)
    ).fetchone()
    conn.close()
    return row["total"]


def cancel_duel(duel_id: int, user_id: int = None):
    conn = get_conn()
    conn.execute(
        "UPDATE duels SET status='cancelled', finished_at=datetime('now') WHERE id=?",
        (duel_id,)
    )
    conn.commit()
    conn.close()


def get_active_duel_for_user(telegram_id: int):
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM duels WHERE (player1_id=? OR player2_id=?) AND status IN ('searching','active') LIMIT 1",
        (telegram_id, telegram_id)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


# ── Notes ──────────────────────────────────────────

def create_note(title: str, description="", subject="", category="",
                language="ru", topic="", difficulty=1, is_paid=False,
                price=0, is_premium=False, created_by_admin=0) -> int:
    conn = get_conn()
    cur = conn.execute("""
        INSERT INTO notes(title, description, subject, category, language, topic,
            difficulty, is_paid, price, is_premium, created_by_admin)
        VALUES(?,?,?,?,?,?,?,?,?,?,?)
    """, (title, description, subject, category, language, topic,
          difficulty, int(is_paid), price, int(is_premium), created_by_admin))
    note_id = cur.lastrowid
    conn.commit()
    conn.close()
    return note_id


def get_note(note_id: int):
    conn = get_conn()
    row = conn.execute("SELECT * FROM notes WHERE id=?", (note_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def list_notes(language=None, limit=50, offset=0):
    conn = get_conn()
    if language:
        rows = conn.execute(
            "SELECT * FROM notes WHERE language=? ORDER BY id DESC LIMIT ? OFFSET ?",
            (language, limit, offset)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM notes ORDER BY id DESC LIMIT ? OFFSET ?", (limit, offset)
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_note_page(note_id: int, page_number: int, content: str) -> int:
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO note_pages(note_id, page_number, content) VALUES(?,?,?)",
        (note_id, page_number, content)
    )
    page_id = cur.lastrowid
    conn.commit()
    conn.close()
    return page_id


def get_note_pages(note_id: int):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM note_pages WHERE note_id=? ORDER BY page_number", (note_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_note_homework(note_id: int):
    conn = get_conn()
    row = conn.execute("SELECT * FROM note_homeworks WHERE note_id=? LIMIT 1", (note_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def add_note_homework(note_id: int, homework_type: str, test_id=None,
                      open_task_prompt="", auto_check_enabled=False) -> int:
    conn = get_conn()
    cur = conn.execute("""
        INSERT INTO note_homeworks(note_id, homework_type, test_id, open_task_prompt, auto_check_enabled)
        VALUES(?,?,?,?,?)
    """, (note_id, homework_type, test_id, open_task_prompt, int(auto_check_enabled)))
    hw_id = cur.lastrowid
    conn.commit()
    conn.close()
    return hw_id


def update_note_progress(user_id: int, note_id: int, last_page=None,
                         completed=False, homework_completed=False):
    conn = get_conn()
    conn.execute("""
        INSERT INTO user_notes_progress(user_id, note_id, last_page, completed, homework_completed)
        VALUES(?,?,?,?,?)
        ON CONFLICT(user_id, note_id) DO UPDATE SET
            last_page=COALESCE(excluded.last_page, last_page),
            completed=MAX(completed, excluded.completed),
            homework_completed=MAX(homework_completed, excluded.homework_completed)
    """, (user_id, note_id, last_page or 0, int(completed), int(homework_completed)))
    conn.commit()
    conn.close()


def get_note_progress(user_id: int, note_id: int):
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM user_notes_progress WHERE user_id=? AND note_id=?",
        (user_id, note_id)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def save_hw_answer(user_id: int, hw_id: int, answer_text: str, score=None):
    conn = get_conn()
    conn.execute(
        "INSERT INTO hw_answers(user_id, homework_id, answer_text, score) VALUES(?,?,?,?)",
        (user_id, hw_id, answer_text, score)
    )
    conn.commit()
    conn.close()


# ── Tournaments ────────────────────────────────────

def list_tournaments():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM tournaments ORDER BY start_date DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_tournament(title: str, test_id: int, start_date: str, end_date: str,
                      prize: str, created_by: int) -> int:
    conn = get_conn()
    cur = conn.execute("""
        INSERT INTO tournaments(title, test_id, start_date, end_date, prize, created_by)
        VALUES(?,?,?,?,?,?)
    """, (title, test_id, start_date, end_date, prize, created_by))
    tour_id = cur.lastrowid
    conn.commit()
    conn.close()
    return tour_id


def save_tournament_result(tournament_id: int, user_id: int, score: int,
                           percentage: float, attempt_id: int):
    conn = get_conn()
    conn.execute("""
        INSERT OR REPLACE INTO tournament_results(tournament_id, user_id, score, percentage, attempt_id)
        VALUES(?,?,?,?,?)
    """, (tournament_id, user_id, score, percentage, attempt_id))
    conn.commit()
    conn.close()


def get_tournament_leaderboard(tournament_id: int, limit=10):
    conn = get_conn()
    rows = conn.execute("""
        SELECT u.full_name, tr.score, tr.percentage
        FROM tournament_results tr JOIN users u ON tr.user_id=u.telegram_id
        WHERE tr.tournament_id=?
        ORDER BY tr.percentage DESC LIMIT ?
    """, (tournament_id, limit)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Group quizzes ──────────────────────────────────

def create_group_quiz(chat_id: int, test_id: int, started_by: int) -> int:
    from services.test_runner import get_questions as gq
    import random
    questions = get_questions(test_id)
    q_ids = [q["id"] for q in questions]
    random.shuffle(q_ids)
    conn = get_conn()
    cur = conn.execute("""
        INSERT INTO group_quizzes(test_id, group_id, started_by, question_order, status)
        VALUES(?,?,?,?,'waiting')
    """, (test_id, chat_id, started_by, json.dumps(q_ids)))
    quiz_id = cur.lastrowid
    conn.commit()
    conn.close()
    return quiz_id


def get_active_group_quiz(chat_id: int):
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM group_quizzes WHERE group_id=? AND status IN ('waiting','active') LIMIT 1",
        (chat_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def update_group_quiz(quiz_id: int, data: dict):
    sets = ", ".join(f"{k}=?" for k in data)
    conn = get_conn()
    conn.execute(f"UPDATE group_quizzes SET {sets} WHERE id=?", [*data.values(), quiz_id])
    conn.commit()
    conn.close()


def join_group_quiz(quiz_id: int, user_id: int):
    conn = get_conn()
    conn.execute("INSERT OR IGNORE INTO group_quiz_participants(quiz_id, user_id) VALUES(?,?)",
                 (quiz_id, user_id))
    conn.commit()
    conn.close()


def add_group_quiz_score(quiz_id: int, user_id: int, points: int):
    conn = get_conn()
    conn.execute(
        "UPDATE group_quiz_participants SET score=score+? WHERE quiz_id=? AND user_id=?",
        (points, quiz_id, user_id)
    )
    conn.commit()
    conn.close()


def group_quiz_top(quiz_id: int):
    conn = get_conn()
    rows = conn.execute("""
        SELECT u.full_name, p.score
        FROM group_quiz_participants p JOIN users u ON p.user_id=u.telegram_id
        WHERE p.quiz_id=? ORDER BY p.score DESC LIMIT 10
    """, (quiz_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def has_answered_group_question(quiz_id: int, user_id: int, question_id: int) -> bool:
    conn = get_conn()
    row = conn.execute(
        "SELECT 1 FROM group_quiz_answers WHERE quiz_id=? AND user_id=? AND question_id=?",
        (quiz_id, user_id, question_id)
    ).fetchone()
    conn.close()
    return row is not None


def save_answered_group_question(quiz_id: int, user_id: int, question_id: int, is_correct: bool):
    conn = get_conn()
    conn.execute(
        "INSERT OR IGNORE INTO group_quiz_answers(quiz_id, user_id, question_id, is_correct) VALUES(?,?,?,?)",
        (quiz_id, user_id, question_id, int(is_correct))
    )
    conn.commit()
    conn.close()


# ── Settings ───────────────────────────────────────

def get_setting(key: str, default: str = "") -> str:
    conn = get_conn()
    row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else default


def set_setting(key: str, value: str):
    conn = get_conn()
    conn.execute("INSERT OR REPLACE INTO settings(key, value) VALUES(?,?)", (key, value))
    conn.commit()
    conn.close()


# ── Analytics ──────────────────────────────────────

def get_weak_topics(user_id: int, language: str, limit=5):
    conn = get_conn()
    rows = conn.execute("""
        SELECT aa.topic,
               ROUND(AVG(CAST(aa.is_correct AS REAL))*100, 1) AS pct
        FROM attempt_answers aa
        JOIN test_attempts ta ON ta.id=aa.attempt_id
        WHERE ta.user_id=? AND aa.topic != ''
        GROUP BY aa.topic HAVING pct < 60
        ORDER BY pct ASC LIMIT ?
    """, (user_id, limit)).fetchall()
    conn.close()
    return [r["topic"] for r in rows]


def get_user_stats(telegram_id: int) -> dict:
    conn = get_conn()
    total = conn.execute(
        "SELECT COUNT(*) as cnt FROM test_attempts WHERE user_id=? AND status='finished'",
        (telegram_id,)
    ).fetchone()["cnt"]
    correct = conn.execute(
        "SELECT COALESCE(SUM(correct_answers),0) as s FROM test_attempts WHERE user_id=? AND status='finished'",
        (telegram_id,)
    ).fetchone()["s"]
    avg_row = conn.execute("""
        SELECT ROUND(AVG(correct_answers*100.0/NULLIF(correct_answers+wrong_answers+skipped_answers,0)),1) as avg
        FROM test_attempts WHERE user_id=? AND status='finished' AND is_counted=1
    """, (telegram_id,)).fetchone()
    conn.close()
    streak = get_user_streak(telegram_id)
    return {
        "total_attempts": total,
        "total_correct": correct,
        "avg_percent": avg_row["avg"] or 0,
        "current_streak": streak["current"],
        "best_streak": streak["best"],
    }
