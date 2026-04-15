import logging
import csv
import io
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from config import ADMIN_IDS
from database import (
    create_test, get_test, list_tests, update_test, delete_test,
    add_question, add_option, get_questions, get_question, get_options,
    delete_question, update_question, count_questions,
    grant_test_access, grant_note_access,
    has_premium, grant_premium, revoke_premium,
    get_user, block_user, unblock_user,
    get_global_channels, add_channel, list_channels, delete_channel,
    get_leaderboard, get_user_stats,
    list_tournaments, create_tournament,
    get_setting, set_setting,
    list_notes, create_note, get_note, add_note_page, get_note_homework,
    add_note_homework, get_attempt_answers, count_user_attempts,
    save_poll_draft, get_poll_drafts_needing_answer, resolve_poll_draft
)
from filters import IsAdmin
from states import (
    CreateTest, AddQuestion, TextImport, PollImport,
    ResolveDraft, GiveAccess, AdminPremium, AdminBlock,
    AdminChannel, CreateNote, AddHomework, CreateTournament,
    ExportResults, DailySettings
)
from keyboards import (
    admin_panel_kb, yes_no_kb, back_kb, test_type_kb, test_status_kb,
    lang_choice_kb, paid_type_kb, note_paid_type_kb, question_mode_kb,
    difficulty_kb, test_manage_kb, pagination_kb
)
from locales import get_text
from utils import parse_text_questions, today_str

logger = logging.getLogger(__name__)
router = Router()
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())

@router.message(Command("admin"))
async def cmd_admin(message: Message):
    await message.answer("🛠 Панель администратора", reply_markup=admin_panel_kb())

@router.callback_query(F.data == "admin_panel")
async def cb_admin_panel(cq: CallbackQuery):
    await cq.message.edit_text("🛠 Панель администратора", reply_markup=admin_panel_kb())
    await cq.answer()

@router.callback_query(F.data == "admin_create_test")
async def cb_create_test_start(cq: CallbackQuery, state: FSMContext):
    await cq.message.edit_text("📝 Введите название теста:")
    await state.set_state(CreateTest.title)
    await cq.answer()

@router.message(CreateTest.title)
async def ct_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text.strip())
    await message.answer("📄 Введите описание теста:")
    await state.set_state(CreateTest.description)

@router.message(CreateTest.description)
async def ct_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text.strip())
    await message.answer("📚 Введите предмет:")
    await state.set_state(CreateTest.subject)

@router.message(CreateTest.subject)
async def ct_subject(message: Message, state: FSMContext):
    await state.update_data(subject=message.text.strip())
    await message.answer("🏫 Введите класс (например: 11):")
    await state.set_state(CreateTest.grade)

@router.message(CreateTest.grade)
async def ct_grade(message: Message, state: FSMContext):
    await state.update_data(grade=message.text.strip())
    await message.answer("📂 Введите категорию (ЕНТ, Пробник, Тренировка):")
    await state.set_state(CreateTest.category)

@router.message(CreateTest.category)
async def ct_category(message: Message, state: FSMContext):
    await state.update_data(category=message.text.strip())
    await message.answer("🌐 Выберите язык теста:", reply_markup=lang_choice_kb())
    await state.set_state(CreateTest.language)

@router.callback_query(CreateTest.language, F.data.in_(["lang_ru", "lang_kz"]))
async def ct_language(cq: CallbackQuery, state: FSMContext):
    lang = "ru" if cq.data == "lang_ru" else "kz"
    await state.update_data(language=lang)
    await cq.message.edit_text("📋 Выберите тип теста:", reply_markup=test_type_kb())
    await state.set_state(CreateTest.test_type)
    await cq.answer()

@router.callback_query(CreateTest.test_type)
async def ct_test_type(cq: CallbackQuery, state: FSMContext):
    valid = ["type_regular","type_probnik","type_quiz","type_daily","type_duel","type_tournament"]
    if cq.data not in valid:
        await cq.answer("Выберите тип из списка")
        return
    await state.update_data(test_type=cq.data.replace("type_",""))
    await cq.message.edit_text("📊 Выберите статус:", reply_markup=test_status_kb())
    await state.set_state(CreateTest.status)
    await cq.answer()

@router.callback_query(CreateTest.status)
async def ct_status(cq: CallbackQuery, state: FSMContext):
    if cq.data not in ["status_active","status_hidden","status_finished"]:
        await cq.answer()
        return
    await state.update_data(status=cq.data.replace("status_",""))
    await cq.message.edit_text("💰 Платный или бесплатный?", reply_markup=paid_type_kb())
    await state.set_state(CreateTest.is_paid)
    await cq.answer()

@router.callback_query(CreateTest.is_paid, F.data.in_(["paid_yes","paid_no"]))
async def ct_is_paid(cq: CallbackQuery, state: FSMContext):
    is_paid = cq.data == "paid_yes"
    await state.update_data(is_paid=is_paid)
    if is_paid:
        await cq.message.edit_text("💵 Введите цену (тенге):")
        await state.set_state(CreateTest.price)
    else:
        await state.update_data(price=0)
        await cq.message.edit_text("🔢 Количество вопросов (0 = все):")
        await state.set_state(CreateTest.question_count)
    await cq.answer()

@router.message(CreateTest.price)
async def ct_price(message: Message, state: FSMContext):
    try:
        price = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Введите число:")
        return
    await state.update_data(price=price)
    await message.answer("🔢 Количество вопросов (0 = все):")
    await state.set_state(CreateTest.question_count)

@router.message(CreateTest.question_count)
async def ct_question_count(message: Message, state: FSMContext):
    try:
        qc = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Введите число:")
        return
    await state.update_data(question_count=qc)
    await message.answer("🔁 Лимит попыток (0 = без лимита):")
    await state.set_state(CreateTest.attempt_limit)

@router.message(CreateTest.attempt_limit)
async def ct_attempt_limit(message: Message, state: FSMContext):
    try:
        al = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Введите число:")
        return
    await state.update_data(attempt_limit=al)
    await message.answer("📌 Учитывать только первую попытку?", reply_markup=yes_no_kb("first_attempt"))
    await state.set_state(CreateTest.first_attempt_only)

@router.callback_query(CreateTest.first_attempt_only)
async def ct_first_attempt(cq: CallbackQuery, state: FSMContext):
    await state.update_data(first_attempt_only=cq.data=="yes_first_attempt")
    await cq.message.edit_text("📅 Дедлайн (YYYY-MM-DD или 'нет'):")
    await state.set_state(CreateTest.deadline)
    await cq.answer()

@router.message(CreateTest.deadline)
async def ct_deadline(message: Message, state: FSMContext):
    txt = message.text.strip()
    deadline = None
    if txt.lower() not in ("нет","жоқ","-","no"):
        try:
            deadline = datetime.strptime(txt,"%Y-%m-%d").isoformat()
        except ValueError:
            await message.answer("❌ Формат: YYYY-MM-DD или 'нет'")
            return
    await state.update_data(deadline=deadline)
    await message.answer("🔀 Перемешивать вопросы?", reply_markup=yes_no_kb("shuffle_q"))
    await state.set_state(CreateTest.shuffle_questions)

@router.callback_query(CreateTest.shuffle_questions)
async def ct_shuffle_q(cq: CallbackQuery, state: FSMContext):
    await state.update_data(shuffle_questions=cq.data=="yes_shuffle_q")
    await cq.message.edit_text("🔀 Перемешивать варианты?", reply_markup=yes_no_kb("shuffle_o"))
    await state.set_state(CreateTest.shuffle_options)
    await cq.answer()

@router.callback_query(CreateTest.shuffle_options)
async def ct_shuffle_o(cq: CallbackQuery, state: FSMContext):
    await state.update_data(shuffle_options=cq.data=="yes_shuffle_o")
    await cq.message.edit_text("✅ Показывать правильные ответы?", reply_markup=yes_no_kb("show_ans"))
    await state.set_state(CreateTest.show_answers)
    await cq.answer()

@router.callback_query(CreateTest.show_answers)
async def ct_show_ans(cq: CallbackQuery, state: FSMContext):
    await state.update_data(show_answers=cq.data=="yes_show_ans")
    await cq.message.edit_text("💡 Показывать объяснения?", reply_markup=yes_no_kb("show_exp"))
    await state.set_state(CreateTest.show_explanations)
    await cq.answer()

@router.callback_query(CreateTest.show_explanations)
async def ct_show_exp(cq: CallbackQuery, state: FSMContext):
    await state.update_data(show_explanations=cq.data=="yes_show_exp")
    await cq.message.edit_text("⏱ Время на вопрос (секунды, минимум 5):")
    await state.set_state(CreateTest.time_per_question)
    await cq.answer()

@router.message(CreateTest.time_per_question)
async def ct_time_per_q(message: Message, state: FSMContext):
    try:
        t = int(message.text.strip())
        if t < 5: raise ValueError
    except ValueError:
        await message.answer("❌ Введите число >= 5:")
        return
    await state.update_data(time_per_question=t)
    await message.answer("📢 Требуется подписка?", reply_markup=yes_no_kb("req_sub"))
    await state.set_state(CreateTest.require_subscription)

@router.callback_query(CreateTest.require_subscription)
async def ct_req_sub(cq: CallbackQuery, state: FSMContext):
    await state.update_data(require_subscription=cq.data=="yes_req_sub")
    await cq.message.edit_text("👥 Разрешить в группе?", reply_markup=yes_no_kb("allow_group"))
    await state.set_state(CreateTest.allow_group)
    await cq.answer()

@router.callback_query(CreateTest.allow_group)
async def ct_allow_group(cq: CallbackQuery, state: FSMContext):
    await state.update_data(allow_group=cq.data=="yes_allow_group")
    await cq.message.edit_text("⚔️ Разрешить для дуэлей?", reply_markup=yes_no_kb("allow_duel"))
    await state.set_state(CreateTest.allow_duel)
    await cq.answer()

@router.callback_query(CreateTest.allow_duel)
async def ct_allow_duel(cq: CallbackQuery, state: FSMContext):
    await state.update_data(allow_duel=cq.data=="yes_allow_duel")
    await cq.message.edit_text("📅 Разрешить для Daily ENT?", reply_markup=yes_no_kb("allow_daily"))
    await state.set_state(CreateTest.allow_daily)
    await cq.answer()

@router.callback_query(CreateTest.allow_daily)
async def ct_allow_daily(cq: CallbackQuery, state: FSMContext):
    await state.update_data(allow_daily=cq.data=="yes_allow_daily")
    await cq.message.edit_text("🏆 Разрешить для турниров?", reply_markup=yes_no_kb("allow_tournament"))
    await state.set_state(CreateTest.allow_tournament)
    await cq.answer()

@router.callback_query(CreateTest.allow_tournament)
async def ct_allow_tournament(cq: CallbackQuery, state: FSMContext):
    await state.update_data(allow_tournament=cq.data=="yes_allow_tournament")
    await cq.message.edit_text("🖥 Режим вопросов:", reply_markup=question_mode_kb())
    await state.set_state(CreateTest.question_mode)
    await cq.answer()

@router.callback_query(CreateTest.question_mode)
async def ct_question_mode(cq: CallbackQuery, state: FSMContext):
    if cq.data not in ["qmode_inline","qmode_poll"]:
        await cq.answer()
        return
    mode = cq.data.replace("qmode_","")
    await state.update_data(question_mode=mode)
    data = await state.get_data()
    try:
        test_id = create_test(
            title=data["title"], description=data.get("description",""),
            subject=data.get("subject",""), grade=data.get("grade",""),
            category=data.get("category",""), language=data.get("language","ru"),
            test_type=data.get("test_type","regular"), status=data.get("status","active"),
            is_paid=data.get("is_paid",False), price=data.get("price",0),
            question_count=data.get("question_count",0), attempt_limit=data.get("attempt_limit",0),
            first_attempt_only=data.get("first_attempt_only",True), deadline=data.get("deadline"),
            shuffle_questions=data.get("shuffle_questions",True), shuffle_options=data.get("shuffle_options",True),
            show_answers=data.get("show_answers",False), show_explanations=data.get("show_explanations",False),
            time_per_question=data.get("time_per_question",30), require_subscription=data.get("require_subscription",False),
            allow_group=data.get("allow_group",True), allow_duel=data.get("allow_duel",False),
            allow_daily=data.get("allow_daily",False), allow_tournament=data.get("allow_tournament",False),
            question_mode=mode, created_by=cq.from_user.id
        )
        await cq.message.edit_text(
            f"✅ Тест создан! ID: {test_id}\n\nДобавьте вопросы:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="➕ Добавить вручную", callback_data=f"add_question_{test_id}")],
                [InlineKeyboardButton(text="📝 Импорт текстом", callback_data=f"text_import_{test_id}")],
                [InlineKeyboardButton(text="◀️ В панель", callback_data="admin_panel")]
            ])
        )
    except Exception as e:
        await cq.message.edit_text(f"❌ Ошибка: {e}")
    await state.clear()
    await cq.answer()

@router.callback_query(F.data.startswith("add_question_"))
async def cb_add_question(cq: CallbackQuery, state: FSMContext):
    test_id = int(cq.data.split("_")[-1])
    await state.update_data(current_test_id=test_id)
    await cq.message.edit_text("❓ Введите текст вопроса:")
    await state.set_state(AddQuestion.question_text)
    await cq.answer()

@router.message(AddQuestion.question_text)
async def aq_text(message: Message, state: FSMContext):
    await state.update_data(q_text=message.text.strip())
    await message.answer("🅰️ Вариант A:")
    await state.set_state(AddQuestion.option_a)

@router.message(AddQuestion.option_a)
async def aq_opt_a(message: Message, state: FSMContext):
    await state.update_data(opt_a=message.text.strip())
    await message.answer("🅱️ Вариант B:")
    await state.set_state(AddQuestion.option_b)

@router.message(AddQuestion.option_b)
async def aq_opt_b(message: Message, state: FSMContext):
    await state.update_data(opt_b=message.text.strip())
    await message.answer("🅲 Вариант C:")
    await state.set_state(AddQuestion.option_c)

@router.message(AddQuestion.option_c)
async def aq_opt_c(message: Message, state: FSMContext):
    await state.update_data(opt_c=message.text.strip())
    await message.answer("🅳 Вариант D:")
    await state.set_state(AddQuestion.option_d)

@router.message(AddQuestion.option_d)
async def aq_opt_d(message: Message, state: FSMContext):
    await state.update_data(opt_d=message.text.strip())
    await message.answer("✅ Правильный вариант?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="A", callback_data="correct_0"),
            InlineKeyboardButton(text="B", callback_data="correct_1"),
            InlineKeyboardButton(text="C", callback_data="correct_2"),
            InlineKeyboardButton(text="D", callback_data="correct_3"),
        ]]))
    await state.set_state(AddQuestion.correct_option)

@router.callback_query(AddQuestion.correct_option, F.data.startswith("correct_"))
async def aq_correct(cq: CallbackQuery, state: FSMContext):
    await state.update_data(correct_idx=int(cq.data.split("_")[1]))
    await cq.message.edit_text("💡 Объяснение (или '-'):")
    await state.set_state(AddQuestion.explanation)
    await cq.answer()

@router.message(AddQuestion.explanation)
async def aq_explanation(message: Message, state: FSMContext):
    exp = message.text.strip()
    if exp == "-": exp = ""
    await state.update_data(explanation=exp)
    await message.answer("🏷 Тема вопроса:")
    await state.set_state(AddQuestion.topic)

@router.message(AddQuestion.topic)
async def aq_topic(message: Message, state: FSMContext):
    await state.update_data(topic=message.text.strip())
    await message.answer("⚖️ Сложность:", reply_markup=difficulty_kb())
    await state.set_state(AddQuestion.difficulty)

@router.callback_query(AddQuestion.difficulty, F.data.startswith("diff_"))
async def aq_difficulty(cq: CallbackQuery, state: FSMContext):
    await state.update_data(difficulty=int(cq.data.split("_")[1]))
    await cq.message.edit_text("💯 Баллы за вопрос (например: 1):")
    await state.set_state(AddQuestion.points)
    await cq.answer()

@router.message(AddQuestion.points)
async def aq_points(message: Message, state: FSMContext):
    try:
        pts = float(message.text.strip())
    except ValueError:
        await message.answer("❌ Введите число:")
        return
    data = await state.get_data()
    test_id = data["current_test_id"]
    opts = [data["opt_a"],data["opt_b"],data["opt_c"],data["opt_d"]]
    correct_idx = data["correct_idx"]
    try:
        q_id = add_question(test_id=test_id, text=data["q_text"],
            explanation=data.get("explanation",""), topic=data.get("topic",""),
            difficulty=data.get("difficulty",1), points=pts)
        for i, opt_text in enumerate(opts):
            add_option(q_id, opt_text, is_correct=(i==correct_idx))
        total = count_questions(test_id)
        await message.answer(f"✅ Вопрос добавлен! Всего: {total}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="➕ Ещё вопрос", callback_data=f"add_question_{test_id}")],
                [InlineKeyboardButton(text="◀️ В панель", callback_data="admin_panel")]
            ]))
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")
    await state.clear()

@router.callback_query(F.data.startswith("text_import_"))
async def cb_text_import(cq: CallbackQuery, state: FSMContext):
    test_id = int(cq.data.split("_")[-1])
    await state.update_data(import_test_id=test_id)
    await cq.message.edit_text(
        "📝 Отправьте вопросы в формате:\n\nВопрос:\nA) Вариант\nB) Вариант\nC) Вариант\nD) Вариант *\n\n* = правильный ответ")
    await state.set_state(TextImport.waiting_text)
    await cq.answer()

@router.message(TextImport.waiting_text)
async def ti_receive(message: Message, state: FSMContext):
    data = await state.get_data()
    test_id = data["import_test_id"]
    questions, errors = parse_text_questions(message.text or "")
    saved = 0
    for q in questions:
        try:
            q_id = add_question(test_id=test_id, text=q["text"], explanation="", topic="", difficulty=1, points=1.0)
            for i, opt in enumerate(q["options"]):
                add_option(q_id, opt["text"], is_correct=opt["is_correct"])
            saved += 1
        except Exception as e:
            errors.append(f"DB error: {e}")
    result = f"✅ Добавлено: {saved}\n❌ Ошибок: {len(errors)}"
    if errors:
        result += "\n\n" + "\n".join(errors[:5])
    await message.answer(result,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📥 Ещё импорт", callback_data=f"text_import_{test_id}")],
            [InlineKeyboardButton(text="◀️ В панель", callback_data="admin_panel")]
        ]))
    await state.clear()

@router.callback_query(F.data == "admin_my_tests")
async def cb_my_tests(cq: CallbackQuery):
    await show_tests_page(cq.message, 0, edit=True)
    await cq.answer()

async def show_tests_page(message, page, edit=False):
    tests = list_tests(limit=10, offset=page*10)
    if not tests:
        text, kb = "📋 Тестов нет.", back_kb("admin_panel")
    else:
        text = f"📋 Тесты (стр. {page+1}):\n\n"
        btns = []
        for t in tests:
            icon = {"active":"✅","hidden":"👁","finished":"🏁"}.get(t["status"],"❓")
            btns.append([InlineKeyboardButton(text=f"{icon} {t['title'][:35]}", callback_data=f"admin_test_{t['id']}")])
        nav = []
        if page > 0: nav.append(InlineKeyboardButton(text="◀️", callback_data=f"tests_page_{page-1}"))
        nav.append(InlineKeyboardButton(text="◀️ Назад", callback_data="admin_panel"))
        if len(tests)==10: nav.append(InlineKeyboardButton(text="▶️", callback_data=f"tests_page_{page+1}"))
        btns.append(nav)
        kb = InlineKeyboardMarkup(inline_keyboard=btns)
    if edit: await message.edit_text(text, reply_markup=kb)
    else: await message.answer(text, reply_markup=kb)

@router.callback_query(F.data.startswith("tests_page_"))
async def cb_tests_page(cq: CallbackQuery):
    await show_tests_page(cq.message, int(cq.data.split("_")[-1]), edit=True)
    await cq.answer()

@router.callback_query(F.data.startswith("admin_test_"))
async def cb_admin_test(cq: CallbackQuery):
    test_id = int(cq.data.split("_")[-1])
    test = get_test(test_id)
    if not test:
        await cq.message.edit_text("❌ Тест не найден.")
        return
    q_count = count_questions(test_id)
    text = (f"📋 <b>{test['title']}</b>\nID: {test_id} | {test['language'].upper()}\n"
            f"Тип: {test['test_type']} | Статус: {test['status']}\n"
            f"Вопросов: {q_count} | Время: {test['time_per_question']}с\n"
            f"Платный: {'Да' if test['is_paid'] else 'Нет'}")
    await cq.message.edit_text(text, reply_markup=test_manage_kb(test_id), parse_mode="HTML")
    await cq.answer()

@router.callback_query(F.data.startswith("test_toggle_status_"))
async def cb_toggle_status(cq: CallbackQuery):
    test_id = int(cq.data.split("_")[-1])
    test = get_test(test_id)
    if not test:
        await cq.answer("Тест не найден")
        return
    new_status = "hidden" if test["status"]=="active" else "active"
    update_test(test_id, status=new_status)
    await cq.answer(f"Статус: {new_status}")
    await cb_admin_test(cq)

@router.callback_query(F.data.startswith("test_delete_"))
async def cb_test_delete(cq: CallbackQuery):
    delete_test(int(cq.data.split("_")[-1]))
    await cq.message.edit_text("🗑 Тест удалён.", reply_markup=back_kb("admin_panel"))
    await cq.answer()

@router.callback_query(F.data.startswith("test_questions_"))
async def cb_test_questions(cq: CallbackQuery):
    test_id = int(cq.data.split("_")[-1])
    questions = get_questions(test_id)
    if not questions:
        await cq.message.edit_text("❌ Вопросов нет.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="➕ Добавить", callback_data=f"add_question_{test_id}")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data=f"admin_test_{test_id}")]
            ]))
        return
    btns = [[InlineKeyboardButton(text=f"#{i+1} {q['text'][:40]}", callback_data=f"edit_question_{q['id']}")] for i,q in enumerate(questions[:20])]
    btns.append([InlineKeyboardButton(text="➕ Добавить", callback_data=f"add_question_{test_id}"),
                 InlineKeyboardButton(text="◀️ Назад", callback_data=f"admin_test_{test_id}")])
    await cq.message.edit_text(f"📋 Вопросы ({len(questions)}):", reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))
    await cq.answer()

@router.callback_query(F.data.startswith("edit_question_"))
async def cb_edit_question(cq: CallbackQuery):
    q_id = int(cq.data.split("_")[-1])
    q = get_question(q_id)
    if not q:
        await cq.answer("Вопрос не найден")
        return
    opts = get_options(q_id)
    opts_text = "\n".join(f"{'✅' if o['is_correct'] else '○'} {o['text']}" for o in opts)
    await cq.message.edit_text(f"❓ <b>{q['text']}</b>\n\n{opts_text}", parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"del_question_{q_id}")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data=f"test_questions_{q['test_id']}")]
        ]))
    await cq.answer()

@router.callback_query(F.data.startswith("del_question_"))
async def cb_del_question(cq: CallbackQuery):
    q_id = int(cq.data.split("_")[-1])
    q = get_question(q_id)
    if q:
        test_id = q["test_id"]
        delete_question(q_id)
        await cq.answer("Удалён")
        cq.data = f"test_questions_{test_id}"
        await cb_test_questions(cq)
    else:
        await cq.answer("Не найден")

@router.callback_query(F.data == "admin_give_access")
async def cb_give_access_start(cq: CallbackQuery, state: FSMContext):
    await cq.message.edit_text("💳 Введите Telegram ID:")
    await state.set_state(GiveAccess.user_id)
    await cq.answer()

@router.message(GiveAccess.user_id)
async def ga_user_id(message: Message, state: FSMContext):
    try:
        uid = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Введите числовой ID:")
        return
    await state.update_data(ga_user_id=uid)
    await message.answer("Что выдать?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 Доступ к тесту", callback_data="ga_type_test")],
            [InlineKeyboardButton(text="📖 Доступ к конспекту", callback_data="ga_type_note")],
        ]))
    await state.set_state(GiveAccess.access_type)

@router.callback_query(GiveAccess.access_type)
async def ga_type(cq: CallbackQuery, state: FSMContext):
    atype = cq.data.replace("ga_type_","")
    await state.update_data(ga_type=atype)
    await cq.message.edit_text(f"🔢 Введите ID {'теста' if atype=='test' else 'конспекта'}:")
    await state.set_state(GiveAccess.item_id)
    await cq.answer()

@router.message(GiveAccess.item_id)
async def ga_item_id(message: Message, state: FSMContext):
    try:
        item_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Введите число:")
        return
    data = await state.get_data()
    uid, atype = data["ga_user_id"], data["ga_type"]
    try:
        if atype=="test": grant_test_access(uid, item_id)
        else: grant_note_access(uid, item_id)
        await message.answer(f"✅ Доступ выдан! {uid} → {atype} #{item_id}")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")
    await state.clear()

@router.callback_query(F.data == "admin_premium")
async def cb_admin_premium(cq: CallbackQuery, state: FSMContext):
    await cq.message.edit_text("👑 Premium\n\nВведите Telegram ID:")
    await state.set_state(AdminPremium.user_id)
    await cq.answer()

@router.message(AdminPremium.user_id)
async def ap_user_id(message: Message, state: FSMContext):
    try:
        uid = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Введите число:")
        return
    await state.update_data(premium_uid=uid)
    is_prem = has_premium(uid)
    await message.answer(f"Пользователь {uid}\nPremium: {'✅' if is_prem else '❌'}\n\nДействие:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Бессрочно", callback_data="prem_grant_0")],
            [InlineKeyboardButton(text="📅 30 дней", callback_data="prem_grant_30")],
            [InlineKeyboardButton(text="📅 90 дней", callback_data="prem_grant_90")],
            [InlineKeyboardButton(text="❌ Отозвать", callback_data="prem_revoke")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_panel")]
        ]))
    await state.set_state(AdminPremium.action)

@router.callback_query(AdminPremium.action, F.data.startswith("prem_"))
async def ap_action(cq: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    uid = data["premium_uid"]
    if cq.data == "prem_revoke":
        revoke_premium(uid)
        await cq.message.edit_text(f"❌ Premium отозван у {uid}.")
    elif cq.data.startswith("prem_grant_"):
        days = int(cq.data.split("_")[-1])
        expires = (datetime.now()+timedelta(days=days)).isoformat() if days>0 else None
        grant_premium(uid, granted_by=cq.from_user.id, expires_at=expires)
        await cq.message.edit_text(f"✅ Premium выдан {uid} ({'на '+str(days)+' дней' if days>0 else 'бессрочно'}).")
    await state.clear()
    await cq.answer()

@router.callback_query(F.data == "admin_block")
async def cb_admin_block(cq: CallbackQuery, state: FSMContext):
    await cq.message.edit_text("🚫 Введите Telegram ID:")
    await state.set_state(AdminBlock.user_id)
    await cq.answer()

@router.message(AdminBlock.user_id)
async def ab_user_id(message: Message, state: FSMContext):
    try:
        uid = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Введите число:")
        return
    await state.update_data(block_uid=uid)
    await message.answer(f"Пользователь {uid}:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚫 Заблокировать", callback_data="block_do")],
            [InlineKeyboardButton(text="✅ Разблокировать", callback_data="unblock_do")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_panel")]
        ]))
    await state.set_state(AdminBlock.action)

@router.callback_query(AdminBlock.action, F.data.in_(["block_do","unblock_do"]))
async def ab_action(cq: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    uid = data["block_uid"]
    if cq.data == "block_do": block_user(uid); await cq.message.edit_text(f"🚫 {uid} заблокирован.")
    else: unblock_user(uid); await cq.message.edit_text(f"✅ {uid} разблокирован.")
    await state.clear()
    await cq.answer()

@router.callback_query(F.data == "admin_channels")
async def cb_admin_channels(cq: CallbackQuery):
    channels = list_channels()
    text = "📢 Каналы:\n\n" + "\n".join(f"• @{ch['channel_username']}" for ch in channels) if channels else "📢 Каналов нет."
    await cq.message.edit_text(text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить", callback_data="add_channel")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_panel")]
        ]))
    await cq.answer()

@router.callback_query(F.data == "add_channel")
async def cb_add_channel_start(cq: CallbackQuery, state: FSMContext):
    await cq.message.edit_text("📢 Введите @username канала:")
    await state.set_state(AdminChannel.username)
    await cq.answer()

@router.message(AdminChannel.username)
async def ach_username(message: Message, state: FSMContext):
    await state.update_data(ch_username=message.text.strip().lstrip("@"))
    await message.answer("🌐 Сделать глобальным?", reply_markup=yes_no_kb("ch_global"))
    await state.set_state(AdminChannel.is_global)

@router.callback_query(AdminChannel.is_global)
async def ach_is_global(cq: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    add_channel(channel_username=data["ch_username"], title=data["ch_username"],
                is_global=cq.data=="yes_ch_global", test_id=None)
    await cq.message.edit_text(f"✅ @{data['ch_username']} добавлен.", reply_markup=back_kb("admin_channels"))
    await state.clear()
    await cq.answer()

@router.callback_query(F.data == "admin_stats")
async def cb_admin_stats(cq: CallbackQuery):
    import sqlite3
    from config import DB_PATH
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    users = cur.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    tests = cur.execute("SELECT COUNT(*) FROM tests").fetchone()[0]
    attempts = cur.execute("SELECT COUNT(*) FROM test_attempts WHERE status='finished'").fetchone()[0]
    premium = cur.execute("SELECT COUNT(*) FROM premium_users WHERE (expires_at IS NULL OR expires_at > datetime('now'))").fetchone()[0]
    conn.close()
    await cq.message.edit_text(f"📈 Статистика\n\n👤 Пользователей: {users}\n📋 Тестов: {tests}\n✅ Попыток: {attempts}\n👑 Premium: {premium}",
        reply_markup=back_kb("admin_panel"))
    await cq.answer()

@router.callback_query(F.data == "admin_export")
async def cb_admin_export_start(cq: CallbackQuery):
    tests = list_tests(limit=20)
    if not tests:
        await cq.message.edit_text("❌ Нет тестов.")
        return
    btns = [[InlineKeyboardButton(text=f"📋 {t['title'][:35]}", callback_data=f"export_test_{t['id']}")] for t in tests]
    btns.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_panel")])
    await cq.message.edit_text("📤 Выберите тест:", reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))
    await cq.answer()

@router.callback_query(F.data.startswith("export_test_"))
async def cb_export_test(cq: CallbackQuery):
    test_id = int(cq.data.split("_")[-1])
    import sqlite3
    from config import DB_PATH
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT u.telegram_id,u.full_name,u.username,a.correct_answers,a.wrong_answers,a.skipped_answers,a.start_time,a.end_time FROM test_attempts a JOIN users u ON a.user_id=u.telegram_id WHERE a.test_id=? AND a.status='finished' ORDER BY a.correct_answers DESC",(test_id,)).fetchall()
    conn.close()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID","Имя","Username","Правильных","Неправильных","Пропущено","Начало","Конец"])
    for r in rows:
        writer.writerow([r["telegram_id"],r["full_name"],r["username"] or "",r["correct_answers"],r["wrong_answers"],r["skipped_answers"],r["start_time"],r["end_time"]])
    file = BufferedInputFile(output.getvalue().encode("utf-8-sig"), filename=f"results_{test_id}.csv")
    await cq.message.answer_document(file, caption=f"📤 Тест #{test_id}")
    await cq.answer()

@router.callback_query(F.data == "admin_notes")
async def cb_admin_notes(cq: CallbackQuery):
    notes = list_notes(limit=20)
    if not notes:
        await cq.message.edit_text("📚 Конспектов нет.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="➕ Создать", callback_data="admin_create_note")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_panel")]
            ]))
    else:
        btns = [[InlineKeyboardButton(text=f"📖 {n['title'][:35]}", callback_data=f"admin_note_{n['id']}")] for n in notes]
        btns.append([InlineKeyboardButton(text="➕ Создать", callback_data="admin_create_note"),
                     InlineKeyboardButton(text="◀️ Назад", callback_data="admin_panel")])
        await cq.message.edit_text("📚 Конспекты:", reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))
    await cq.answer()

@router.callback_query(F.data == "admin_create_note")
async def cb_create_note_start(cq: CallbackQuery, state: FSMContext):
    await cq.message.edit_text("📖 Название конспекта:")
    await state.set_state(CreateNote.title)
    await cq.answer()

@router.message(CreateNote.title)
async def cn_title(message: Message, state: FSMContext):
    await state.update_data(note_title=message.text.strip())
    await message.answer("📄 Описание:")
    await state.set_state(CreateNote.description)

@router.message(CreateNote.description)
async def cn_description(message: Message, state: FSMContext):
    await state.update_data(note_desc=message.text.strip())
    await message.answer("📚 Предмет:")
    await state.set_state(CreateNote.subject)

@router.message(CreateNote.subject)
async def cn_subject(message: Message, state: FSMContext):
    await state.update_data(note_subject=message.text.strip())
    await message.answer("📂 Категория:")
    await state.set_state(CreateNote.category)

@router.message(CreateNote.category)
async def cn_category(message: Message, state: FSMContext):
    await state.update_data(note_cat=message.text.strip())
    await message.answer("🏷 Тема:")
    await state.set_state(CreateNote.topic)

@router.message(CreateNote.topic)
async def cn_topic(message: Message, state: FSMContext):
    await state.update_data(note_topic=message.text.strip())
    await message.answer("🌐 Язык:", reply_markup=lang_choice_kb())
    await state.set_state(CreateNote.language)

@router.callback_query(CreateNote.language, F.data.in_(["lang_ru","lang_kz"]))
async def cn_language(cq: CallbackQuery, state: FSMContext):
    await state.update_data(note_lang="ru" if cq.data=="lang_ru" else "kz")
    await cq.message.edit_text("💰 Тип доступа:", reply_markup=note_paid_type_kb())
    await state.set_state(CreateNote.paid_type)
    await cq.answer()

@router.callback_query(CreateNote.paid_type)
async def cn_paid_type(cq: CallbackQuery, state: FSMContext):
    is_paid = cq.data=="note_paid"
    is_premium = cq.data=="note_premium"
    await state.update_data(note_is_paid=is_paid, note_is_premium=is_premium)
    if is_paid:
        await cq.message.edit_text("💵 Цена (тенге):")
        await state.set_state(CreateNote.price)
    else:
        await state.update_data(note_price=0)
        await cq.message.edit_text("⚖️ Сложность:", reply_markup=difficulty_kb())
        await state.set_state(CreateNote.difficulty)
    await cq.answer()

@router.message(CreateNote.price)
async def cn_price(message: Message, state: FSMContext):
    try:
        p = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Введите число:")
        return
    await state.update_data(note_price=p)
    await message.answer("⚖️ Сложность:", reply_markup=difficulty_kb())
    await state.set_state(CreateNote.difficulty)

@router.callback_query(CreateNote.difficulty, F.data.startswith("diff_"))
async def cn_difficulty(cq: CallbackQuery, state: FSMContext):
    await state.update_data(note_diff=int(cq.data.split("_")[1]))
    await cq.message.edit_text("📝 Введите содержимое первой страницы:")
    await state.set_state(CreateNote.content)
    await cq.answer()

@router.message(CreateNote.content)
async def cn_content(message: Message, state: FSMContext):
    data = await state.get_data()
    try:
        note_id = create_note(
            title=data["note_title"], description=data.get("note_desc",""),
            subject=data.get("note_subject",""), category=data.get("note_cat",""),
            language=data.get("note_lang","ru"), topic=data.get("note_topic",""),
            difficulty=data.get("note_diff",1), is_paid=data.get("note_is_paid",False),
            price=data.get("note_price",0), is_premium=data.get("note_is_premium",False),
            created_by_admin=message.from_user.id)
        add_note_page(note_id, 1, message.text)
        await message.answer(f"✅ Конспект создан! ID: {note_id}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="➕ Страница", callback_data=f"add_note_page_{note_id}")],
                [InlineKeyboardButton(text="📝 ДЗ", callback_data=f"add_hw_{note_id}")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_notes")]
            ]))
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")
    await state.clear()

@router.callback_query(F.data.startswith("add_note_page_"))
async def cb_add_note_page(cq: CallbackQuery, state: FSMContext):
    await state.update_data(add_page_note_id=int(cq.data.split("_")[-1]))
    await cq.message.edit_text("📝 Содержимое страницы:")
    await state.set_state(CreateNote.add_page)
    await cq.answer()

@router.message(CreateNote.add_page)
async def cn_add_page(message: Message, state: FSMContext):
    data = await state.get_data()
    note_id = data["add_page_note_id"]
    import sqlite3
    from config import DB_PATH
    conn = sqlite3.connect(DB_PATH)
    page_count = conn.execute("SELECT COUNT(*) FROM note_pages WHERE note_id=?",(note_id,)).fetchone()[0]
    conn.close()
    add_note_page(note_id, page_count+1, message.text)
    await message.answer(f"✅ Страница {page_count+1} добавлена!",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Ещё", callback_data=f"add_note_page_{note_id}")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_notes")]
        ]))
    await state.clear()

@router.callback_query(F.data.startswith("add_hw_"))
async def cb_add_hw(cq: CallbackQuery, state: FSMContext):
    await state.update_data(hw_note_id=int(cq.data.split("_")[-1]))
    await cq.message.edit_text("📝 Тип ДЗ:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 Тест", callback_data="hw_type_test")],
            [InlineKeyboardButton(text="✍️ Открытый ответ", callback_data="hw_type_open")],
        ]))
    await state.set_state(AddHomework.hw_type)
    await cq.answer()

@router.callback_query(AddHomework.hw_type)
async def ah_type(cq: CallbackQuery, state: FSMContext):
    htype = cq.data.replace("hw_type_","")
    await state.update_data(hw_type=htype)
    if htype=="test":
        await cq.message.edit_text("🔢 ID теста:")
        await state.set_state(AddHomework.test_id)
    else:
        await cq.message.edit_text("✍️ Текст задания:")
        await state.set_state(AddHomework.open_prompt)
    await cq.answer()

@router.message(AddHomework.test_id)
async def ah_test_id(message: Message, state: FSMContext):
    try:
        test_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Введите число:")
        return
    data = await state.get_data()
    add_note_homework(note_id=data["hw_note_id"], homework_type="test", test_id=test_id, open_task_prompt=None, auto_check_enabled=False)
    await message.answer("✅ ДЗ прикреплено!")
    await state.clear()

@router.message(AddHomework.open_prompt)
async def ah_open_prompt(message: Message, state: FSMContext):
    data = await state.get_data()
    add_note_homework(note_id=data["hw_note_id"], homework_type="open", test_id=None, open_task_prompt=message.text.strip(), auto_check_enabled=True)
    await message.answer("✅ ДЗ прикреплено!")
    await state.clear()

@router.callback_query(F.data == "admin_daily_settings")
async def cb_daily_settings(cq: CallbackQuery):
    enabled = get_setting("daily_enabled") or "1"
    count = get_setting("daily_question_count") or "10"
    mode = get_setting("daily_mode") or "random"
    await cq.message.edit_text(
        f"📅 Daily ENT\n\nСтатус: {'✅' if enabled=='1' else '❌'}\nВопросов: {count}\nРежим: {mode}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Вкл/Выкл", callback_data="daily_toggle")],
            [InlineKeyboardButton(text="🔢 Кол-во вопросов", callback_data="daily_set_count")],
            [InlineKeyboardButton(text="🎲 Режим", callback_data="daily_set_mode")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_panel")]
        ]))
    await cq.answer()

@router.callback_query(F.data == "daily_toggle")
async def cb_daily_toggle(cq: CallbackQuery):
    current = get_setting("daily_enabled") or "1"
    new_val = "0" if current=="1" else "1"
    set_setting("daily_enabled", new_val)
    await cq.answer(f"Daily ENT {'включён' if new_val=='1' else 'выключен'}")
    await cb_daily_settings(cq)

@router.callback_query(F.data == "daily_set_count")
async def cb_daily_set_count(cq: CallbackQuery, state: FSMContext):
    await cq.message.edit_text("🔢 Введите 5, 10 или 15:")
    await state.set_state(DailySettings.question_count)
    await cq.answer()

@router.message(DailySettings.question_count)
async def ds_question_count(message: Message, state: FSMContext):
    try:
        n = int(message.text.strip())
        if n not in (5,10,15): raise ValueError
    except ValueError:
        await message.answer("❌ Введите 5, 10 или 15:")
        return
    set_setting("daily_question_count", str(n))
    await message.answer(f"✅ Вопросов: {n}")
    await state.clear()

@router.callback_query(F.data == "admin_tournaments")
async def cb_admin_tournaments(cq: CallbackQuery):
    tours = list_tournaments()
    if not tours:
        await cq.message.edit_text("🏆 Турниров нет.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="➕ Создать", callback_data="create_tournament")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_panel")]
            ]))
    else:
        btns = [[InlineKeyboardButton(text=f"🏆 {t['title'][:35]}", callback_data=f"admin_tour_{t['id']}")] for t in tours]
        btns.append([InlineKeyboardButton(text="➕ Создать", callback_data="create_tournament"),
                     InlineKeyboardButton(text="◀️ Назад", callback_data="admin_panel")])
        await cq.message.edit_text("🏆 Турниры:", reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))
    await cq.answer()

@router.callback_query(F.data == "create_tournament")
async def cb_create_tournament(cq: CallbackQuery, state: FSMContext):
    await cq.message.edit_text("🏆 Название турнира:")
    await state.set_state(CreateTournament.title)
    await cq.answer()

@router.message(CreateTournament.title)
async def tour_title(message: Message, state: FSMContext):
    await state.update_data(tour_title=message.text.strip())
    await message.answer("🔢 ID теста:")
    await state.set_state(CreateTournament.test_id)

@router.message(CreateTournament.test_id)
async def tour_test_id(message: Message, state: FSMContext):
    try:
        tid = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Введите число:")
        return
    await state.update_data(tour_test_id=tid)
    await message.answer("📅 Дата начала (YYYY-MM-DD):")
    await state.set_state(CreateTournament.start_date)

@router.message(CreateTournament.start_date)
async def tour_start(message: Message, state: FSMContext):
    try:
        datetime.strptime(message.text.strip(),"%Y-%m-%d")
    except ValueError:
        await message.answer("❌ Формат: YYYY-MM-DD")
        return
    await state.update_data(tour_start=message.text.strip())
    await message.answer("📅 Дата окончания (YYYY-MM-DD):")
    await state.set_state(CreateTournament.end_date)

@router.message(CreateTournament.end_date)
async def tour_end(message: Message, state: FSMContext):
    try:
        datetime.strptime(message.text.strip(),"%Y-%m-%d")
    except ValueError:
        await message.answer("❌ Формат: YYYY-MM-DD")
        return
    await state.update_data(tour_end=message.text.strip())
    await message.answer("🏅 Приз (или '-'):")
    await state.set_state(CreateTournament.prize)

@router.message(CreateTournament.prize)
async def tour_prize(message: Message, state: FSMContext):
    data = await state.get_data()
    prize = message.text.strip()
    if prize=="-": prize=""
    try:
        tid = create_tournament(title=data["tour_title"], test_id=data["tour_test_id"],
            start_date=data["tour_start"], end_date=data["tour_end"],
            prize=prize, created_by=message.from_user.id)
        await message.answer(f"✅ Турнир создан! ID: {tid}", reply_markup=back_kb("admin_tournaments"))
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")
    await state.clear()
