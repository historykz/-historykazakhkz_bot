import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from database import get_user, has_premium, get_user_achievements, get_user_stats, get_user_streak, count_referrals
from locales import get_text
from keyboards import lang_choice_kb, main_menu_kb
from states import ChangeLang
from utils import compute_level

logger = logging.getLogger(__name__)
router = Router()


@router.message(F.text.in_(["👤 Профиль", "👤 Профиль"]))
@router.callback_query(F.data == "show_profile")
async def show_profile(update, state: FSMContext = None):
    if isinstance(update, CallbackQuery):
        user = update.from_user
        send = update.message.edit_text
        answer_cq = update.answer
    else:
        user = update.from_user
        send = update.answer
        answer_cq = None

    db_user = get_user(user.id)
    if not db_user:
        if answer_cq: await answer_cq()
        return
    lang = db_user.get("language", "ru")
    is_prem = has_premium(user.id)
    stats = get_user_stats(user.id)
    streak = get_user_streak(user.id)
    achievements = get_user_achievements(user.id)
    refs = count_referrals(user.id)
    level_label = compute_level(stats.get("avg_percent", 0))
    prem_text = ("👑 Premium активен" if lang=="ru" else "👑 Premium белсенді") if is_prem else ("👑 Premium не активен" if lang=="ru" else "👑 Premium белсенді емес")
    streak_emoji = "🔥" if streak["current"] > 0 else "💤"

    if lang == "ru":
        text = (f"👤 <b>Профиль</b>\n\nИмя: {db_user.get('full_name','—')}\nID: {user.id}\nЯзык: 🇷🇺 Русский\n\n{prem_text}\n\n📊 Статистика:\n• Тестов: {stats.get('total_attempts',0)}\n• Правильных: {stats.get('total_correct',0)}\n• Средний: {stats.get('avg_percent',0):.1f}%\n• Уровень: {level_label}\n\n{streak_emoji} Streak: {streak['current']} дней\n🏆 Лучший: {streak['best']} дней\n\n🎁 Друзей: {refs}\n🏅 Достижений: {len(achievements)}")
    else:
        text = (f"👤 <b>Профиль</b>\n\nАты: {db_user.get('full_name','—')}\nID: {user.id}\nТіл: 🇰🇿 Қазақша\n\n{prem_text}\n\n📊 Статистика:\n• Тест: {stats.get('total_attempts',0)}\n• Дұрыс: {stats.get('total_correct',0)}\n• Орташа: {stats.get('avg_percent',0):.1f}%\n• Деңгей: {level_label}\n\n{streak_emoji} Streak: {streak['current']} күн\n🏆 Үздік: {streak['best']} күн\n\n🎁 Достар: {refs}\n🏅 Жетістік: {len(achievements)}")

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌐 Сменить язык" if lang=="ru" else "🌐 Тілді өзгерту", callback_data="change_language")],
        [InlineKeyboardButton(text="🏅 Достижения" if lang=="ru" else "🏅 Жетістіктер", callback_data="show_achievements")],
        [InlineKeyboardButton(text="🎁 Пригласить друга" if lang=="ru" else "🎁 Дос шақыру", callback_data="referral_link")],
        [InlineKeyboardButton(text="👑 Premium", callback_data="premium_info")],
    ])
    if answer_cq:
        await send(text, reply_markup=kb, parse_mode="HTML")
        await answer_cq()
    else:
        await send(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data == "change_language")
async def cb_change_language(cq: CallbackQuery, state: FSMContext):
    db_user = get_user(cq.from_user.id)
    lang = db_user.get("language", "ru") if db_user else "ru"
    await cq.message.edit_text("Выберите язык:" if lang=="ru" else "Тілді таңдаңыз:", reply_markup=lang_choice_kb())
    await state.set_state(ChangeLang.selecting)
    await cq.answer()


@router.callback_query(ChangeLang.selecting, F.data.in_(["lang_ru", "lang_kz"]))
async def cl_select(cq: CallbackQuery, state: FSMContext):
    import sqlite3
    from config import DB_PATH
    new_lang = "ru" if cq.data == "lang_ru" else "kz"
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE users SET language=? WHERE telegram_id=?", (new_lang, cq.from_user.id))
    conn.commit()
    conn.close()
    await state.clear()
    await cq.message.edit_text("✅ Язык изменён!" if new_lang=="ru" else "✅ Тіл өзгертілді!")
    await cq.message.answer(get_text("main_menu", new_lang), reply_markup=main_menu_kb(new_lang))
    await cq.answer()


@router.callback_query(F.data == "show_achievements")
async def cb_achievements(cq: CallbackQuery):
    db_user = get_user(cq.from_user.id)
    lang = db_user.get("language", "ru") if db_user else "ru"
    achievements = get_user_achievements(cq.from_user.id)
    LABELS = {
        "first_test": "🎯 Первый тест", "test_10": "📋 10 тестов",
        "test_50": "📋 50 тестов", "streak_7": "🔥 7 дней streak",
        "streak_30": "🏆 30 дней streak", "correct_100": "✅ 100 правильных",
        "duel_win": "⚔️ Победа в дуэли", "first_note": "📖 Первый конспект",
        "premium": "👑 Premium",
    }
    if achievements:
        text = "🏅 Достижения:\n\n" + "\n".join(f"• {LABELS.get(a['achievement_key'], a['achievement_key'])}" for a in achievements)
    else:
        text = "Пока нет достижений." if lang=="ru" else "Жетістік жоқ."
    await cq.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад" if lang=="ru" else "◀️ Артқа", callback_data="show_profile")]
    ]))
    await cq.answer()


@router.callback_query(F.data == "referral_link")
async def cb_referral_link(cq: CallbackQuery):
    import sqlite3
    from config import DB_PATH
    db_user = get_user(cq.from_user.id)
    lang = db_user.get("language", "ru") if db_user else "ru"
    conn = sqlite3.connect(DB_PATH)
    bot_row = conn.execute("SELECT value FROM settings WHERE key='bot_username'").fetchone()
    conn.close()
    bot_username = bot_row[0] if bot_row else "your_bot"
    refs = count_referrals(cq.from_user.id)
    link = f"https://t.me/{bot_username}?start=ref_{cq.from_user.id}"
    text = f"🎁 Реферальная ссылка\n\n{link}\n\nДрузей: {refs}\n\n• 1 друг — бесплатный тест\n• 3 друга — Premium тест\n• 10 друзей — пробник"
    await cq.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад" if lang=="ru" else "◀️ Артқа", callback_data="show_profile")]
    ]))
    await cq.answer()
