from aiogram.fsm.state import State, StatesGroup


class LangSelect(StatesGroup):
    choosing = State()


class CreateTest(StatesGroup):
    title = State()
    description = State()
    subject = State()
    grade = State()
    category = State()
    language = State()
    test_type = State()
    status = State()
    is_paid = State()
    price = State()
    question_count = State()
    attempt_limit = State()
    first_attempt_only = State()
    deadline = State()
    shuffle_questions = State()
    shuffle_options = State()
    show_answers = State()
    show_explanations = State()
    time_per_question = State()
    require_subscription = State()
    allow_group = State()
    allow_duel = State()
    allow_daily = State()
    allow_tournament = State()
    question_mode = State()


class AddQuestion(StatesGroup):
    question_text = State()
    option_a = State()
    option_b = State()
    option_c = State()
    option_d = State()
    correct_option = State()
    explanation = State()
    topic = State()
    difficulty = State()
    points = State()


class TextImport(StatesGroup):
    waiting_text = State()


class PollImport(StatesGroup):
    waiting_polls = State()


class ResolveDraft(StatesGroup):
    selecting_correct = State()


class GiveAccess(StatesGroup):
    user_id = State()
    access_type = State()
    item_id = State()


class AdminPremium(StatesGroup):
    user_id = State()
    action = State()


class AdminBlock(StatesGroup):
    user_id = State()
    action = State()


class AdminChannel(StatesGroup):
    username = State()
    is_global = State()


class CreateNote(StatesGroup):
    title = State()
    description = State()
    subject = State()
    category = State()
    topic = State()
    language = State()
    paid_type = State()
    price = State()
    difficulty = State()
    content = State()
    add_page = State()


class AddHomework(StatesGroup):
    hw_type = State()
    test_id = State()
    open_prompt = State()


class GenerateTest(StatesGroup):
    select_note = State()
    q_count = State()


class CreateTournament(StatesGroup):
    title = State()
    test_id = State()
    start_date = State()
    end_date = State()
    prize = State()


class ExportResults(StatesGroup):
    select_test = State()


class DailySettings(StatesGroup):
    question_count = State()
    mode = State()


class TestSession(StatesGroup):
    running = State()


class GroupQuizLaunch(StatesGroup):
    select_test = State()


class DuelSearch(StatesGroup):
    searching = State()


class DailySession(StatesGroup):
    running = State()


class ChangeLang(StatesGroup):
    selecting = State()


class HomeworkAnswer(StatesGroup):
    typing = State()
