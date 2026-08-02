"""Manual-only location provider for version 1."""

from __future__ import annotations

from typing import Any


def get_location(config: dict[str, Any] | None = None) -> dict[str, object]:
    config = config or {}
    if config.get("mode", "manual") != "manual":
        return {"available": False, "city": None, "country": None, "source": "manual"}
    city = str(config.get("city", "")).strip()
    country = str(config.get("country", "")).strip()
    return {
        "available": bool(city or country),
        "city": city or None,
        "country": country or None,
        "source": "manual",
    }

