"""Blocks diagnostic or medication wording before any text is shown."""

BLOCKED = ["you have", "you are suffering", "diagnos", "disease", "condition:", "take ", "dose", "medication", "prescri"]


def blocks_diagnostic(text: str) -> list[str]:
    lowered = text.lower()
    return [p for p in BLOCKED if p in lowered]
