import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database import get_user, has_premium

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == "premium_info")
async def cb_premium_info(cq: CallbackQuery):
    db_user = get_user(cq.from_user.id)
    lang = db_user.get("language", "ru") if db_user else "ru"
    is_prem = has_premium(cq.from_user.id)
    if lang == "ru":
        if is_prem:
            text = ("👑 <b>Premium активен</b>\n\nУ вас есть доступ к:\n"
                    "• Всем платным тестам\n• Всем конспектам\n"
                    "• Всем ДЗ\n• Расширенной аналитике\n\nСпасибо! 🙏")
        else:
            text = ("👑 <b>Premium</b>\n\nС Premium вы получаете:\n"
                    "• Все платные тесты\n• Все конспекты\n"
                    "• Все ДЗ\n• Расширенную аналитику\n\n"
                    "Для получения обратитесь к менеджеру:\n📞 @historyentk_bot")
    else:
        if is_prem:
            text = ("👑 <b>Premium белсенді</b>\n\nҚолжетімді:\n"
                    "• Барлық ақылы тесттер\n• Барлық конспекттер\n"
                    "• Барлық ҮТ\n• Кеңейтілген аналитика\n\nРахмет! 🙏")
        else:
            text = ("👑 <b>Premium</b>\n\nPremium арқылы:\n"
                    "• Барлық ақылы тесттер\n• Барлық конспекттер\n"
                    "• Барлық ҮТ\n• Кеңейтілген аналитика\n\n"
                    "Алу үшін менеджерге жазыңыз:\n📞 @historyentk_bot")
    btns = []
    if not is_prem:
        btns.append([InlineKeyboardButton(
            text="💬 Написать менеджеру" if lang=="ru" else "💬 Менеджерге жазу",
            url="https://t.me/historyentk_bot"
        )])
    btns.append([InlineKeyboardButton(
        text="◀️ Назад" if lang=="ru" else "◀️ Артқа",
        callback_data="show_profile"
    )])
    await cq.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=btns), parse_mode="HTML")
    await cq.answer()
