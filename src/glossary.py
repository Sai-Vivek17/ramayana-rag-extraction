from __future__ import annotations

import re
from typing import Any

from src.config import get_settings
from src.utils import read_json


def load_glossary() -> list[dict[str, Any]]:
    settings = get_settings()
    return read_json(settings.glossary_terms, default=[]) or []


def load_transliteration_rules() -> dict[str, Any]:
    settings = get_settings()
    return read_json(settings.transliteration_rules, default={}) or {}


def glossary_prompt_block(max_terms: int | None = None) -> str:
    terms = load_glossary()
    if max_terms:
        terms = terms[:max_terms]
    lines = [
        "Use this glossary consistently. Preserve these canonical English spellings and notes:",
    ]
    for term in terms:
        telugu = ", ".join(term.get("telugu", []))
        canonical = term.get("canonical", "")
        note = term.get("note", "")
        lines.append(f"- {telugu} => {canonical}. {note}".strip())
    rules = load_transliteration_rules()
    if rules.get("principles"):
        lines.append("Transliteration principles:")
        lines.extend(f"- {principle}" for principle in rules["principles"])
    return "\n".join(lines)


def canonical_terms() -> set[str]:
    return {str(term.get("canonical")) for term in load_glossary() if term.get("canonical")}


def find_glossary_inconsistencies(text: str) -> list[str]:
    rules = load_transliteration_rules()
    normalizations = rules.get("normalizations", {})
    text_lower = (text or "").lower()
    issues: list[str] = []
    for canonical, variants in normalizations.items():
        for variant in variants:
            variant_pattern = rf"\b{re.escape(variant.lower())}\b"
            canonical_pattern = rf"\b{re.escape(canonical.lower())}\b"
            if re.search(variant_pattern, text_lower) and not re.search(canonical_pattern, text_lower):
                issues.append(f"Variant '{variant}' appears; prefer '{canonical}'.")
    return issues
