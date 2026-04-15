import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from database import get_user, get_note, get_note_homework, update_note_progress
from services.notes_service import check_note_access, auto_check_hw
from services.test_runner import start_attempt
from states import HomeworkAnswer
from keyboards import back_kb

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data.startswith("start_hw_"))
async def cb_start_hw(cq: CallbackQuery, state: FSMContext):
    note_id = int(cq.data.split("_")[-1])
    db_user = get_user(cq.from_user.id)
    lang = db_user.get("language", "ru") if db_user else "ru"
    access = check_note_access(cq.from_user.id, note_id)
    if access != "ok":
        await cq.answer("❌ Нет доступа" if lang=="ru" else "❌ Жоқ", show_alert=True)
        return
    hw = get_note_homework(note_id)
    if not hw:
        await cq.answer("ДЗ не найдено" if lang=="ru" else "ҮТ табылмады", show_alert=True)
        return
    if hw["homework_type"] == "test" and hw.get("test_id"):
        await cq.message.answer("📝 Запускаем тест-ДЗ..." if lang=="ru" else "📝 Тест-ҮТ іске қосылуда...")
        await start_attempt(cq.message, cq.from_user.id, hw["test_id"], state)
    else:
        await state.update_data(hw_note_id=note_id, hw_id=hw["id"], hw_prompt=hw.get("open_task_prompt",""))
        prompt = hw.get("open_task_prompt", "Напишите ваш ответ:")
        text = f"📝 Домашнее задание\n\n{prompt}\n\nНапишите ответ:" if lang=="ru" else f"📝 Үй тапсырмасы\n\n{prompt}\n\nЖауабыңыз:"
        await cq.message.edit_text(text)
        await state.set_state(HomeworkAnswer.typing)
    await cq.answer()


@router.message(HomeworkAnswer.typing)
async def hw_receive_answer(message: Message, state: FSMContext):
    data = await state.get_data()
    note_id = data.get("hw_note_id")
    hw_id = data.get("hw_id")
    db_user = get_user(message.from_user.id)
    lang = db_user.get("language", "ru") if db_user else "ru"
    user_answer = message.text.strip()
    hw = get_note_homework(note_id)
    if hw and hw.get("auto_check_enabled") and hw.get("open_task_prompt"):
        score, comment = auto_check_hw(user_answer, hw["open_task_prompt"])
        from database import save_hw_answer
        save_hw_answer(message.from_user.id, hw_id, user_answer, score)
        update_note_progress(message.from_user.id, note_id, last_page=None, homework_completed=True)
        result_text = (f"📝 Ответ получен!\n\n{'✅ Правильно' if score>=7 else '⚠️ Частично' if score>=4 else '❌ Неверно'}\nБаллы: {score}/10\n\n💬 {comment}"
                       if lang=="ru" else
                       f"📝 Жауап қабылданды!\n\n{'✅ Дұрыс' if score>=7 else '⚠️ Жартылай' if score>=4 else '❌ Қате'}\nҰпай: {score}/10\n\n💬 {comment}")
    else:
        from database import save_hw_answer
        save_hw_answer(message.from_user.id, hw_id, user_answer, score=None)
        update_note_progress(message.from_user.id, note_id, last_page=None, homework_completed=True)
        result_text = "✅ Ответ сохранён! Преподаватель проверит позже." if lang=="ru" else "✅ Жауап сақталды!"
    await message.answer(result_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ К конспекту" if lang=="ru" else "◀️ Конспектке", callback_data=f"note_card_{note_id}")]
    ]))
    await state.clear()
