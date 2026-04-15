import logging
from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

import database as db
from keyboards import lang_select_kb, main_menu_kb, back_kb
from locales import get_text as t
from states import LangSelect
from config import MANAGER_USERNAME

logger = logging.getLogger(__name__)
router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user = db.get_user(message.from_user.id)
    lang = user.get("language", "ru") if user else "ru"

    args = message.text.split(maxsplit=1)
    param = args[1].strip() if len(args) > 1 else ""

    if param.startswith("ref_"):
        referrer_str = param[4:]
        if referrer_str.isdigit():
            db.record_referral(int(referrer_str), message.from_user.id)

    if param.startswith("test_"):
        test_id_str = param[5:]
        if test_id_str.isdigit():
            if not user or not user.get("language"):
                await message.answer(t("choose_language", "ru"), reply_markup=lang_select_kb())
                await state.set_state(LangSelect.choosing)
                await state.update_data(pending_test_id=int(test_id_str))
                return
            from handlers.user import show_test_card
            await show_test_card(message, int(test_id_str), lang)
            return

    if not user or not user.get("language"):
        await message.answer(t("choose_language", "ru"), reply_markup=lang_select_kb())
        await state.set_state(LangSelect.choosing)
        return

    await message.answer(t("main_menu", lang), reply_markup=main_menu_kb(lang))


@router.callback_query(LangSelect.choosing, F.data.startswith("lang:"))
async def cb_lang_select(call: CallbackQuery, state: FSMContext):
    lang = call.data.split(":")[1]
    db.set_user_language(call.from_user.id, lang)
    await call.answer()
    await call.message.edit_text(t("language_set", lang))
    data = await state.get_data()
    pending_test = data.get("pending_test_id")
    await state.clear()
    if pending_test:
        from handlers.user import show_test_card
        await show_test_card(call.message, pending_test, lang)
    else:
        await call.message.answer(t("main_menu", lang), reply_markup=main_menu_kb(lang))


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    user = db.get_user(message.from_user.id)
    lang = user.get("language", "ru") if user else "ru"
    await state.clear()
    await message.answer(t("cancelled", lang), reply_markup=main_menu_kb(lang))


@router.message(Command("help"))
@router.message(F.text.in_(["ℹ️ Помощь", "ℹ️ Көмек"]))
async def cmd_help(message: Message):
    user = db.get_user(message.from_user.id)
    lang = user.get("language", "ru") if user else "ru"
    await message.answer(t("help_text", lang, manager=MANAGER_USERNAME), parse_mode="HTML")


@router.message(F.text.in_(["🛠 Техподдержка", "🛠 Техқолдау"]))
async def btn_support(message: Message):
    user = db.get_user(message.from_user.id)
    lang = user.get("language", "ru") if user else "ru"
    from keyboards import support_kb
    await message.answer(
        f"📞 {t('btn_support', lang)}: {MANAGER_USERNAME}",
        reply_markup=support_kb(lang),
    )


@router.callback_query(F.data == "noop")
async def cb_noop(call: CallbackQuery):
    await call.answer()
