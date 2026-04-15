import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database import get_user, list_notes, get_note, get_note_pages, get_note_homework, has_premium, update_note_progress
from services.notes_service import check_note_access
from locales import get_text
from keyboards import back_kb

logger = logging.getLogger(__name__)
router = Router()


@router.message(F.text.in_(["📖 Конспекты", "📖 Конспекттер"]))
@router.callback_query(F.data == "section_notes")
async def show_notes_catalog(update):
    if isinstance(update, CallbackQuery):
        user_id = update.from_user.id
        send = update.message.edit_text
        await update.answer()
    else:
        user_id = update.from_user.id
        send = update.answer
    db_user = get_user(user_id)
    lang = db_user.get("language", "ru") if db_user else "ru"
    notes = list_notes(language=lang)
    if not notes:
        await send("📚 Конспектов пока нет." if lang=="ru" else "📚 Конспект әзірше жоқ.")
        return
    btns = []
    for note in notes:
        icon = "🆓" if not note["is_paid"] and not note["is_premium"] else ("👑" if note["is_premium"] else "🔒")
        btns.append([InlineKeyboardButton(text=f"{icon} {note['title'][:40]}", callback_data=f"note_card_{note['id']}")])
    await send("📚 Конспекты:\n\nВыберите:" if lang=="ru" else "📚 Конспекттер:", reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))


@router.callback_query(F.data.startswith("note_card_"))
async def show_note_card(cq: CallbackQuery):
    note_id = int(cq.data.split("_")[-1])
    note = get_note(note_id)
    if not note:
        await cq.answer("Конспект не найден")
        return
    db_user = get_user(cq.from_user.id)
    lang = db_user.get("language", "ru") if db_user else "ru"
    if note["language"] != lang:
        await cq.message.edit_text("❌ Этот конспект на другом языке. Смените язык в профиле.", reply_markup=back_kb("section_notes"))
        await cq.answer()
        return
    access = check_note_access(cq.from_user.id, note_id)
    hw = get_note_homework(note_id)
    pages = get_note_pages(note_id)
    page_count = len(pages)
    icon = "🆓" if not note["is_paid"] and not note["is_premium"] else ("👑" if note["is_premium"] else "🔒")
    text = (f"📖 <b>{note['title']}</b>\n\n{note.get('description','')}\n\n"
            f"📚 Предмет: {note.get('subject','—')}\n"
            f"🏷 Тема: {note.get('topic','—')}\n"
            f"📄 Страниц: {page_count}\n"
            f"📝 ДЗ: {'Есть' if hw else 'Нет'}\n"
            f"{icon} Доступ: " + ("Бесплатный" if not note["is_paid"] and not note["is_premium"] else ("Premium" if note["is_premium"] else f"Платный ({note['price']} тг)")))
    btns = []
    if access == "ok":
        btns.append([InlineKeyboardButton(text="📖 Читать" if lang=="ru" else "📖 Оқу", callback_data=f"read_note_{note_id}_1")])
        if hw:
            btns.append([InlineKeyboardButton(text="📝 Начать ДЗ" if lang=="ru" else "📝 ҮТ бастау", callback_data=f"start_hw_{note_id}")])
    elif access == "paid":
        btns += [
            [InlineKeyboardButton(text="💬 Написать менеджеру" if lang=="ru" else "💬 Менеджерге жазу", url="https://t.me/historyentk_bot")],
            [InlineKeyboardButton(text="🔄 Проверить доступ" if lang=="ru" else "🔄 Тексеру", callback_data=f"check_note_access_{note_id}")]
        ]
    elif access == "premium":
        btns += [
            [InlineKeyboardButton(text="💎 Купить Premium", callback_data="premium_info")],
            [InlineKeyboardButton(text="💬 Написать менеджеру" if lang=="ru" else "💬 Менеджерге жазу", url="https://t.me/historyentk_bot")]
        ]
    btns.append([InlineKeyboardButton(text="◀️ Назад" if lang=="ru" else "◀️ Артқа", callback_data="section_notes")])
    await cq.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=btns), parse_mode="HTML")
    await cq.answer()


@router.callback_query(F.data.startswith("read_note_"))
async def read_note_page(cq: CallbackQuery):
    parts = cq.data.split("_")
    note_id = int(parts[2])
    page_num = int(parts[3])
    note = get_note(note_id)
    if not note:
        await cq.answer("Конспект не найден")
        return
    db_user = get_user(cq.from_user.id)
    lang = db_user.get("language", "ru") if db_user else "ru"
    access = check_note_access(cq.from_user.id, note_id)
    if access != "ok":
        await cq.answer("Доступ закрыт" if lang=="ru" else "Қолжетімділік жабық", show_alert=True)
        return
    pages = get_note_pages(note_id)
    if not pages:
        await cq.answer("Страниц нет")
        return
    page = next((p for p in pages if p["page_number"] == page_num), None)
    if not page:
        await cq.answer("Страница не найдена")
        return
    total = len(pages)
    nav = []
    if page_num > 1:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"read_note_{note_id}_{page_num-1}"))
    nav.append(InlineKeyboardButton(text=f"{page_num}/{total}", callback_data="noop"))
    if page_num < total:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"read_note_{note_id}_{page_num+1}"))
    btns = [nav]
    if page_num == total:
        hw = get_note_homework(note_id)
        if hw:
            btns.append([InlineKeyboardButton(text="📝 Начать ДЗ" if lang=="ru" else "📝 ҮТ бастау", callback_data=f"start_hw_{note_id}")])
    btns.append([InlineKeyboardButton(text="◀️ К карточке" if lang=="ru" else "◀️ Картаға", callback_data=f"note_card_{note_id}")])
    update_note_progress(cq.from_user.id, note_id, page_num, completed=(page_num==total))
    await cq.message.answer(
        f"📖 <b>{note['title']}</b> — стр. {page_num}/{total}\n\n{page['content']}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=btns),
        parse_mode="HTML", protect_content=True)
    await cq.answer()


@router.callback_query(F.data.startswith("check_note_access_"))
async def cb_check_note_access(cq: CallbackQuery):
    note_id = int(cq.data.split("_")[-1])
    db_user = get_user(cq.from_user.id)
    lang = db_user.get("language", "ru") if db_user else "ru"
    access = check_note_access(cq.from_user.id, note_id)
    if access == "ok":
        await cq.answer("✅ Доступ открыт!" if lang=="ru" else "✅ Ашылды!", show_alert=True)
        cq.data = f"note_card_{note_id}"
        await show_note_card(cq)
    else:
        await cq.answer("❌ Доступа нет. Обратитесь к менеджеру." if lang=="ru" else "❌ Жоқ. Менеджерге хабарласыңыз.", show_alert=True)
