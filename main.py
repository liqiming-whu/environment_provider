"""Inject fail-open environment context into the current model request."""

from __future__ import annotations

from copy import deepcopy
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
    location = get_location(config.get("location", {}), language)
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


_CONTEXT_OPEN = '<environment_context transient="true">'
_CONTEXT_CLOSE = "</environment_context>"
_LEGACY_MARKERS = ("【当前环境】", "[Current Environment]")


def _environment_text(kwargs: dict[str, Any]) -> str:
    try:
        config = _load_config()
        if not config.get("enabled", True):
            return ""
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
        return context
    except Exception:
        return ""


def _strip_environment_suffix(text: str) -> str:
    """Remove environment blocks produced by this plugin from an API copy."""
    start = text.rfind(_CONTEXT_OPEN)
    if start >= 0 and text.rstrip().endswith(_CONTEXT_CLOSE):
        return text[:start].rstrip()
    for marker in _LEGACY_MARKERS:
        start = text.rfind("\n\n" + marker)
        if start >= 0:
            return text[:start].rstrip()
    return text


def _clean_content(content: Any) -> Any:
    if isinstance(content, str):
        return _strip_environment_suffix(content)
    if not isinstance(content, list):
        return content
    cleaned = deepcopy(content)
    for part in cleaned:
        if isinstance(part, dict) and isinstance(part.get("text"), str):
            part["text"] = _strip_environment_suffix(part["text"])
    return cleaned


def _append_context(content: Any, context: str, *, responses_input: bool) -> Any:
    block = f"{_CONTEXT_OPEN}\n{context}\n{_CONTEXT_CLOSE}"
    if isinstance(content, str):
        return f"{content.rstrip()}\n\n{block}" if content.strip() else block
    if isinstance(content, list):
        result = deepcopy(content)
        result.append({"type": "input_text" if responses_input else "text", "text": block})
        return result
    return content


def inject_environment_request(**kwargs: Any) -> dict[str, Any] | None:
    """Hermes ``llm_request`` middleware; changes only the outbound copy."""
    try:
        request = kwargs.get("request")
        if not isinstance(request, dict):
            return None
        context = _environment_text(kwargs)
        if not context:
            return None

        updated = deepcopy(request)
        field = "messages" if isinstance(updated.get("messages"), list) else "input"
        payload = updated.get(field)

        if isinstance(payload, str) and field == "input":
            updated[field] = _append_context(
                _strip_environment_suffix(payload), context, responses_input=True
            )
            return {"request": updated, "source": "environment_provider"}
        if not isinstance(payload, list):
            return None

        current_user = -1
        for index, message in enumerate(payload):
            if not isinstance(message, dict) or message.get("role") != "user":
                continue
            message["content"] = _clean_content(message.get("content"))
            current_user = index
        if current_user < 0:
            return None
        payload[current_user]["content"] = _append_context(
            payload[current_user].get("content"),
            context,
            responses_input=(field == "input"),
        )
        return {"request": updated, "source": "environment_provider"}
    except Exception:
        return None


def register(ctx: Any) -> None:
    ctx.register_middleware("llm_request", inject_environment_request)
