from aiogram.types import InlineQueryResultArticle, InputTextMessageContent
import database as db


def build_inline_result(test, lang: str = "ru"):
    try:
        link = f"https://t.me/historykazakhkz_bot?start=test_{test['id']}"
        text = (
            f"📚 <b>{test['title']}</b>\n"
            f"❓ Вопросов: {test.get('question_count') or '?'}\n"
            f"⏱ {test.get('time_per_question', 30)} сек/вопрос\n\n"
            f"🔗 {link}"
        )
        return InlineQueryResultArticle(
            id=f"test_{test['id']}",
            title=test["title"],
            description=f"{test.get('test_type','test')} • {test.get('question_count','?')} вопр.",
            input_message_content=InputTextMessageContent(
                message_text=text,
                parse_mode="HTML",
            ),
        )
    except Exception:
        return None
