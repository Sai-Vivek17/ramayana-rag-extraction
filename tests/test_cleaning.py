from __future__ import annotations

from src.clean_telugu_text import clean_telugu_text
from src.utils import telugu_char_count


def test_cleaning_preserves_telugu_text():
    source = "\n12\n\nరాముడు అయోధ్యకు వెళ్లెను.\n\n   \n***\n"

    cleaned = clean_telugu_text(source)

    assert "రాముడు" in cleaned
    assert "12" not in cleaned
    assert telugu_char_count(cleaned) > 0


def test_cleaning_is_conservative_with_question_answer_shape():
    source = "ప్రశ్న: రాముడు ఎవరు?\nజవాబు: రాముడు దశరథుని కుమారుడు."

    cleaned = clean_telugu_text(source)

    assert "ప్రశ్న" in cleaned
    assert "జవాబు" in cleaned

