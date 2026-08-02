"""Cross-platform local time provider."""

from __future__ import annotations

from datetime import datetime


def get_time(now: datetime | None = None) -> dict[str, object]:
    current = now or datetime.now().astimezone()
    if current.tzinfo is None:
        current = current.astimezone()
    timezone_name = getattr(current.tzinfo, "key", None) or current.tzname() or "UTC"
    return {
        "available": True,
        "datetime": current.strftime("%Y-%m-%d %H:%M:%S"),
        "timezone": timezone_name,
        "weekday": current.strftime("%A"),
        "weekday_number": current.isoweekday(),
    }

