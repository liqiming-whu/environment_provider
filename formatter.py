"""Convert structured environment data into compact localized context."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _messages(language: str, locales_dir: Path) -> dict[str, Any]:
    target = locales_dir / f"{language}.json"
    if not target.is_file():
        target = locales_dir / "en_US.json"
    return json.loads(target.read_text(encoding="utf-8"))


def _value(data: dict[str, Any], key: str, unavailable: str) -> Any:
    value = data.get(key)
    return unavailable if value is None or value == "" else value


def format_environment(
    environment: dict[str, Any],
    language: str,
    locales_dir: Path,
    max_chars: int = 1600,
) -> str:
    msg = _messages(language, locales_dir)
    unavailable = msg["unavailable"]
    time_data = environment.get("time", {})
    location = environment.get("location", {})
    weather = environment.get("weather", {})
    device = environment.get("device", {})
    weekday_number = int(time_data.get("weekday_number", 0) or 0)
    weekdays = msg["weekdays"]
    weekday = weekdays[weekday_number - 1] if 1 <= weekday_number <= 7 else unavailable

    if language == "zh_CN":
        lines = [
            f"【{msg['environment']}】",
            f"{msg['datetime']}：{_value(time_data, 'datetime', unavailable)}",
            f"{msg['timezone']}：{_value(time_data, 'timezone', unavailable)}",
            f"{msg['weekday']}：{weekday}",
            f"{msg['location']}：{_value(location, 'city', unavailable)} / {_value(location, 'country', unavailable)}",
            f"{msg['weather']}：{_value(weather, 'condition', unavailable)}",
            f"{msg['temperature']}：{_value(weather, 'temperature', unavailable)}°C" if weather.get("temperature") is not None else f"{msg['temperature']}：{unavailable}",
            f"{msg['humidity']}：{_value(weather, 'humidity', unavailable)}%" if weather.get("humidity") is not None else f"{msg['humidity']}：{unavailable}",
            f"{msg['wind']}：{_value(weather, 'wind_speed', unavailable)} km/h" if weather.get("wind_speed") is not None else f"{msg['wind']}：{unavailable}",
            f"{msg['battery']}：{_value(device, 'battery_percent', unavailable)}%" if device.get("battery_percent") is not None else f"{msg['battery']}：{unavailable}",
            f"{msg['charging']}：{msg['charging_yes'] if device.get('charging') is True else msg['charging_no'] if device.get('charging') is False else unavailable}",
        ]
    else:
        lines = [
            f"[{msg['environment']}]",
            f"{msg['datetime']}: {_value(time_data, 'datetime', unavailable)}",
            f"{msg['timezone']}: {_value(time_data, 'timezone', unavailable)}",
            f"{msg['weekday']}: {weekday}",
            f"{msg['location']}: {_value(location, 'city', unavailable)}, {_value(location, 'country', unavailable)}",
            f"{msg['weather']}: {_value(weather, 'condition', unavailable)}",
            f"{msg['temperature']}: {_value(weather, 'temperature', unavailable)}°C" if weather.get("temperature") is not None else f"{msg['temperature']}: {unavailable}",
            f"{msg['humidity']}: {_value(weather, 'humidity', unavailable)}%" if weather.get("humidity") is not None else f"{msg['humidity']}: {unavailable}",
            f"{msg['wind']}: {_value(weather, 'wind_speed', unavailable)} km/h" if weather.get("wind_speed") is not None else f"{msg['wind']}: {unavailable}",
            f"{msg['battery']}: {_value(device, 'battery_percent', unavailable)}%" if device.get("battery_percent") is not None else f"{msg['battery']}: {unavailable}",
            f"{msg['charging']}: {msg['charging_yes'] if device.get('charging') is True else msg['charging_no'] if device.get('charging') is False else unavailable}",
        ]
    text = "\n".join(lines)
    return text if len(text) <= max_chars else text[: max(0, max_chars - 1)].rstrip() + "…"
