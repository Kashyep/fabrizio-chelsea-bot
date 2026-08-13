from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable


class ChelseaMatcher:
    """Case-insensitive literal matching with word-boundary protection."""

    def __init__(self, terms: Iterable[str]) -> None:
        normalized = {self._normalize(term) for term in terms if term.strip()}
        if not normalized:
            raise ValueError("At least one Chelsea term is required")
        alternatives = "|".join(
            re.escape(term) for term in sorted(normalized, key=len, reverse=True)
        )
        self.pattern = re.compile(rf"(?<!\w)(?:{alternatives})(?!\w)")

    @staticmethod
    def _normalize(value: str) -> str:
        return unicodedata.normalize("NFKC", value).casefold()

    def matches(self, text: str) -> bool:
        return self.pattern.search(self._normalize(text)) is not None
