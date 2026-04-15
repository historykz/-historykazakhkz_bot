"""
database.py
All SQLite interaction for the ENT bot.
Tables are created automatically on first run.
"""

import sqlite3
import json
import logging
from contextlib import contextmanager
from datetime import datetime, date
from typing import Optional, Any

from config import DB_PATH

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────
# Connection helper
# ─────────────────────────────────────────────────────────

@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────
# Schema creation
# ─────────────────────────────────────────────────────────

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id           INTEGER PRIMARY KEY,
    tg_id        INTEGER UNIQUE NOT NULL,
    username     TEXT,
    full_name    TEXT,
    language     TEXT DEFAULT 'ru',
    school_id    INTEGER,
    city_id      INTEGER,
    created_at   TEXT DEFAULT (datetime('now')),
    updated_at   TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS admins (
    id       INTEGER PRIMARY KEY,
    tg_id    INTEGER UNIQUE NOT NULL,
    note     TEXT,
    added_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS blocked_users (
    id         INTEGER PRIMARY KEY,
    tg_id      INTEGER UNIQUE NOT NULL,
    reason     TEXT,
    blocked_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS cities (
    id   INTEGER PRIMARY KEY,
    name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS schools (
    id      INTEGER PRIMARY KEY,
    name    TEXT NOT NULL,
    city_id INTEGER REFERENCES cities(id)
);

CREATE TABLE IF NOT EXISTS subjects (
    id       INTEGER PRIMARY KEY,
    name_ru  TEXT NOT NULL,
    name_kz  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS categories (
    id         INTEGER PRIMARY KEY,
    name_ru    TEXT NOT NULL,
    name_kz    TEXT NOT NULL,
    subject_id INTEGER REFERENCES subjects(id)
);

CREATE TABLE IF NOT EXISTS tests (
    id                     INTEGER PRIMARY KEY,
    title                  TEXT NOT NULL,
    description            TEXT DEFAULT '',
    subject_id             INTEGER REFERENCES subjects(id),
    class_num              INTEGER DEFAULT 11,
    category_id            INTEGER REFERENCES categories(id),
    language               TEXT DEFAULT 'ru',
    test_type              TEXT DEFAULT 'regular',
    status                 TEXT DEFAULT 'active',
    is_paid                INTEGER DEFAULT 0,
    price                  INTEGER DEFAULT 0,
    question_count         INTEGER DEFAULT 0,
    attempt_limit          INTEGER DEFAULT 0,
    first_attempt_only     INTEGER DEFAULT 1,
    deadline               TEXT,
    shuffle_questions      INTEGER DEFAULT 1,
    shuffle_options        INTEGER DEFAULT 1,
    show_correct_after     INTEGER DEFAULT 1,
    show_explanation_after INTEGER DEFAULT 1,
    question_time_sec      INTEGER DEFAULT 30,
    require_subscription   INTEGER DEFAULT 0,
    channel_id             INTEGER,
    allow_group            INTEGER DEFAULT 1,
    allow_duel             INTEGER DEFAULT 0,
    allow_daily            INTEGER DEFAULT 0,
    allow_tournament       INTEGER DEFAULT 0,
    question_mode          TEXT DEFAULT 'inline',
    adaptive_mode          INTEGER DEFAULT 0,
    created_by             INTEGER,
    created_at             TEXT DEFAULT (datetime('now')),
    updated_at             TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_tests_lang ON tests(language);
CREATE INDEX IF NOT EXISTS idx_tests_status ON tests(status);
CREATE INDEX IF NOT EXISTS idx_tests_type ON tests(test_type);

CREATE TABLE IF NOT EXISTS questions (
    id           INTEGER PRIMARY KEY,
    test_id      INTEGER REFERENCES tests(id) ON DELETE CASCADE,
    question_text TEXT NOT NULL,
    explanation  TEXT DEFAULT '',
    topic        TEXT DEFAULT '',
    difficulty   INTEGER DEFAULT 1,
    score        INTEGER DEFAULT 1,
    image_file_id TEXT,
    question_mode TEXT DEFAULT 'inline',
    position     INTEGER DEFAULT 0,
    created_at   TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_questions_test ON questions(test_id);
CREATE INDEX IF NOT EXISTS idx_questions_topic ON questions(topic);

CREATE TABLE IF NOT EXISTS question_options (
    id          INTEGER PRIMARY KEY,
    question_id INTEGER REFERENCES questions(id) ON DELETE CASCADE,
    option_text TEXT NOT NULL,
    is_correct  INTEGER DEFAULT 0,
    position    INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_opts_question ON question_options(question_id);

CREATE TABLE IF NOT EXISTS test_attempts (
    id                    INTEGER PRIMARY KEY,
    user_id               INTEGER REFERENCES users(tg_id),
    test_id               INTEGER REFERENCES tests(id),
    current_question_index INTEGER DEFAULT 0,
    question_order        TEXT DEFAULT '[]',
    correct_answers       INTEGER DEFAULT 0,
    wrong_answers         INTEGER DEFAULT 0,
    skipped_answers       INTEGER DEFAULT 0,
    score                 INTEGER DEFAULT 0,
    start_time            TEXT,
    end_time              TEXT,
    status                TEXT DEFAULT 'active',
    paused                INTEGER DEFAULT 0,
    missed_questions_counter INTEGER DEFAULT 0,
    pause_time            TEXT,
    is_counted            INTEGER DEFAULT 0,
    is_first_attempt      INTEGER DEFAULT 0,
    attempt_number        INTEGER DEFAULT 1,
    language              TEXT DEFAULT 'ru',
    group_id              INTEGER,
    started_by_user_id    INTEGER,
    created_at            TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_attempts_user ON test_attempts(user_id);
CREATE INDEX IF NOT EXISTS idx_attempts_test ON test_attempts(test_id);
CREATE INDEX IF NOT EXISTS idx_attempts_status ON test_attempts(status);

CREATE TABLE IF NOT EXISTS attempt_answers (
    id                INTEGER PRIMARY KEY,
    attempt_id        INTEGER REFERENCES test_attempts(id) ON DELETE CASCADE,
    question_id       INTEGER REFERENCES questions(id),
    selected_option_id INTEGER,
    is_correct        INTEGER DEFAULT 0,
    response_time_ms  INTEGER DEFAULT 0,
    topic             TEXT DEFAULT '',
    created_at        TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_ans_attempt ON attempt_answers(attempt_id);

CREATE TABLE IF NOT EXISTS paid_access (
    id          INTEGER PRIMARY KEY,
    user_id     INTEGER NOT NULL,
    test_id     INTEGER,
    note_id     INTEGER,
    granted_by  INTEGER,
    granted_at  TEXT DEFAULT (datetime('now')),
    expires_at  TEXT
);
CREATE INDEX IF NOT EXISTS idx_paid_user ON paid_access(user_id);

CREATE TABLE IF NOT EXISTS premium_users (
    id           INTEGER PRIMARY KEY,
    user_id      INTEGER UNIQUE NOT NULL,
    granted_at   TEXT DEFAULT (datetime('now')),
    expires_at   TEXT,
    granted_by_admin INTEGER
);

CREATE TABLE IF NOT EXISTS required_channels (
    id               INTEGER PRIMARY KEY,
    channel_username TEXT NOT NULL,
    title            TEXT DEFAULT '',
    is_global        INTEGER DEFAULT 0,
    test_id          INTEGER,
    section_id       INTEGER,
    note_id          INTEGER,
    created_at       TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS imported_polls (
    id                          INTEGER PRIMARY KEY,
    test_id                     INTEGER REFERENCES tests(id),
    poll_id                     TEXT,
    question_text               TEXT NOT NULL,
    raw_data                    TEXT,
    correct_option_id           INTEGER DEFAULT -1,
    needs_manual_correct_answer INTEGER DEFAULT 0,
    imported_by                 INTEGER,
    created_at                  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS question_drafts (
    id                  INTEGER PRIMARY KEY,
    test_id             INTEGER REFERENCES tests(id),
    source_type         TEXT DEFAULT 'poll',
    question_text       TEXT NOT NULL,
    raw_text            TEXT,
    raw_options         TEXT,
    status              TEXT DEFAULT 'draft',
    draft_correct_option INTEGER DEFAULT -1,
    created_by          INTEGER,
    created_at          TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS group_quizzes (
    id              INTEGER PRIMARY KEY,
    test_id         INTEGER REFERENCES tests(id),
    group_id        INTEGER NOT NULL,
    started_by      INTEGER,
    status          TEXT DEFAULT 'waiting',
    current_q_index INTEGER DEFAULT 0,
    question_order  TEXT DEFAULT '[]',
    paused          INTEGER DEFAULT 0,
    missed_counter  INTEGER DEFAULT 0,
    started_at      TEXT,
    finished_at     TEXT,
    created_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS group_quiz_participants (
    id        INTEGER PRIMARY KEY,
    quiz_id   INTEGER REFERENCES group_quizzes(id),
    user_id   INTEGER NOT NULL,
    score     INTEGER DEFAULT 0,
    joined_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS group_quiz_answers (
    id          INTEGER PRIMARY KEY,
    quiz_id     INTEGER REFERENCES group_quizzes(id),
    question_id INTEGER,
    user_id     INTEGER,
    is_correct  INTEGER DEFAULT 0,
    answered_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS daily_tasks (
    id           INTEGER PRIMARY KEY,
    task_date    TEXT NOT NULL,
    language     TEXT DEFAULT 'ru',
    subject_id   INTEGER,
    category_id  INTEGER,
    question_ids TEXT DEFAULT '[]',
    mode         TEXT DEFAULT 'random',
    created_at   TEXT DEFAULT (datetime('now'))
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_daily_date_lang ON daily_tasks(task_date, language);

CREATE TABLE IF NOT EXISTS daily_results (
    id              INTEGER PRIMARY KEY,
    user_id         INTEGER NOT NULL,
    task_date       TEXT NOT NULL,
    correct_answers INTEGER DEFAULT 0,
    wrong_answers   INTEGER DEFAULT 0,
    skipped_answers INTEGER DEFAULT 0,
    percentage      REAL DEFAULT 0,
    streak          INTEGER DEFAULT 0,
    best_streak     INTEGER DEFAULT 0,
    completed_at    TEXT DEFAULT (datetime('now')),
    UNIQUE(user_id, task_date)
);

CREATE TABLE IF NOT EXISTS referrals (
    id           INTEGER PRIMARY KEY,
    referrer_id  INTEGER NOT NULL,
    referred_id  INTEGER NOT NULL UNIQUE,
    bonus_given  INTEGER DEFAULT 0,
    created_at   TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS achievements (
    id          INTEGER PRIMARY KEY,
    code        TEXT UNIQUE NOT NULL,
    name_ru     TEXT NOT NULL,
    name_kz     TEXT NOT NULL,
    description_ru TEXT DEFAULT '',
    description_kz TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS user_achievements (
    id             INTEGER PRIMARY KEY,
    user_id        INTEGER NOT NULL,
    achievement_id INTEGER REFERENCES achievements(id),
    earned_at      TEXT DEFAULT (datetime('now')),
    UNIQUE(user_id, achievement_id)
);

CREATE TABLE IF NOT EXISTS tournaments (
    id          INTEGER PRIMARY KEY,
    title       TEXT NOT NULL,
    test_id     INTEGER REFERENCES tests(id),
    start_time  TEXT,
    end_time    TEXT,
    prize       TEXT DEFAULT '',
    status      TEXT DEFAULT 'upcoming',
    created_by  INTEGER,
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS tournament_results (
    id            INTEGER PRIMARY KEY,
    tournament_id INTEGER REFERENCES tournaments(id),
    user_id       INTEGER NOT NULL,
    score         INTEGER DEFAULT 0,
    percentage    REAL DEFAULT 0,
    attempt_id    INTEGER,
    created_at    TEXT DEFAULT (datetime('now')),
    UNIQUE(tournament_id, user_id)
);

CREATE TABLE IF NOT EXISTS duels (
    id          INTEGER PRIMARY KEY,
    player1_id  INTEGER NOT NULL,
    player2_id  INTEGER,
    subject_id  INTEGER,
    category_id INTEGER,
    question_ids TEXT DEFAULT '[]',
    status      TEXT DEFAULT 'searching',
    winner_id   INTEGER,
    created_at  TEXT DEFAULT (datetime('now')),
    started_at  TEXT,
    finished_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_duel_p1 ON duels(player1_id);
CREATE INDEX IF NOT EXISTS idx_duel_p2 ON duels(player2_id);
CREATE INDEX IF NOT EXISTS idx_duel_status ON duels(status);

CREATE TABLE IF NOT EXISTS duel_answers (
    id               INTEGER PRIMARY KEY,
    duel_id          INTEGER REFERENCES duels(id),
    user_id          INTEGER NOT NULL,
    question_id      INTEGER NOT NULL,
    selected_option  INTEGER,
    is_correct       INTEGER DEFAULT 0,
    response_time_ms INTEGER DEFAULT 0,
    score            INTEGER DEFAULT 0,
    created_at       TEXT DEFAULT (datetime('now')),
    UNIQUE(duel_id, user_id, question_id)
);

CREATE TABLE IF NOT EXISTS rankings_cache (
    id         INTEGER PRIMARY KEY,
    scope      TEXT NOT NULL,
    language   TEXT DEFAULT 'ru',
    data_json  TEXT DEFAULT '[]',
    updated_at TEXT DEFAULT (datetime('now')),
    UNIQUE(scope, language)
);

CREATE TABLE IF NOT EXISTS import_batches (
    id          INTEGER PRIMARY KEY,
    test_id     INTEGER REFERENCES tests(id),
    total       INTEGER DEFAULT 0,
    ok          INTEGER DEFAULT 0,
    errors      INTEGER DEFAULT 0,
    error_info  TEXT DEFAULT '',
    imported_by INTEGER,
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS notes (
    id               INTEGER PRIMARY KEY,
    title            TEXT NOT NULL,
    description      TEXT DEFAULT '',
    subject_id       INTEGER REFERENCES subjects(id),
    category_id      INTEGER REFERENCES categories(id),
    language         TEXT DEFAULT 'ru',
    topic            TEXT DEFAULT '',
    difficulty       INTEGER DEFAULT 1,
    is_paid          INTEGER DEFAULT 0,
    price            INTEGER DEFAULT 0,
    is_premium       INTEGER DEFAULT 0,
    created_by_admin INTEGER,
    created_at       TEXT DEFAULT (datetime('now')),
    updated_at       TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_notes_lang ON notes(language);

CREATE TABLE IF NOT EXISTS note_pages (
    id          INTEGER PRIMARY KEY,
    note_id     INTEGER REFERENCES notes(id) ON DELETE CASCADE,
    page_number INTEGER NOT NULL,
    content     TEXT NOT NULL,
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS note_homeworks (
    id                 INTEGER PRIMARY KEY,
    note_id            INTEGER REFERENCES notes(id) ON DELETE CASCADE,
    homework_type      TEXT DEFAULT 'test',
    test_id            INTEGER REFERENCES tests(id),
    open_task_prompt   TEXT DEFAULT '',
    auto_check_enabled INTEGER DEFAULT 0,
    keywords           TEXT DEFAULT '',
    created_at         TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS user_notes_progress (
    id                 INTEGER PRIMARY KEY,
    user_id            INTEGER NOT NULL,
    note_id            INTEGER REFERENCES notes(id),
    last_page          INTEGER DEFAULT 0,
    completed          INTEGER DEFAULT 0,
    homework_completed INTEGER DEFAULT 0,
    hw_score           REAL DEFAULT 0,
    hw_answer_text     TEXT DEFAULT '',
    created_at         TEXT DEFAULT (datetime('now')),
    updated_at         TEXT DEFAULT (datetime('now')),
    UNIQUE(user_id, note_id)
);

CREATE TABLE IF NOT EXISTS generated_questions (
    id           INTEGER PRIMARY KEY,
    note_id      INTEGER REFERENCES notes(id),
    test_id      INTEGER REFERENCES tests(id),
    question_text TEXT NOT NULL,
    options_json TEXT NOT NULL,
    correct_idx  INTEGER NOT NULL,
    explanation  TEXT DEFAULT '',
    topic        TEXT DEFAULT '',
    difficulty   INTEGER DEFAULT 1,
    approved     INTEGER DEFAULT 0,
    created_at   TEXT DEFAULT (datetime('now'))
);
"""

SEED_ACHIEVEMENTS = [
    ("first_test",    "Первый тест",          "Бірінші тест"),
    ("tests_10",      "10 тестов",            "10 тест"),
    ("tests_50",      "50 тестов",            "50 тест"),
    ("streak_7",      "7 дней streak",        "7 күн streak"),
    ("streak_30",     "30 дней streak",       "30 күн streak"),
    ("correct_100",   "100 правильных",       "100 дұрыс жауап"),
    ("duel_win",      "Победа в дуэли",       "Дуэльде жеңу"),
    ("tournament_1st","1 место в турнире",    "Турнирде 1-орын"),
    ("first_note",    "Первый конспект",      "Бірінші конспект"),
    ("first_hw",      "Первое ДЗ",            "Бірінші ҮТ"),
    ("premium",       "Premium получен",      "Premium алынды"),
]


def init_db():
    """Create all tables and seed initial data if not present."""
    logger.info("Initialising database at %s", DB_PATH)
    with get_conn() as conn:
        conn.executescript(SCHEMA_SQL)
        # seed achievements
        for code, ru, kz in SEED_ACHIEVEMENTS:
            conn.execute(
                "INSERT OR IGNORE INTO achievements(code, name_ru, name_kz) VALUES (?,?,?)",
                (code, ru, kz),
            )
    logger.info("Database initialised.")


# ─────────────────────────────────────────────────────────
# Users
# ─────────────────────────────────────────────────────────

def upsert_user(tg_id: int, username: str, full_name: str) -> None:
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO users(tg_id, username, full_name)
               VALUES(?,?,?)
               ON CONFLICT(tg_id) DO UPDATE SET
                   username=excluded.username,
                   full_name=excluded.full_name,
                   updated_at=datetime('now')""",
            (tg_id, username, full_name),
        )


def get_user(tg_id: int) -> Optional[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute("SELECT * FROM users WHERE tg_id=?", (tg_id,)).fetchone()


def set_user_language(tg_id: int, lang: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE users SET language=?, updated_at=datetime('now') WHERE tg_id=?",
            (lang, tg_id),
        )


def get_user_language(tg_id: int) -> str:
    with get_conn() as conn:
        row = conn.execute("SELECT language FROM users WHERE tg_id=?", (tg_id,)).fetchone()
        return row["language"] if row else "ru"


def is_blocked(tg_id: int) -> bool:
    with get_conn() as conn:
        return conn.execute(
            "SELECT 1 FROM blocked_users WHERE tg_id=?", (tg_id,)
        ).fetchone() is not None


def block_user(tg_id: int, reason: str = "") -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO blocked_users(tg_id, reason) VALUES(?,?)",
            (tg_id, reason),
        )


def unblock_user(tg_id: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM blocked_users WHERE tg_id=?", (tg_id,))


def is_admin(tg_id: int) -> bool:
    from config import ADMIN_IDS
    if tg_id in ADMIN_IDS:
        return True
    with get_conn() as conn:
        return conn.execute(
            "SELECT 1 FROM admins WHERE tg_id=?", (tg_id,)
        ).fetchone() is not None


# ─────────────────────────────────────────────────────────
# Premium
# ─────────────────────────────────────────────────────────

def has_premium(tg_id: int) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT expires_at FROM premium_users WHERE user_id=?", (tg_id,)
        ).fetchone()
    if not row:
        return False
    if row["expires_at"] is None:
        return True
    return datetime.fromisoformat(row["expires_at"]) > datetime.utcnow()


def grant_premium(tg_id: int, days: Optional[int], admin_id: int) -> None:
    expires = None
    if days:
        from datetime import timedelta
        expires = (datetime.utcnow() + timedelta(days=days)).isoformat()
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO premium_users(user_id, expires_at, granted_by_admin)
               VALUES(?,?,?)
               ON CONFLICT(user_id) DO UPDATE SET
                   granted_at=datetime('now'), expires_at=excluded.expires_at,
                   granted_by_admin=excluded.granted_by_admin""",
            (tg_id, expires, admin_id),
        )


def revoke_premium(tg_id: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM premium_users WHERE user_id=?", (tg_id,))


# ─────────────────────────────────────────────────────────
# Access
# ─────────────────────────────────────────────────────────

def has_test_access(tg_id: int, test_id: int) -> bool:
    """Returns True if user has explicit paid access or Premium."""
    if has_premium(tg_id):
        return True
    with get_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM paid_access WHERE user_id=? AND test_id=? AND (expires_at IS NULL OR expires_at > datetime('now'))",
            (tg_id, test_id),
        ).fetchone()
    return row is not None


def grant_test_access(tg_id: int, test_id: int, admin_id: int, days: Optional[int] = None) -> None:
    expires = None
    if days:
        from datetime import timedelta
        expires = (datetime.utcnow() + timedelta(days=days)).isoformat()
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO paid_access(user_id, test_id, granted_by, expires_at) VALUES(?,?,?,?)",
            (tg_id, test_id, admin_id, expires),
        )


def has_note_access(tg_id: int, note_id: int) -> bool:
    if has_premium(tg_id):
        return True
    with get_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM paid_access WHERE user_id=? AND note_id=? AND (expires_at IS NULL OR expires_at > datetime('now'))",
            (tg_id, note_id),
        ).fetchone()
    return row is not None


def grant_note_access(tg_id: int, note_id: int, admin_id: int) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO paid_access(user_id, note_id, granted_by) VALUES(?,?,?)",
            (tg_id, note_id, admin_id),
        )


# ─────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────

def create_test(data: dict) -> int:
    cols = ", ".join(data.keys())
    placeholders = ", ".join("?" for _ in data)
    with get_conn() as conn:
        cur = conn.execute(
            f"INSERT INTO tests({cols}) VALUES({placeholders})", list(data.values())
        )
        return cur.lastrowid


def get_test(test_id: int) -> Optional[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute("SELECT * FROM tests WHERE id=?", (test_id,)).fetchone()


def list_tests(language: str = None, test_type: str = None,
               status: str = "active", limit: int = 50, offset: int = 0) -> list:
    clauses = ["status=?"]
    params: list = [status]
    if language:
        clauses.append("language=?")
        params.append(language)
    if test_type:
        clauses.append("test_type=?")
        params.append(test_type)
    where = " AND ".join(clauses)
    params += [limit, offset]
    with get_conn() as conn:
        return conn.execute(
            f"SELECT * FROM tests WHERE {where} ORDER BY id DESC LIMIT ? OFFSET ?",
            params,
        ).fetchall()


def update_test(test_id: int, data: dict) -> None:
    data["updated_at"] = datetime.utcnow().isoformat()
    sets = ", ".join(f"{k}=?" for k in data)
    with get_conn() as conn:
        conn.execute(f"UPDATE tests SET {sets} WHERE id=?", [*data.values(), test_id])


def delete_test(test_id: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM tests WHERE id=?", (test_id,))


# ─────────────────────────────────────────────────────────
# Questions
# ─────────────────────────────────────────────────────────

def add_question(test_id: int, text: str, explanation: str = "",
                 topic: str = "", difficulty: int = 1, score: int = 1,
                 image_file_id: str = None, mode: str = "inline") -> int:
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO questions(test_id, question_text, explanation,
               topic, difficulty, score, image_file_id, question_mode)
               VALUES(?,?,?,?,?,?,?,?)""",
            (test_id, text, explanation, topic, difficulty, score, image_file_id, mode),
        )
        return cur.lastrowid


def add_option(question_id: int, text: str, is_correct: bool, position: int = 0) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO question_options(question_id, option_text, is_correct, position) VALUES(?,?,?,?)",
            (question_id, text, int(is_correct), position),
        )
        return cur.lastrowid


def get_questions(test_id: int) -> list:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM questions WHERE test_id=? ORDER BY position, id",
            (test_id,),
        ).fetchall()


def get_question(qid: int) -> Optional[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute("SELECT * FROM questions WHERE id=?", (qid,)).fetchone()


def get_options(question_id: int) -> list:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM question_options WHERE question_id=? ORDER BY position, id",
            (question_id,),
        ).fetchall()


def count_questions(test_id: int) -> int:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM questions WHERE test_id=?", (test_id,)
        ).fetchone()
        return row["cnt"]


def delete_question(qid: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM questions WHERE id=?", (qid,))


def update_question(qid: int, data: dict) -> None:
    sets = ", ".join(f"{k}=?" for k in data)
    with get_conn() as conn:
        conn.execute(f"UPDATE questions SET {sets} WHERE id=?", [*data.values(), qid])


# ─────────────────────────────────────────────────────────
# Attempts
# ─────────────────────────────────────────────────────────

def create_attempt(user_id: int, test_id: int, question_order: list,
                   is_first: bool, language: str, group_id: int = None,
                   started_by: int = None) -> int:
    # figure out attempt number
    with get_conn() as conn:
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM test_attempts WHERE user_id=? AND test_id=? AND status='finished'",
            (user_id, test_id),
        ).fetchone()
        attempt_num = (row["cnt"] or 0) + 1
        cur = conn.execute(
            """INSERT INTO test_attempts
               (user_id, test_id, question_order, is_first_attempt, attempt_number,
                language, group_id, started_by_user_id, start_time, status)
               VALUES(?,?,?,?,?,?,?,?,datetime('now'),'active')""",
            (user_id, test_id, json.dumps(question_order),
             int(is_first), attempt_num, language, group_id, started_by),
        )
        return cur.lastrowid


def get_attempt(attempt_id: int) -> Optional[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM test_attempts WHERE id=?", (attempt_id,)
        ).fetchone()


def get_active_attempt(user_id: int, test_id: int) -> Optional[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM test_attempts WHERE user_id=? AND test_id=? AND status='active' LIMIT 1",
            (user_id, test_id),
        ).fetchone()


def update_attempt(attempt_id: int, data: dict) -> None:
    sets = ", ".join(f"{k}=?" for k in data)
    with get_conn() as conn:
        conn.execute(
            f"UPDATE test_attempts SET {sets} WHERE id=?", [*data.values(), attempt_id]
        )


def save_answer(attempt_id: int, question_id: int, option_id: Optional[int],
                is_correct: bool, ms: int, topic: str = "") -> None:
    with get_conn() as conn:
        conn.execute(
            """INSERT OR IGNORE INTO attempt_answers
               (attempt_id, question_id, selected_option_id, is_correct, response_time_ms, topic)
               VALUES(?,?,?,?,?,?)""",
            (attempt_id, question_id, option_id, int(is_correct), ms, topic),
        )


def has_answered(attempt_id: int, question_id: int) -> bool:
    with get_conn() as conn:
        return conn.execute(
            "SELECT 1 FROM attempt_answers WHERE attempt_id=? AND question_id=?",
            (attempt_id, question_id),
        ).fetchone() is not None


def count_user_attempts(user_id: int, test_id: int) -> int:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM test_attempts WHERE user_id=? AND test_id=? AND status='finished'",
            (user_id, test_id),
        ).fetchone()
        return row["cnt"]


def get_attempt_answers(attempt_id: int) -> list:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM attempt_answers WHERE attempt_id=?", (attempt_id,)
        ).fetchall()


# ─────────────────────────────────────────────────────────
# Required channels
# ─────────────────────────────────────────────────────────

def get_global_channels() -> list:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM required_channels WHERE is_global=1"
        ).fetchall()


def get_test_channels(test_id: int) -> list:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM required_channels WHERE test_id=? OR is_global=1",
            (test_id,),
        ).fetchall()


def add_channel(username: str, title: str = "", is_global: int = 0,
                test_id: int = None, note_id: int = None) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO required_channels(channel_username, title, is_global, test_id, note_id) VALUES(?,?,?,?,?)",
            (username, title, is_global, test_id, note_id),
        )
        return cur.lastrowid


def list_channels() -> list:
    with get_conn() as conn:
        return conn.execute("SELECT * FROM required_channels ORDER BY id").fetchall()


def delete_channel(ch_id: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM required_channels WHERE id=?", (ch_id,))


# ─────────────────────────────────────────────────────────
# Poll drafts
# ─────────────────────────────────────────────────────────

def save_poll_draft(test_id: int, question_text: str, options: list,
                    correct_option_id: int, poll_id: str,
                    importer_id: int) -> int:
    needs_manual = 1 if correct_option_id < 0 else 0
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO imported_polls
               (test_id, poll_id, question_text, raw_data, correct_option_id,
                needs_manual_correct_answer, imported_by)
               VALUES(?,?,?,?,?,?,?)""",
            (test_id, poll_id, question_text,
             json.dumps({"options": options}), correct_option_id,
             needs_manual, importer_id),
        )
        pid = cur.lastrowid
        if not needs_manual:
            # auto-promote to real question
            _promote_poll_draft(conn, pid, test_id, question_text, options, correct_option_id)
        return pid


def _promote_poll_draft(conn, poll_id_row: int, test_id: int, question_text: str,
                         options: list, correct_idx: int) -> None:
    """Insert into questions + options tables directly."""
    cur = conn.execute(
        "INSERT INTO questions(test_id, question_text, question_mode) VALUES(?,?,'inline')",
        (test_id, question_text),
    )
    qid = cur.lastrowid
    for i, opt in enumerate(options):
        conn.execute(
            "INSERT INTO question_options(question_id, option_text, is_correct, position) VALUES(?,?,?,?)",
            (qid, opt, int(i == correct_idx), i),
        )
    conn.execute("UPDATE imported_polls SET status='promoted' WHERE id=?", (poll_id_row,))


def get_poll_drafts_needing_answer(test_id: int) -> list:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM imported_polls WHERE test_id=? AND needs_manual_correct_answer=1",
            (test_id,),
        ).fetchall()


def resolve_poll_draft(draft_id: int, correct_idx: int) -> None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM imported_polls WHERE id=?", (draft_id,)
        ).fetchone()
        if not row:
            return
        options = json.loads(row["raw_data"]).get("options", [])
        _promote_poll_draft(conn, draft_id, row["test_id"],
                             row["question_text"], options, correct_idx)
        conn.execute(
            "UPDATE imported_polls SET needs_manual_correct_answer=0, correct_option_id=? WHERE id=?",
            (correct_idx, draft_id),
        )


# ─────────────────────────────────────────────────────────
# Ratings
# ─────────────────────────────────────────────────────────

def get_leaderboard(language: str = "ru", limit: int = 10) -> list:
    """Top users by average percent on counted attempts."""
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT u.tg_id, u.full_name,
                      ROUND(AVG(
                          CAST(ta.correct_answers AS REAL) /
                          NULLIF(ta.correct_answers+ta.wrong_answers+ta.skipped_answers,0)*100
                      ),1) AS avg_pct,
                      COUNT(*) AS attempts
               FROM test_attempts ta
               JOIN users u ON u.tg_id=ta.user_id
               JOIN tests t ON t.id=ta.test_id
               WHERE ta.status='finished' AND ta.is_counted=1 AND t.language=?
               GROUP BY ta.user_id
               ORDER BY avg_pct DESC
               LIMIT ?""",
            (language, limit),
        ).fetchall()
    return rows


def get_user_rank(tg_id: int, language: str = "ru") -> int:
    lb = get_leaderboard(language, limit=1000)
    for i, row in enumerate(lb, 1):
        if row["tg_id"] == tg_id:
            return i
    return -1


# ─────────────────────────────────────────────────────────
# Referrals
# ─────────────────────────────────────────────────────────

def record_referral(referrer_id: int, referred_id: int) -> bool:
    """Returns True if newly recorded."""
    if referrer_id == referred_id:
        return False
    with get_conn() as conn:
        existing = conn.execute(
            "SELECT 1 FROM referrals WHERE referred_id=?", (referred_id,)
        ).fetchone()
        if existing:
            return False
        conn.execute(
            "INSERT OR IGNORE INTO referrals(referrer_id, referred_id) VALUES(?,?)",
            (referrer_id, referred_id),
        )
        return True


def count_referrals(tg_id: int) -> int:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM referrals WHERE referrer_id=?", (tg_id,)
        ).fetchone()
        return row["cnt"]


# ─────────────────────────────────────────────────────────
# Achievements
# ─────────────────────────────────────────────────────────

def grant_achievement(tg_id: int, code: str) -> bool:
    """Returns True if newly granted."""
    with get_conn() as conn:
        ach = conn.execute("SELECT id FROM achievements WHERE code=?", (code,)).fetchone()
        if not ach:
            return False
        try:
            conn.execute(
                "INSERT INTO user_achievements(user_id, achievement_id) VALUES(?,?)",
                (tg_id, ach["id"]),
            )
            return True
        except sqlite3.IntegrityError:
            return False


def get_user_achievements(tg_id: int) -> list:
    with get_conn() as conn:
        return conn.execute(
            """SELECT a.code, a.name_ru, a.name_kz, ua.earned_at
               FROM user_achievements ua
               JOIN achievements a ON a.id=ua.achievement_id
               WHERE ua.user_id=?
               ORDER BY ua.earned_at""",
            (tg_id,),
        ).fetchall()


# ─────────────────────────────────────────────────────────
# Daily ENT
# ─────────────────────────────────────────────────────────

def get_daily_task(task_date: str, language: str) -> Optional[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM daily_tasks WHERE task_date=? AND language=?",
            (task_date, language),
        ).fetchone()


def create_daily_task(task_date: str, language: str, question_ids: list,
                      subject_id: int = None, mode: str = "random") -> int:
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT OR REPLACE INTO daily_tasks
               (task_date, language, question_ids, subject_id, mode)
               VALUES(?,?,?,?,?)""",
            (task_date, language, json.dumps(question_ids), subject_id, mode),
        )
        return cur.lastrowid


def save_daily_result(user_id: int, task_date: str, correct: int,
                       wrong: int, skipped: int, pct: float) -> None:
    # compute streak
    from datetime import date, timedelta
    yesterday = (date.fromisoformat(task_date) - timedelta(days=1)).isoformat()
    with get_conn() as conn:
        prev = conn.execute(
            "SELECT streak FROM daily_results WHERE user_id=? AND task_date=?",
            (user_id, yesterday),
        ).fetchone()
        streak = (prev["streak"] + 1) if prev else 1
        best_row = conn.execute(
            "SELECT MAX(best_streak) as bs FROM daily_results WHERE user_id=?", (user_id,)
        ).fetchone()
        best = max(best_row["bs"] or 0, streak)
        conn.execute(
            """INSERT OR REPLACE INTO daily_results
               (user_id, task_date, correct_answers, wrong_answers, skipped_answers,
                percentage, streak, best_streak)
               VALUES(?,?,?,?,?,?,?,?)""",
            (user_id, task_date, correct, wrong, skipped, pct, streak, best),
        )


def get_daily_result(user_id: int, task_date: str) -> Optional[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM daily_results WHERE user_id=? AND task_date=?",
            (user_id, task_date),
        ).fetchone()


def get_user_streak(user_id: int) -> tuple[int, int]:
    """Returns (current_streak, best_streak)."""
    with get_conn() as conn:
        row = conn.execute(
            """SELECT streak, best_streak FROM daily_results
               WHERE user_id=? ORDER BY task_date DESC LIMIT 1""",
            (user_id,),
        ).fetchone()
    if not row:
        return 0, 0
    return row["streak"], row["best_streak"]


# ─────────────────────────────────────────────────────────
# Duels
# ─────────────────────────────────────────────────────────

def create_duel(player1_id: int, subject_id: int = None) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO duels(player1_id, subject_id, status) VALUES(?,?,'searching')",
            (player1_id, subject_id),
        )
        return cur.lastrowid


def find_waiting_duel(player_id: int, subject_id: int = None) -> Optional[sqlite3.Row]:
    with get_conn() as conn:
        if subject_id:
            return conn.execute(
                "SELECT * FROM duels WHERE status='searching' AND player1_id!=? AND subject_id=? LIMIT 1",
                (player_id, subject_id),
            ).fetchone()
        return conn.execute(
            "SELECT * FROM duels WHERE status='searching' AND player1_id!=? LIMIT 1",
            (player_id,),
        ).fetchone()


def join_duel(duel_id: int, player2_id: int, question_ids: list) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE duels SET player2_id=?, question_ids=?, status='active', started_at=datetime('now') WHERE id=?",
            (player2_id, json.dumps(question_ids), duel_id),
        )


def get_duel(duel_id: int) -> Optional[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute("SELECT * FROM duels WHERE id=?", (duel_id,)).fetchone()


def update_duel(duel_id: int, data: dict) -> None:
    sets = ", ".join(f"{k}=?" for k in data)
    with get_conn() as conn:
        conn.execute(f"UPDATE duels SET {sets} WHERE id=?", [*data.values(), duel_id])


def save_duel_answer(duel_id: int, user_id: int, question_id: int,
                      option_id: int, is_correct: bool, ms: int, score: int) -> None:
    with get_conn() as conn:
        conn.execute(
            """INSERT OR IGNORE INTO duel_answers
               (duel_id, user_id, question_id, selected_option, is_correct, response_time_ms, score)
               VALUES(?,?,?,?,?,?,?)""",
            (duel_id, user_id, question_id, option_id, int(is_correct), ms, score),
        )


def get_duel_score(duel_id: int, user_id: int) -> int:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT COALESCE(SUM(score),0) as total FROM duel_answers WHERE duel_id=? AND user_id=?",
            (duel_id, user_id),
        ).fetchone()
    return row["total"]


def cancel_duel(duel_id: int) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE duels SET status='cancelled', finished_at=datetime('now') WHERE id=?",
            (duel_id,),
        )


def get_active_duel_for_user(tg_id: int) -> Optional[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(
            """SELECT * FROM duels
               WHERE (player1_id=? OR player2_id=?) AND status IN ('searching','active')
               LIMIT 1""",
            (tg_id, tg_id),
        ).fetchone()


# ─────────────────────────────────────────────────────────
# Notes / Конспекты
# ─────────────────────────────────────────────────────────

def create_note(data: dict) -> int:
    cols = ", ".join(data.keys())
    phs = ", ".join("?" for _ in data)
    with get_conn() as conn:
        cur = conn.execute(f"INSERT INTO notes({cols}) VALUES({phs})", list(data.values()))
        return cur.lastrowid


def get_note(note_id: int) -> Optional[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute("SELECT * FROM notes WHERE id=?", (note_id,)).fetchone()


def list_notes(language: str = None, limit: int = 50, offset: int = 0) -> list:
    if language:
        with get_conn() as conn:
            return conn.execute(
                "SELECT * FROM notes WHERE language=? ORDER BY id DESC LIMIT ? OFFSET ?",
                (language, limit, offset),
            ).fetchall()
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM notes ORDER BY id DESC LIMIT ? OFFSET ?", (limit, offset)
        ).fetchall()


def add_note_page(note_id: int, page_number: int, content: str) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO note_pages(note_id, page_number, content) VALUES(?,?,?)",
            (note_id, page_number, content),
        )
        return cur.lastrowid


def get_note_pages(note_id: int) -> list:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM note_pages WHERE note_id=? ORDER BY page_number",
            (note_id,),
        ).fetchall()


def get_note_homework(note_id: int) -> Optional[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM note_homeworks WHERE note_id=? LIMIT 1", (note_id,)
        ).fetchone()


def add_note_homework(note_id: int, hw_type: str, test_id: int = None,
                       prompt: str = "", auto_check: bool = False, keywords: str = "") -> int:
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO note_homeworks
               (note_id, homework_type, test_id, open_task_prompt, auto_check_enabled, keywords)
               VALUES(?,?,?,?,?,?)""",
            (note_id, hw_type, test_id, prompt, int(auto_check), keywords),
        )
        return cur.lastrowid


def update_note_progress(user_id: int, note_id: int, last_page: int,
                          completed: bool = False) -> None:
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO user_notes_progress(user_id, note_id, last_page, completed)
               VALUES(?,?,?,?)
               ON CONFLICT(user_id, note_id) DO UPDATE SET
                   last_page=excluded.last_page,
                   completed=excluded.completed,
                   updated_at=datetime('now')""",
            (user_id, note_id, last_page, int(completed)),
        )


def get_note_progress(user_id: int, note_id: int) -> Optional[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM user_notes_progress WHERE user_id=? AND note_id=?",
            (user_id, note_id),
        ).fetchone()


def save_hw_answer(user_id: int, note_id: int, answer_text: str, score: float) -> None:
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO user_notes_progress(user_id, note_id, homework_completed, hw_score, hw_answer_text)
               VALUES(?,?,1,?,?)
               ON CONFLICT(user_id, note_id) DO UPDATE SET
                   homework_completed=1,
                   hw_score=excluded.hw_score,
                   hw_answer_text=excluded.hw_answer_text,
                   updated_at=datetime('now')""",
            (user_id, note_id, score, answer_text),
        )


# ─────────────────────────────────────────────────────────
# Tournaments
# ─────────────────────────────────────────────────────────

def list_tournaments(status: str = "active") -> list:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM tournaments WHERE status=? ORDER BY start_time",
            (status,),
        ).fetchall()


def create_tournament(title: str, test_id: int, start_time: str,
                       end_time: str, prize: str, admin_id: int) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO tournaments(title, test_id, start_time, end_time, prize, created_by)
               VALUES(?,?,?,?,?,?)""",
            (title, test_id, start_time, end_time, prize, admin_id),
        )
        return cur.lastrowid


def save_tournament_result(tournament_id: int, user_id: int,
                            score: int, pct: float, attempt_id: int) -> None:
    with get_conn() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO tournament_results
               (tournament_id, user_id, score, percentage, attempt_id)
               VALUES(?,?,?,?,?)""",
            (tournament_id, user_id, score, pct, attempt_id),
        )


def get_tournament_leaderboard(tournament_id: int, limit: int = 10) -> list:
    with get_conn() as conn:
        return conn.execute(
            """SELECT u.full_name, tr.score, tr.percentage
               FROM tournament_results tr
               JOIN users u ON u.tg_id=tr.user_id
               WHERE tr.tournament_id=?
               ORDER BY tr.percentage DESC, tr.score DESC
               LIMIT ?""",
            (tournament_id, limit),
        ).fetchall()


# ─────────────────────────────────────────────────────────
# Group quizzes
# ─────────────────────────────────────────────────────────

def create_group_quiz(test_id: int, group_id: int, started_by: int,
                       question_order: list) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO group_quizzes
               (test_id, group_id, started_by, question_order, status)
               VALUES(?,?,?,?,'waiting')""",
            (test_id, group_id, started_by, json.dumps(question_order)),
        )
        return cur.lastrowid


def get_active_group_quiz(group_id: int) -> Optional[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM group_quizzes WHERE group_id=? AND status IN ('waiting','active') LIMIT 1",
            (group_id,),
        ).fetchone()


def update_group_quiz(quiz_id: int, data: dict) -> None:
    sets = ", ".join(f"{k}=?" for k in data)
    with get_conn() as conn:
        conn.execute(
            f"UPDATE group_quizzes SET {sets} WHERE id=?", [*data.values(), quiz_id]
        )


def join_group_quiz(quiz_id: int, user_id: int) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO group_quiz_participants(quiz_id, user_id) VALUES(?,?)",
            (quiz_id, user_id),
        )


def add_group_quiz_score(quiz_id: int, user_id: int, points: int) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE group_quiz_participants SET score=score+? WHERE quiz_id=? AND user_id=?",
            (points, quiz_id, user_id),
        )


def group_quiz_top(quiz_id: int) -> list:
    with get_conn() as conn:
        return conn.execute(
            """SELECT u.full_name, p.score, u.tg_id
               FROM group_quiz_participants p
               JOIN users u ON u.tg_id=p.user_id
               WHERE p.quiz_id=?
               ORDER BY p.score DESC LIMIT 10""",
            (quiz_id,),
        ).fetchall()


def has_answered_group_question(quiz_id: int, user_id: int, question_id: int) -> bool:
    with get_conn() as conn:
        return conn.execute(
            "SELECT 1 FROM group_quiz_answers WHERE quiz_id=? AND user_id=? AND question_id=?",
            (quiz_id, user_id, question_id),
        ).fetchone() is not None


def save_group_quiz_answer(quiz_id: int, user_id: int, question_id: int, is_correct: bool) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO group_quiz_answers(quiz_id, user_id, question_id, is_correct) VALUES(?,?,?,?)",
            (quiz_id, user_id, question_id, int(is_correct)),
        )


# ─────────────────────────────────────────────────────────
# Settings
# ─────────────────────────────────────────────────────────

def get_setting(key: str, default: str = "") -> str:
    with get_conn() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default


def set_setting(key: str, value: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO settings(key, value) VALUES(?,?)", (key, value)
        )


# ─────────────────────────────────────────────────────────
# Analytics helpers
# ─────────────────────────────────────────────────────────

def get_weak_topics(user_id: int, language: str, limit: int = 5) -> list[str]:
    """Return topic names where user's correct rate is lowest."""
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT aa.topic,
                      ROUND(AVG(CAST(aa.is_correct AS REAL))*100, 1) AS pct
               FROM attempt_answers aa
               JOIN test_attempts ta ON ta.id=aa.attempt_id
               JOIN tests t ON t.id=ta.test_id
               WHERE ta.user_id=? AND t.language=? AND aa.topic != ''
               GROUP BY aa.topic
               HAVING pct < 60
               ORDER BY pct ASC
               LIMIT ?""",
            (user_id, language, limit),
        ).fetchall()
    return [r["topic"] for r in rows]


def get_topic_stats(user_id: int) -> list:
    with get_conn() as conn:
        return conn.execute(
            """SELECT aa.topic,
                      COUNT(*) as total,
                      SUM(aa.is_correct) as correct,
                      ROUND(AVG(CAST(aa.is_correct AS REAL))*100, 1) AS pct
               FROM attempt_answers aa
               JOIN test_attempts ta ON ta.id=aa.attempt_id
               WHERE ta.user_id=? AND aa.topic != ''
               GROUP BY aa.topic
               ORDER BY pct ASC""",
            (user_id,),
        ).fetchall()


def get_user_stats(tg_id: int) -> dict:
    with get_conn() as conn:
        tests_done = conn.execute(
            "SELECT COUNT(*) as cnt FROM test_attempts WHERE user_id=? AND status='finished'",
            (tg_id,),
        ).fetchone()["cnt"]
        avg_row = conn.execute(
            """SELECT ROUND(AVG(CAST(correct_answers AS REAL)/
               NULLIF(correct_answers+wrong_answers+skipped_answers,0)*100),1) AS avg
               FROM test_attempts WHERE user_id=? AND status='finished' AND is_counted=1""",
            (tg_id,),
        ).fetchone()
        avg_pct = avg_row["avg"] or 0
    streak, best = get_user_streak(tg_id)
    refs = count_referrals(tg_id)
    return {
        "tests_done": tests_done,
        "avg_pct": avg_pct,
        "streak": streak,
        "best_streak": best,
        "refs": refs,
    }
