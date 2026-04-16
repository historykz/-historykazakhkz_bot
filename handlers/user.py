@router.callback_query(F.data.startswith("tp_"))
async def cb_pause_test(call: CallbackQuery, bot: Bot):
    attempt_id = int(call.data.replace("tp_", ""))
    attempt = db.get_attempt(attempt_id)
    if not attempt or attempt["user_id"] != call.from_user.id:
        await call.answer("❌", show_alert=True)
        return
    user = db.get_user(call.from_user.id)
    lang = user.get("language", "ru") if user else "ru"
    db.update_attempt(attempt_id, {"paused": 1})
    await call.answer()
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="▶️ Продолжить" if lang == "ru" else "▶️ Жалғастыру",
            callback_data=f"tc_{attempt_id}"
        ),
        InlineKeyboardButton(
            text="⏹ Завершить" if lang == "ru" else "⏹ Аяқтау",
            callback_data=f"tf_{attempt_id}"
        ),
    ]])
    await call.message.edit_text(
        "⏸ <b>Тест на паузе</b>\n\nНажмите «Продолжить» когда будете готовы."
        if lang == "ru" else
        "⏸ <b>Тест тоқтатылды</b>\n\n«Жалғастыру» батырмасын басыңыз.",
        reply_markup=kb,
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("tc_"))
async def cb_continue_test(call: CallbackQuery, bot: Bot):
    attempt_id = int(call.data.replace("tc_", ""))
    attempt = db.get_attempt(attempt_id)
    if not attempt or attempt["user_id"] != call.from_user.id:
        await call.answer("❌", show_alert=True)
        return
    user = db.get_user(call.from_user.id)
    lang = user.get("language", "ru") if user else "ru"
    await call.answer()
    await call.message.edit_text("▶️ Продолжаем!" if lang == "ru" else "▶️ Жалғасамыз!")
    from services.test_runner import resume_attempt
    test = db.get_test(attempt["test_id"])
    await resume_attempt(bot, attempt_id, call.message.chat.id, test or {})


@router.callback_query(F.data.startswith("tf_"))
async def cb_finish_test(call: CallbackQuery, bot: Bot):
    attempt_id = int(call.data.replace("tf_", ""))
    attempt = db.get_attempt(attempt_id)
    if not attempt or attempt["user_id"] != call.from_user.id:
        await call.answer("❌", show_alert=True)
        return
    user = db.get_user(call.from_user.id)
    lang = user.get("language", "ru") if user else "ru"
    await call.answer()
    await call.message.edit_text("⏹ Завершаем тест..." if lang == "ru" else "⏹ Аяқталуда...")
    from services.test_runner import finish_attempt
    test = db.get_test(attempt["test_id"])
    await finish_attempt(bot, attempt_id, call.message.chat.id, test or {}, lang)
