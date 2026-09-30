import re


def normalize_task(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip()).lower()
