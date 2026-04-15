"""states.py — aiogram FSM state groups."""
from aiogram.fsm.state import State, StatesGroup


class LangSelect(StatesGroup):
    choosing = State()


# ── Admin: create test ────────────────────────────────────
class CreateTest(StatesGroup):
    title       = State()
    description = State()
    subject     = State()
    class_num   = State()
    category    = State()
    language    = State()
    test_type   = State()
    status      = State()
    paid        = State()
    price       = State()
    q_count     = State()
    attempt_limit = State()
    first_attempt_only = State()
    deadline    = State()
    shuffle_q   = State()
    shuffle_o   = State()
    show_correct = State()
    show_explanation = State()
    q_time      = State()
    require_sub  = State()
    channel_username = State()
    allow_group  = State()
    allow_duel   = State()
    allow_daily  = State()
    allow_tournament = State()
    q_mode       = State()
    adaptive     = State()
    confirm      = State()


# ── Admin: add question manually ─────────────────────────
class AddQuestion(StatesGroup):
    selecting_test = State()
    text       = State()
    options    = State()         # expects 4 lines
    correct    = State()
    explanation = State()
    topic      = State()
    difficulty = State()
    score      = State()
    image      = State()
    confirm    = State()


# ── Admin: text import ───────────────────────────────────
class TextImport(StatesGroup):
    select_test = State()
    waiting_text = State()


# ── Admin: poll import ───────────────────────────────────
class PollImport(StatesGroup):
    select_test = State()
    waiting_polls = State()
    resolve_correct = State()   # when correct_option_id unknown


# ── Admin: resolve poll draft ─────────────────────────────
class ResolveDraft(StatesGroup):
    waiting = State()


# ── Admin: give access ────────────────────────────────────
class GiveAccess(StatesGroup):
    enter_user_id = State()
    select_type   = State()   # test or note
    select_item   = State()


# ── Admin: premium ────────────────────────────────────────
class AdminPremium(StatesGroup):
    enter_user_id = State()
    select_action = State()   # grant / revoke
    enter_days    = State()


# ── Admin: block ─────────────────────────────────────────
class AdminBlock(StatesGroup):
    enter_user_id = State()
    action        = State()   # block / unblock


# ── Admin: channel management ────────────────────────────
class AdminChannel(StatesGroup):
    enter_username = State()
    select_scope   = State()
    select_test    = State()


# ── Admin: create note ────────────────────────────────────
class CreateNote(StatesGroup):
    title       = State()
    description = State()
    subject     = State()
    category    = State()
    language    = State()
    topic       = State()
    difficulty  = State()
    paid_type   = State()   # free / paid / premium
    price       = State()
    pages       = State()   # multi-message page input
    confirm     = State()


# ── Admin: add homework ───────────────────────────────────
class AddHomework(StatesGroup):
    select_note  = State()
    hw_type      = State()
    select_test  = State()   # if type==test
    open_prompt  = State()   # if type==open
    keywords     = State()
    auto_check   = State()


# ── Admin: generate test from note ───────────────────────
class GenerateTest(StatesGroup):
    select_note  = State()
    q_count      = State()
    difficulty   = State()
    confirm      = State()


# ── Admin: tournament ─────────────────────────────────────
class CreateTournament(StatesGroup):
    title       = State()
    select_test = State()
    start_time  = State()
    end_time    = State()
    prize       = State()
    confirm     = State()


# ── Admin: export ─────────────────────────────────────────
class ExportResults(StatesGroup):
    select_test = State()


# ── Admin: daily settings ─────────────────────────────────
class DailySettings(StatesGroup):
    q_count   = State()
    mode      = State()
    subjects  = State()


# ── User: test session ────────────────────────────────────
class TestSession(StatesGroup):
    running = State()


# ── User: group quiz launch ───────────────────────────────
class GroupQuizLaunch(StatesGroup):
    select_test = State()
    waiting_participants = State()


# ── User: duel ────────────────────────────────────────────
class DuelSearch(StatesGroup):
    searching     = State()
    select_subject = State()
    in_duel       = State()


# ── User: daily ───────────────────────────────────────────
class DailySession(StatesGroup):
    running = State()


# ── User: change language ─────────────────────────────────
class ChangeLang(StatesGroup):
    choosing = State()


# ── User: HW open answer ─────────────────────────────────
class HomeworkAnswer(StatesGroup):
    note_id  = State()
    waiting  = State()
