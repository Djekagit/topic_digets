import re
from urllib.parse import urlparse


CHANNEL_RE = re.compile(r"^[a-zA-Z0-9_]{5,32}$")
MAX_INTERVAL_HOURS = 720


def normalize_channel_name(raw: str) -> str:
    value = raw.strip().rstrip("/")
    if not value:
        raise ValueError("Пустое название канала")

    if value.startswith("@"):
        value = value[1:]
    elif "://" in value or value.startswith("t.me/") or value.startswith("telegram.me/"):
        parsed = urlparse(value if "://" in value else f"https://{value}")
        if parsed.netloc not in {"t.me", "www.t.me", "telegram.me", "www.telegram.me"}:
            raise ValueError("Поддерживаются только ссылки t.me")

        parts = [part for part in parsed.path.split("/") if part]
        if parts and parts[0] == "s":
            parts = parts[1:]
        if not parts or parts[0].startswith("+"):
            raise ValueError("Поддерживаются только публичные каналы")
        value = parts[0]

    value = value.lower()
    if not CHANNEL_RE.fullmatch(value):
        raise ValueError(f"Некорректное название канала: {raw}")
    return value


def normalize_channel_list(raw: str) -> list[str]:
    candidates = re.split(r"[\s,]+", raw.strip())
    channels: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        if not candidate:
            continue
        channel = normalize_channel_name(candidate)
        if channel in seen:
            continue
        channels.append(channel)
        seen.add(channel)
    return channels


def parse_interval_hours(raw: str) -> int:
    value = raw.strip()
    if not value.isdigit():
        raise ValueError("Интервал должен быть числом часов")

    hours = int(value)
    if hours < 1 or hours > MAX_INTERVAL_HOURS:
        raise ValueError(f"Интервал должен быть от 1 до {MAX_INTERVAL_HOURS} часов")
    return hours
