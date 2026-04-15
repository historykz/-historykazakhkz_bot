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


def lang_select_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang:ru"),
        InlineKeyboardButton(text="🇰🇿 Қазақша", callback_data="lang:kz"),
    ]])


def main_menu_kb(lang: str) -> ReplyKeyboardMarkup:
    b = ReplyKeyboardBuilder()
    rows = [
        [t("btn_tests", lang), t("btn_probniki", lang)],
        [t("btn_quizzes", lang), t("btn_notes", lang)],
        [t("btn_daily", lang), t("btn_duel", lang)],
        [t("btn_rating", lang), t("btn_my_results", lang)],
        [t("btn_profile", lang)],
        [t("btn_share_test", lang), t("btn_invite", lang)],
        [t("btn_support", lang), t("btn_help", lang)],
    ]
    for row in rows:
        b.row(*[KeyboardButton(text=btn) for btn in row])
    return b.as_markup(resize_keyboard=True)


def admin_panel_kb(lang: str = "ru") -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    buttons = [
        ("➕ Создать тест", "admin_create_test"),
        ("📥 Импорт Poll", "admin_poll_import"),
        ("📝 Импорт текстом", "admin_import_text"),
        ("📋 Мои тесты", "admin_my_tests"),
        ("📊 Статистика", "admin_stats"),
        ("🎫 Выдать доступ", "admin_give_access"),
        ("👑 Premium", "admin_premium"),
        ("🚫 Блокировка", "admin_block"),
        ("📢 Каналы", "admin_channels"),
        ("📤 Экспорт", "admin_export"),
        ("🏆 Турниры", "admin_tournaments"),
        ("📅 Daily ENT", "admin_daily_settings"),
        ("📚 Конспекты", "admin_notes"),
    ]
    for text, cbd in buttons:
        b.button(text=text, callback_data=cbd)
    b.adjust(2)
    return b.as_markup()


def yes_no_kb(suffix: str = "") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Да", callback_data=f"yes_{suffix}"),
        InlineKeyboardButton(text="❌ Нет", callback_data=f"no_{suffix}"),
    ]])


def back_kb(cb: str = "admin_panel") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="◀️ Назад", callback_data=cb)
    ]])


def test_type_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Обычный", callback_data="type_regular"),
         InlineKeyboardButton(text="📋 Пробник", callback_data="type_probnik")],
        [InlineKeyboardButton(text="🧠 Викторина", callback_data="type_quiz"),
         InlineKeyboardButton(text="📅 Daily", callback_data="type_daily")],
        [InlineKeyboardButton(text="⚔️ Дуэль", callback_data="type_duel"),
         InlineKeyboardButton(text="🏆 Турнир", callback_data="type_tournament")],
    ])


def test_status_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Активный", callback_data="status_active"),
         InlineKeyboardButton(text="👁 Скрытый", callback_data="status_hidden"),
         InlineKeyboardButton(text="🏁 Завершён", callback_data="status_finished")],
    ])


def lang_choice_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru"),
        InlineKeyboardButton(text="🇰🇿 Қазақша", callback_data="lang_kz"),
    ]])


def paid_type_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🆓 Бесплатный", callback_data="paid_no")],
        [InlineKeyboardButton(text="💰 Платный", callback_data="paid_yes")],
    ])


def note_paid_type_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🆓 Бесплатный", callback_data="note_free")],
        [InlineKeyboardButton(text="💰 Платный", callback_data="note_paid")],
        [InlineKeyboardButton(text="👑 Premium", callback_data="note_premium")],
    ])


def question_mode_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="💬 Inline", callback_data="qmode_inline"),
        InlineKeyboardButton(text="📊 Poll", callback_data="qmode_poll"),
    ]])


def difficulty_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="1 ⭐", callback_data="diff_1"),
        InlineKeyboardButton(text="2 ⭐", callback_data="diff_2"),
        InlineKeyboardButton(text="3 ⭐", callback_data="diff_3"),
    ]])


def test_manage_kb(test_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Вопросы", callback_data=f"test_questions_{test_id}"),
         InlineKeyboardButton(text="🔄 Статус", callback_data=f"test_toggle_status_{test_id}")],
        [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"test_delete_{test_id}")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_my_tests")],
    ])


def test_card_kb(lang: str, test_id: int, allow_group: bool = True) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="▶️ Начать тест", callback_data=f"test:start:{test_id}")
    if allow_group:
        b.button(text="👥 Групповой", callback_data=f"group_start_{test_id}")
    b.button(text="📨 Поделиться", callback_data=f"test:share:{test_id}")
    b.adjust(2)
    return b.as_markup()


def paid_test_kb(lang: str, test_id: int, manager: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Написать менеджеру", url=f"https://t.me/{manager.lstrip('@')}")],
        [InlineKeyboardButton(text="🔄 Проверить доступ", callback_data=f"test:check_access:{test_id}")],
    ])


def subscribe_kb(lang: str, channel_username: str, test_id: int) -> InlineKeyboardMarkup:
    username = channel_username.lstrip("@")
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Подписаться", url=f"https://t.me/{username}")],
        [InlineKeyboardButton(text="🔄 Проверить", callback_data=f"sub:check:{test_id}")],
    ])


def answer_kb(options: list, attempt_id: int, question_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    letters = ["A", "B", "C", "D", "E", "F"]
    for i, (opt_id, opt_text) in enumerate(options):
        b.button(text=f"{letters[i]}) {opt_text}", callback_data=f"ans:{attempt_id}:{question_id}:{opt_id}")
    b.adjust(1)
    return b.as_markup()


def pause_kb(lang: str, attempt_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="▶️ Продолжить", callback_data=f"pause:continue:{attempt_id}")],
        [InlineKeyboardButton(text="⏹ Завершить", callback_data=f"pause:finish:{attempt_id}")],
    ])


def group_pause_kb(lang: str, quiz_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="▶️ Продолжить", callback_data=f"gquiz_resume_{quiz_id}")],
        [InlineKeyboardButton(text="⏹ Завершить", callback_data=f"gquiz_finish_{quiz_id}")],
    ])


def group_quiz_join_kb(lang: str, quiz_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✋ Присоединиться", callback_data=f"quiz_join_{quiz_id}")],
        [InlineKeyboardButton(text="▶️ Запустить", callback_data=f"quiz_launch_{quiz_id}")],
    ])


def group_answer_kb(options: list, quiz_id: int, question_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    letters = ["A", "B", "C", "D"]
    for i, (opt_id, opt_text) in enumerate(options):
        b.button(text=f"{letters[i]}) {opt_text}", callback_data=f"gquiz_answer_{quiz_id}_{question_id}_{i}")
    b.adjust(1)
    return b.as_markup()


def note_card_kb(lang: str, note_id: int, has_hw: bool) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="📖 Читать", callback_data=f"read_note_{note_id}_1")
    if has_hw:
        b.button(text="📝 ДЗ", callback_data=f"start_hw_{note_id}")
    b.button(text="◀️ Назад", callback_data="section_notes")
    b.adjust(1)
    return b.as_markup()


def note_pages_kb(lang: str, note_id: int, cur_page: int, total_pages: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    if cur_page > 1:
        b.button(text="◀️", callback_data=f"read_note_{note_id}_{cur_page - 1}")
    if cur_page < total_pages:
        b.button(text="▶️", callback_data=f"read_note_{note_id}_{cur_page + 1}")
    b.button(text="◀️ Назад", callback_data=f"note_card_{note_id}")
    b.adjust(2)
    return b.as_markup()


def paid_note_kb(lang: str, note_id: int, manager: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Менеджеру", url=f"https://t.me/{manager.lstrip('@')}")],
        [InlineKeyboardButton(text="🔄 Проверить", callback_data=f"check_note_access_{note_id}")],
    ])


def premium_note_kb(lang: str, manager: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👑 Купить Premium", url=f"https://t.me/{manager.lstrip('@')}")],
    ])


def profile_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌐 Сменить язык", callback_data="change_language")],
        [InlineKeyboardButton(text="🛠 Поддержка", url=f"https://t.me/{MANAGER_USERNAME.lstrip('@')}")],
    ])


def pagination_kb(lang: str, scope: str, page: int, total: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    if page > 0:
        b.button(text="◀️", callback_data=f"page:{scope}:{page - 1}")
    b.button(text=f"{page + 1}", callback_data="noop")
    if (page + 1) * PAGE_SIZE < total:
        b.button(text="▶️", callback_data=f"page:{scope}:{page + 1}")
    b.adjust(3)
    return b.as_markup()


def duel_menu_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚡ Быстрая дуэль", callback_data="duel_quick")],
        [InlineKeyboardButton(text="📚 По предмету", callback_data="duel_by_subject")],
        [InlineKeyboardButton(text="📜 История", callback_data="duel_history")],
    ])


def cancel_duel_kb(lang: str, duel_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="❌ Отменить", callback_data=f"cancel_duel_{duel_id}")
    ]])


def duel_answer_kb(options: list, duel_id: int, question_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    letters = ["A", "B", "C", "D"]
    for i, (opt_id, opt_text) in enumerate(options):
        b.button(text=f"{letters[i]}) {opt_text}", callback_data=f"duel_answer_{duel_id}_{question_id}_{i}")
    b.adjust(1)
    return b.as_markup()


def daily_menu_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="▶️ Начать", callback_data="section_daily")],
        [InlineKeyboardButton(text="🔥 Streak", callback_data="daily_streak")],
        [InlineKeyboardButton(text="🏆 Рейтинг", callback_data="daily_rating")],
    ])


def poll_draft_options_kb(options: list, draft_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    letters = ["A", "B", "C", "D"]
    for i, opt in enumerate(options):
        b.button(text=f"{letters[i]}) {opt}", callback_data=f"resolve_correct_{i}")
    b.adjust(1)
    return b.as_markup()


def support_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="💬 Написать", url=f"https://t.me/{MANAGER_USERNAME.lstrip('@')}")
    ]])


def rating_scope_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌐 Общий", callback_data="rating_global"),
         InlineKeyboardButton(text="📅 Неделя", callback_data="rating_week")],
        [InlineKeyboardButton(text="📆 Месяц", callback_data="rating_month"),
         InlineKeyboardButton(text="⚔️ Дуэли", callback_data="rating_duels")],
    ])
