"""keyboards.py — all keyboards for the ENT bot."""
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from locales import get_text as t
from config import MANAGER_USERNAME, PAGE_SIZE


def remove_kb() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()


# ─────────────────────────────────────────────────────────
# Language selection (first start)
# ─────────────────────────────────────────────────────────

def lang_select_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang:ru"),
            InlineKeyboardButton(text="🇰🇿 Қазақша", callback_data="lang:kz"),
        ]
    ])


# ─────────────────────────────────────────────────────────
# Main menu
# ─────────────────────────────────────────────────────────

def main_menu_kb(lang: str) -> ReplyKeyboardMarkup:
    b = ReplyKeyboardBuilder()
    rows = [
        [t("btn_tests", lang),   t("btn_probniki", lang)],
        [t("btn_quizzes", lang), t("btn_notes", lang)],
        [t("btn_daily", lang),   t("btn_duel", lang)],
        [t("btn_rating", lang),  t("btn_my_results", lang)],
        [t("btn_profile", lang)],
        [t("btn_share_test", lang), t("btn_invite", lang)],
        [t("btn_support", lang), t("btn_help", lang)],
    ]
    for row in rows:
        b.row(*[KeyboardButton(text=btn) for btn in row])
    return b.as_markup(resize_keyboard=True)


# ─────────────────────────────────────────────────────────
# Admin panel
# ─────────────────────────────────────────────────────────

def admin_panel_kb(lang: str = "ru") -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    buttons = [
        ("btn_create_test",    "adm:create_test"),
        ("btn_import_poll",    "adm:import_poll"),
        ("btn_import_text",    "adm:import_text"),
        ("btn_my_tests",       "adm:my_tests"),
        ("btn_stats",          "adm:stats"),
        ("btn_give_access",    "adm:give_access"),
        ("btn_premium_admin",  "adm:premium"),
        ("btn_block",          "adm:block"),
        ("btn_run_quiz",       "adm:run_quiz"),
        ("btn_channels",       "adm:channels"),
        ("btn_export",         "adm:export"),
        ("btn_tournaments",    "adm:tournaments"),
        ("btn_ref_bonuses",    "adm:ref_bonuses"),
        ("btn_daily_settings", "adm:daily_settings"),
        ("btn_manage_notes",   "adm:notes"),
        ("btn_manage_hw",      "adm:hw"),
    ]
    for key, cbd in buttons:
        b.button(text=t(key, lang), callback_data=cbd)
    b.adjust(2)
    return b.as_markup()


# ─────────────────────────────────────────────────────────
# Yes / No
# ─────────────────────────────────────────────────────────

def yes_no_kb(lang: str, yes_cb: str, no_cb: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t("btn_yes", lang), callback_data=yes_cb),
        InlineKeyboardButton(text=t("btn_no",  lang), callback_data=no_cb),
    ]])


def back_kb(lang: str, cb: str = "back") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t("btn_back", lang), callback_data=cb)
    ]])


# ─────────────────────────────────────────────────────────
# Test type / status / mode selectors
# ─────────────────────────────────────────────────────────

def test_type_kb(lang: str) -> InlineKeyboardMarkup:
    types = [
        ("type_regular",    "tt:regular"),
        ("type_probnik",    "tt:probnik"),
        ("type_quiz",       "tt:quiz"),
        ("type_daily",      "tt:daily"),
        ("type_duel",       "tt:duel"),
        ("type_tournament", "tt:tournament"),
    ]
    b = InlineKeyboardBuilder()
    for key, cbd in types:
        b.button(text=t(key, lang), callback_data=cbd)
    b.adjust(2)
    return b.as_markup()


def test_status_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=t("status_active", lang),   callback_data="ts:active"),
            InlineKeyboardButton(text=t("status_hidden", lang),   callback_data="ts:hidden"),
            InlineKeyboardButton(text=t("status_finished", lang), callback_data="ts:finished"),
        ]
    ])


def lang_choice_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🇷🇺 Русский", callback_data="tl:ru"),
        InlineKeyboardButton(text="🇰🇿 Қазақша", callback_data="tl:kz"),
    ]])


def paid_type_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("btn_free", lang), callback_data="paid:0")],
        [InlineKeyboardButton(text=t("btn_paid", lang), callback_data="paid:1")],
    ])


def note_paid_type_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("btn_free",         lang), callback_data="npaid:free")],
        [InlineKeyboardButton(text=t("btn_paid",         lang), callback_data="npaid:paid")],
        [InlineKeyboardButton(text=t("btn_premium_only", lang), callback_data="npaid:premium")],
    ])


def question_mode_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=t("mode_inline", lang), callback_data="qm:inline"),
            InlineKeyboardButton(text=t("mode_poll",   lang), callback_data="qm:poll"),
        ]
    ])


def difficulty_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="1 — Лёгкий",  callback_data="diff:1"),
        InlineKeyboardButton(text="2 — Средний", callback_data="diff:2"),
        InlineKeyboardButton(text="3 — Сложный", callback_data="diff:3"),
    ]])


# ─────────────────────────────────────────────────────────
# Test card (user facing)
# ─────────────────────────────────────────────────────────

def test_card_kb(lang: str, test_id: int, allow_group: bool = True) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=t("btn_start_test", lang), callback_data=f"test:start:{test_id}")
    if allow_group:
        b.button(text=t("btn_group_test", lang), callback_data=f"test:group:{test_id}")
    b.button(text=t("btn_share", lang), callback_data=f"test:share:{test_id}")
    b.button(text=t("btn_details", lang), callback_data=f"test:details:{test_id}")
    b.adjust(2)
    return b.as_markup()


def paid_test_kb(lang: str, test_id: int, manager: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("btn_write_manager", lang), url=f"https://t.me/{manager.lstrip('@')}")],
        [InlineKeyboardButton(text=t("btn_check_access",  lang), callback_data=f"test:check_access:{test_id}")],
        [InlineKeyboardButton(text=t("btn_back",          lang), callback_data="back:catalog")],
    ])


def subscribe_kb(lang: str, channel_username: str, test_id: int) -> InlineKeyboardMarkup:
    username = channel_username.lstrip("@")
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("btn_subscribe", lang), url=f"https://t.me/{username}")],
        [InlineKeyboardButton(text=t("btn_check_sub", lang), callback_data=f"sub:check:{test_id}")],
    ])


# ─────────────────────────────────────────────────────────
# Quiz options (answer buttons)
# ─────────────────────────────────────────────────────────

def answer_kb(options: list, attempt_id: int, question_id: int) -> InlineKeyboardMarkup:
    """options: list of (option_id, option_text)"""
    b = InlineKeyboardBuilder()
    letters = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"]
    for i, (opt_id, opt_text) in enumerate(options):
        label = f"{letters[i]}) {opt_text}"
        b.button(text=label, callback_data=f"ans:{attempt_id}:{question_id}:{opt_id}")
    b.adjust(1)
    return b.as_markup()


def pause_kb(lang: str, attempt_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("btn_continue",    lang), callback_data=f"pause:continue:{attempt_id}")],
        [InlineKeyboardButton(text=t("btn_finish_test", lang), callback_data=f"pause:finish:{attempt_id}")],
    ])


def group_pause_kb(lang: str, quiz_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("btn_continue_quiz", lang), callback_data=f"gquiz:continue:{quiz_id}")],
        [InlineKeyboardButton(text=t("btn_finish_quiz",   lang), callback_data=f"gquiz:finish:{quiz_id}")],
    ])


def group_quiz_join_kb(lang: str, quiz_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("btn_join_quiz",  lang), callback_data=f"gquiz:join:{quiz_id}")],
        [InlineKeyboardButton(text=t("btn_start_quiz", lang), callback_data=f"gquiz:start:{quiz_id}")],
    ])


def group_answer_kb(options: list, quiz_id: int, question_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    letters = ["A", "B", "C", "D", "E", "F", "G", "H"]
    for i, (opt_id, opt_text) in enumerate(options):
        label = f"{letters[i]}) {opt_text}"
        b.button(text=label, callback_data=f"gans:{quiz_id}:{question_id}:{opt_id}")
    b.adjust(1)
    return b.as_markup()


# ─────────────────────────────────────────────────────────
# Note card
# ─────────────────────────────────────────────────────────

def note_card_kb(lang: str, note_id: int, has_hw: bool) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=t("btn_read_note", lang), callback_data=f"note:read:{note_id}")
    if has_hw:
        b.button(text=t("btn_start_hw", lang), callback_data=f"note:hw:{note_id}")
    b.button(text=t("btn_back", lang), callback_data="back:notes")
    b.adjust(1)
    return b.as_markup()


def note_pages_kb(lang: str, note_id: int, cur_page: int, total_pages: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    if cur_page > 1:
        b.button(text=t("btn_prev_page", lang), callback_data=f"notep:{note_id}:{cur_page - 1}")
    if cur_page < total_pages:
        b.button(text=t("btn_next_page", lang), callback_data=f"notep:{note_id}:{cur_page + 1}")
    b.button(text=t("btn_back", lang), callback_data=f"note:menu:{note_id}")
    b.adjust(2)
    return b.as_markup()


def paid_note_kb(lang: str, note_id: int, manager: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("btn_write_manager", lang), url=f"https://t.me/{manager.lstrip('@')}")],
        [InlineKeyboardButton(text=t("btn_check_access",  lang), callback_data=f"note:check_access:{note_id}")],
        [InlineKeyboardButton(text=t("btn_back",          lang), callback_data="back:notes")],
    ])


def premium_note_kb(lang: str, manager: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("btn_buy_premium",   lang), url=f"https://t.me/{manager.lstrip('@')}")],
        [InlineKeyboardButton(text=t("btn_write_manager", lang), url=f"https://t.me/{manager.lstrip('@')}")],
    ])


# ─────────────────────────────────────────────────────────
# Profile
# ─────────────────────────────────────────────────────────

def profile_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("btn_change_lang", lang), callback_data="profile:change_lang")],
        [InlineKeyboardButton(text=t("btn_support",     lang), url=f"https://t.me/{MANAGER_USERNAME.lstrip('@')}")],
    ])


# ─────────────────────────────────────────────────────────
# Pagination
# ─────────────────────────────────────────────────────────

def pagination_kb(lang: str, scope: str, page: int, total: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    if page > 0:
        b.button(text="◀️", callback_data=f"page:{scope}:{page - 1}")
    b.button(text=f"{page + 1}/{(total // PAGE_SIZE) + 1}", callback_data="noop")
    if (page + 1) * PAGE_SIZE < total:
        b.button(text="▶️", callback_data=f"page:{scope}:{page + 1}")
    b.adjust(3)
    return b.as_markup()


# ─────────────────────────────────────────────────────────
# Duel
# ─────────────────────────────────────────────────────────

def duel_menu_kb(lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=t("btn_quick_duel",    lang), callback_data="duel:quick")
    b.button(text=t("btn_subject_duel",  lang), callback_data="duel:subject")
    b.button(text=t("btn_duel_history",  lang), callback_data="duel:history")
    b.adjust(1)
    return b.as_markup()


def cancel_duel_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t("btn_cancel_duel", lang), callback_data="duel:cancel")
    ]])


def duel_answer_kb(options: list, duel_id: int, question_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    letters = ["A", "B", "C", "D", "E", "F", "G", "H"]
    for i, (opt_id, opt_text) in enumerate(options):
        b.button(text=f"{letters[i]}) {opt_text}", callback_data=f"dans:{duel_id}:{question_id}:{opt_id}")
    b.adjust(1)
    return b.as_markup()


# ─────────────────────────────────────────────────────────
# Daily ENT
# ─────────────────────────────────────────────────────────

def daily_menu_kb(lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=t("btn_start_daily",  lang), callback_data="daily:start")
    b.button(text=t("btn_daily_streak", lang), callback_data="daily:streak")
    b.button(text=t("btn_daily_rating", lang), callback_data="daily:rating")
    b.adjust(1)
    return b.as_markup()


# ─────────────────────────────────────────────────────────
# Poll draft resolve
# ─────────────────────────────────────────────────────────

def poll_draft_options_kb(options: list, draft_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    letters = ["A", "B", "C", "D", "E", "F", "G", "H"]
    for i, opt in enumerate(options):
        b.button(text=f"{letters[i]}) {opt}", callback_data=f"draft:correct:{draft_id}:{i}")
    b.adjust(1)
    return b.as_markup()


# ─────────────────────────────────────────────────────────
# Admin: tests list item
# ─────────────────────────────────────────────────────────

def test_manage_kb(lang: str, test_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="✏️ Редактировать", callback_data=f"adm_test:edit:{test_id}")
    b.button(text="🗑 Удалить",       callback_data=f"adm_test:delete:{test_id}")
    b.button(text="📋 Вопросы",       callback_data=f"adm_test:questions:{test_id}")
    b.button(text="📊 Статистика",    callback_data=f"adm_test:stats:{test_id}")
    b.button(text="📤 Экспорт",       callback_data=f"adm_test:export:{test_id}")
    b.button(text=t("btn_back", lang), callback_data="adm:my_tests")
    b.adjust(2)
    return b.as_markup()


# ─────────────────────────────────────────────────────────
# Support shortcut
# ─────────────────────────────────────────────────────────

def support_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t("btn_support", lang),
                             url=f"https://t.me/{MANAGER_USERNAME.lstrip('@')}")
    ]])


# ─────────────────────────────────────────────────────────
# Rating scope selector
# ─────────────────────────────────────────────────────────

def rating_scope_kb(lang: str) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for label, cb in [("Общий", "rating:global"), ("Неделя", "rating:week"),
                       ("Месяц", "rating:month"), ("Друзья", "rating:friends")]:
        b.button(text=label, callback_data=cb)
    b.adjust(2)
    return b.as_markup()
