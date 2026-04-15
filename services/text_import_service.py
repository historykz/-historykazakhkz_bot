import logging
import database as db
from utils import parse_text_questions

logger = logging.getLogger(__name__)


def import_questions_from_text(test_id: int, raw_text: str,
                                topic: str = "", difficulty: int = 1,
                                imported_by: int = 0) -> tuple:
    questions, errors = parse_text_questions(raw_text)
    ok = 0
    for q in questions:
        try:
            qid = db.add_question(
                test_id=test_id,
                text=q["text"],
                explanation="",
                topic=topic,
                difficulty=difficulty,
                points=1.0
            )
            for i, opt in enumerate(q["options"]):
                db.add_option(qid, opt["text"], is_correct=opt["is_correct"])
            ok += 1
        except Exception as e:
            logger.error("Error saving question: %s", e)
            errors.append(str(e))
    return ok, len(errors), errors
