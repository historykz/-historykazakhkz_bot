import os
from dotenv import load_dotenv

load_dotenv()

# ── Telegram ──────────────────────────────────────────────
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
ADMIN_IDS: list[int] = [
    int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()
]

# ── Manager contact ───────────────────────────────────────
MANAGER_USERNAME: str = os.getenv("MANAGER_USERNAME", "@historyentk_bot")

# ── Database ──────────────────────────────────────────────
DB_PATH: str = os.getenv("DB_PATH", "ent_bot.db")

# ── Anti-spam ─────────────────────────────────────────────
SPAM_COOLDOWN_SECONDS: int = 3          # min seconds between test starts
BUTTON_COOLDOWN_SECONDS: float = 0.5   # min seconds between button presses

# ── Test runner ───────────────────────────────────────────
PAUSE_AFTER_MISSED: int = 2            # pause test after N missed questions in a row
DEFAULT_QUESTION_TIME: int = 30        # default seconds per question

# ── Daily ENT ─────────────────────────────────────────────
DAILY_DEFAULT_QUESTIONS: int = 10

# ── Referral ──────────────────────────────────────────────
REFERRAL_BONUS_THRESHOLDS: dict = {
    1: "one_test",
    3: "premium_test",
    10: "probnik",
}

# ── Pagination ────────────────────────────────────────────
PAGE_SIZE: int = 8                     # items per page in catalogs

# ── Notes protection ──────────────────────────────────────
# NOTE: Telegram Bot API allows protect_content=True to disable forwarding,
# but cannot prevent screenshots. Pages are kept small intentionally.
NOTE_PAGE_MAX_CHARS: int = 800         # max chars per note page chunk
