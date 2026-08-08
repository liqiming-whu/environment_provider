"""wttr.in weather provider with a small atomic JSON cache."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Callable
from urllib.parse import quote
from urllib.request import Request, urlopen


WEATHER_ZH_FALLBACK = {
    "113": "晴",
    "116": "局部多云",
    "119": "多云",
    "122": "阴",
    "143": "薄雾",
    "149": "烟霾",
    "176": "局部可能有雨",
    "179": "局部可能有雪",
    "182": "局部可能有雨夹雪",
    "185": "局部可能有冻毛毛雨",
    "200": "局部可能有雷暴",
    "227": "风吹雪",
    "230": "暴雪",
    "248": "有雾",
    "260": "冻雾",
    "263": "局部毛毛雨",
    "266": "小毛毛雨",
    "281": "冻毛毛雨",
    "284": "强冻毛毛雨",
    "293": "局部小雨",
    "296": "小雨",
    "299": "间歇性中雨",
    "302": "中雨",
    "305": "间歇性大雨",
    "308": "大雨",
    "311": "小冻雨",
    "314": "中到大冻雨",
    "317": "小雨夹雪",
    "320": "中到大雨夹雪",
    "323": "局部小雪",
    "326": "小雪",
    "329": "局部中雪",
    "332": "中雪",
    "335": "局部大雪",
    "338": "大雪",
    "350": "冰粒",
    "353": "小阵雨",
    "356": "中到大阵雨",
    "359": "暴雨",
    "362": "小雨夹雪阵雨",
    "365": "中到大雨夹雪阵雨",
    "368": "小阵雪",
    "371": "中到大阵雪",
    "374": "小冰粒阵雨",
    "377": "中到大冰粒阵雨",
    "386": "局部小雨伴雷电",
    "389": "中到大雨伴雷电",
    "392": "局部小雪伴雷电",
    "395": "中到大雪伴雷电",
}


def _unavailable() -> dict[str, object]:
    return {
        "available": False,
        "condition": None,
        "temperature": None,
        "humidity": None,
        "wind_speed": None,
    }


def _description_value(value: Any) -> str | None:
    if isinstance(value, list) and value:
        value = value[0]
    if isinstance(value, dict):
        text = str(value.get("value") or "").strip()
        return text or None
    return None


def _condition(current: dict[str, Any], language: str) -> str | None:
    if language == "zh_CN":
        for key in ("lang_zh-cn", "lang_zh", "lang_xx"):
            localized = _description_value(current.get(key))
            if localized:
                return localized
        fallback = WEATHER_ZH_FALLBACK.get(str(current.get("weatherCode") or ""))
        if fallback:
            return fallback
    return _description_value(current.get("weatherDesc"))


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
    city = str(location.get("query_city") or location.get("city") or "").strip()
    country = str(location.get("query_country") or "").strip()
    if not city:
        return _unavailable()
    query = ",".join(part for part in (city, country) if part)
    current_time = time.time() if now is None else now
    cache_key = f"v2|{query}|{language}"
    ttl_seconds = max(0, int(config.get("cache_minutes", 30))) * 60
    cached = _read_cache(cache_path, cache_key, ttl_seconds, current_time)
    if cached is not None:
        return cached
    try:
        timeout = max(1.0, float(config.get("timeout_seconds", 3)))
        request = Request(
            f"https://wttr.in/{quote(query)}?format=j1&lang={'zh-cn' if language == 'zh_CN' else 'en'}",
            headers={"User-Agent": "Hermes-environment-provider/1.0"},
        )
        with opener(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
        current = payload["current_condition"][0]
        data = {
            "available": True,
            "condition": _condition(current, language),
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
