"""Manual-only location provider for version 1."""

from __future__ import annotations

from typing import Any


def get_location(
    config: dict[str, Any] | None = None,
    language: str = "zh_CN",
) -> dict[str, object]:
    config = config or {}
    if config.get("mode", "manual") != "manual":
        return {
            "available": False,
            "city": None,
            "country": None,
            "query_city": None,
            "query_country": None,
            "source": "manual",
        }

    query = config.get("query") if isinstance(config.get("query"), dict) else {}
    query_city = str(query.get("city") or config.get("city") or "").strip()
    query_country = str(query.get("country") or config.get("country") or "").strip()

    display_all = config.get("display") if isinstance(config.get("display"), dict) else {}
    display = display_all.get(language) if isinstance(display_all.get(language), dict) else {}
    city = str(display.get("city") or query_city).strip()
    country = str(display.get("country") or query_country).strip()
    return {
        "available": bool(query_city or query_country or city or country),
        "city": city or None,
        "country": country or None,
        "query_city": query_city or None,
        "query_country": query_country or None,
        "source": "manual",
    }
