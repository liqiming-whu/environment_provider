"""Register a fail-open environment context hook with Hermes."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .formatter import format_environment
from .locale import resolve_language
from .providers.battery_provider import get_battery
from .providers.location_provider import get_location
from .providers.time_provider import get_time
from .providers.weather_provider import get_weather

PLUGIN_ROOT = Path(__file__).resolve().parent


def _load_config() -> dict[str, Any]:
    try:
        import yaml

        data = yaml.safe_load((PLUGIN_ROOT / "config.yaml").read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _hermes_language(kwargs: dict[str, Any]) -> str | None:
    for key in ("language", "locale"):
        value = kwargs.get(key)
        if isinstance(value, str) and value.strip():
            return value
    config = kwargs.get("config")
    if isinstance(config, dict):
        for key in ("language", "locale"):
            value = config.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return None


def build_environment(
    config: dict[str, Any] | None = None,
    language: str = "en_US",
) -> dict[str, Any]:
    """Collect every provider independently so one failure cannot block a turn."""
    config = config or _load_config()
    location = get_location(config.get("location", {}))
    weather_config = config.get("weather", {})
    weather = (
        get_weather(
            location,
            weather_config,
            PLUGIN_ROOT / "cache" / "weather_cache.json",
            language=language,
        )
        if weather_config.get("enabled", True)
        else {"available": False}
    )
    device = (
        get_battery()
        if config.get("battery", {}).get("enabled", True)
        else {"available": False}
    )
    return {
        "time": get_time(),
        "location": location,
        "weather": weather,
        "device": device,
    }


def inject_environment(**kwargs: Any) -> dict[str, str] | None:
    """Hermes pre_llm_call callback. It always fails open."""
    try:
        config = _load_config()
        if not config.get("enabled", True):
            return None
        language = resolve_language(
            config.get("language", {}).get("mode", "auto"),
            _hermes_language(kwargs),
        )
        context = format_environment(
            build_environment(config, language),
            language,
            PLUGIN_ROOT / "locales",
            int(config.get("max_injected_chars", 1600)),
        )
        return {"context": context} if context else None
    except Exception:
        return None


def register(ctx: Any) -> None:
    ctx.register_hook("pre_llm_call", inject_environment)
