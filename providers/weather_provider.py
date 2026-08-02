"""wttr.in weather provider with a small atomic JSON cache."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Callable
from urllib.parse import quote
from urllib.request import Request, urlopen


def _unavailable() -> dict[str, object]:
    return {
        "available": False,
        "condition": None,
        "temperature": None,
        "humidity": None,
        "wind_speed": None,
    }


def _read_cache(path: Path, cache_key: str, ttl_seconds: int, now: float) -> dict[str, Any] | None:
    try:
        cached = json.loads(path.read_text(encoding="utf-8"))
        if cached.get("cache_key") == cache_key and now - float(cached.get("cached_at", 0)) <= ttl_seconds:
            data = cached.get("data")
            return data if isinstance(data, dict) else None
    except Exception:
        return None
    return None


def _write_cache(path: Path, cache_key: str, data: dict[str, Any], now: float) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(path.suffix + ".tmp")
        temp.write_text(
            json.dumps({"cache_key": cache_key, "cached_at": now, "data": data}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        os.replace(temp, path)
    except Exception:
        return


def get_weather(
    location: dict[str, Any],
    config: dict[str, Any] | None,
    cache_path: Path,
    opener: Callable[..., Any] = urlopen,
    now: float | None = None,
    language: str = "en_US",
) -> dict[str, object]:
    config = config or {}
    city = str(location.get("city") or "").strip()
    if not city:
        return _unavailable()
    current_time = time.time() if now is None else now
    cache_key = f"{city}|{language}"
    ttl_seconds = max(0, int(config.get("cache_minutes", 30))) * 60
    cached = _read_cache(cache_path, cache_key, ttl_seconds, current_time)
    if cached is not None:
        return cached
    try:
        timeout = max(1.0, float(config.get("timeout_seconds", 3)))
        request = Request(
            f"https://wttr.in/{quote(city)}?format=j1&lang={'zh' if language == 'zh_CN' else 'en'}",
            headers={"User-Agent": "Hermes-environment-provider/1.0"},
        )
        with opener(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
        current = payload["current_condition"][0]
        descriptions = current.get("weatherDesc") or []
        data = {
            "available": True,
            "condition": descriptions[0].get("value") if descriptions else None,
            "temperature": int(current["temp_C"]),
            "humidity": int(current["humidity"]),
            "wind_speed": int(current["windspeedKmph"]),
            "source": "wttr.in",
        }
        _write_cache(cache_path, cache_key, data, current_time)
        return data
    except Exception:
        stale = _read_cache(cache_path, cache_key, 365 * 24 * 60 * 60, current_time)
        if stale is not None:
            stale = dict(stale)
            stale["stale"] = True
            return stale
        return _unavailable()
