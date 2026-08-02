from __future__ import annotations

import json
import tempfile
import unittest
import sys
from types import SimpleNamespace
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from environment_provider.formatter import format_environment
from environment_provider.main import _load_config, inject_environment, register
from environment_provider.providers.battery_provider import get_battery
from environment_provider.providers.location_provider import get_location
from environment_provider.providers.time_provider import get_time
from environment_provider.providers.weather_provider import WEATHER_ZH_FALLBACK, get_weather


EXPECTED_WEATHER_CODES = {
    "113", "116", "119", "122", "143", "176", "179", "182", "185", "200",
    "227", "230", "248", "260", "263", "266", "281", "284", "293", "296",
    "299", "302", "305", "308", "311", "314", "317", "320", "323", "326",
    "329", "332", "335", "338", "350", "353", "356", "359", "362", "365",
    "368", "371", "374", "377", "386", "389", "392", "395",
}


class _Response:
    def __init__(self, payload: dict):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class EnvironmentProviderTests(unittest.TestCase):
    def setUp(self):
        self.plugin_root = Path(__file__).resolve().parents[1]
        self.sample = {
            "time": get_time(datetime(2026, 8, 2, 21, 30, tzinfo=timezone.utc)),
            "location": {"city": "Wuhan", "country": "China", "source": "manual"},
            "weather": {"condition": "Clear", "temperature": 34, "humidity": 45, "wind_speed": 12},
            "device": {"battery_percent": 72, "charging": False},
        }

    def test_time_contains_weekday(self):
        self.assertEqual(self.sample["time"]["weekday_number"], 7)

    def test_chinese_output_contains_weekday(self):
        text = format_environment(self.sample, "zh_CN", self.plugin_root / "locales")
        self.assertIn("星期：星期日", text)
        self.assertIn("电量：72%", text)

    def test_english_output_contains_weekday(self):
        text = format_environment(self.sample, "en_US", self.plugin_root / "locales")
        self.assertIn("Weekday: Sunday", text)

    def test_localized_location_uses_display_name_and_keeps_query_name(self):
        config = {
            "mode": "manual",
            "query": {"city": "Wuhan", "country": "China"},
            "display": {
                "zh_CN": {"city": "武汉", "country": "中国"},
                "en_US": {"city": "Wuhan", "country": "China"},
            },
        }
        zh = get_location(config, "zh_CN")
        en = get_location(config, "en_US")
        self.assertEqual((zh["city"], zh["country"]), ("武汉", "中国"))
        self.assertEqual((en["city"], en["country"]), ("Wuhan", "China"))
        self.assertEqual((zh["query_city"], zh["query_country"]), ("Wuhan", "China"))

    def test_legacy_location_config_remains_supported(self):
        location = get_location({"city": "Wuhan", "country": "China"}, "zh_CN")
        self.assertEqual((location["city"], location["country"]), ("Wuhan", "China"))

    def test_weather_api_failure_is_unavailable(self):
        def fail(*args, **kwargs):
            raise OSError("offline")

        with tempfile.TemporaryDirectory() as temp:
            result = get_weather(
                {"city": "Wuhan"}, {}, Path(temp) / "cache.json", opener=fail, now=1
            )
        self.assertFalse(result["available"])

    def test_weather_response_and_cache(self):
        payload = {"current_condition": [{
            "weatherDesc": [{"value": "Sunny"}],
            "lang_zh-cn": [{"value": "晴"}], "weatherCode": "113", "temp_C": "34",
            "humidity": "45", "windspeedKmph": "12"
        }]}
        calls = []

        def open_ok(*args, **kwargs):
            calls.append(1)
            return _Response(payload)

        with tempfile.TemporaryDirectory() as temp:
            cache = Path(temp) / "cache.json"
            location = {"query_city": "Wuhan", "query_country": "China"}
            first = get_weather(location, {}, cache, opener=open_ok, now=10, language="zh_CN")
            second = get_weather(location, {}, cache, opener=open_ok, now=20, language="zh_CN")
        self.assertTrue(first["available"])
        self.assertEqual(first["condition"], "晴")
        self.assertEqual(first, second)
        self.assertEqual(len(calls), 1)

    def test_chinese_weather_code_fallback(self):
        payload = {"current_condition": [{
            "weatherDesc": [{"value": "Partly cloudy"}],
            "weatherCode": "116", "temp_C": "31", "humidity": "60", "windspeedKmph": "8"
        }]}

        with tempfile.TemporaryDirectory() as temp:
            result = get_weather(
                {"query_city": "Wuhan"}, {}, Path(temp) / "cache.json",
                opener=lambda *args, **kwargs: _Response(payload), now=1, language="zh_CN",
            )
        self.assertEqual(result["condition"], "局部多云")

    def test_chinese_weather_fallback_covers_all_wwo_codes(self):
        self.assertEqual(set(WEATHER_ZH_FALLBACK), EXPECTED_WEATHER_CODES)
        self.assertEqual(WEATHER_ZH_FALLBACK["302"], "中雨")
        self.assertEqual(WEATHER_ZH_FALLBACK["308"], "大雨")
        self.assertEqual(WEATHER_ZH_FALLBACK["359"], "暴雨")
        self.assertEqual(WEATHER_ZH_FALLBACK["395"], "中到大雪伴雷电")

    def test_battery_available(self):
        fake_psutil = SimpleNamespace(
            sensors_battery=lambda: SimpleNamespace(percent=71.6, power_plugged=True)
        )
        with patch.dict(sys.modules, {"psutil": fake_psutil}):
            result = get_battery()
        self.assertEqual(result["battery_percent"], 72)
        self.assertTrue(result["charging"])

    def test_battery_unsupported(self):
        fake_psutil = SimpleNamespace(sensors_battery=lambda: None)
        with patch.dict(sys.modules, {"psutil": fake_psutil}):
            result = get_battery()
        self.assertFalse(result["available"])

    def test_plugin_loads_without_config(self):
        with tempfile.TemporaryDirectory() as temp, patch(
            "environment_provider.main.PLUGIN_ROOT", Path(temp)
        ):
            self.assertEqual(_load_config(), {})

    def test_hook_returns_context(self):
        with patch("environment_provider.main.build_environment", return_value=self.sample):
            result = inject_environment(language="zh_CN")
        self.assertIsInstance(result, dict)
        self.assertIn("context", result)
        self.assertIn("星期", result["context"])

    def test_registers_pre_llm_hook(self):
        calls = []

        class Context:
            def register_hook(self, name, callback):
                calls.append((name, callback))

        register(Context())
        self.assertEqual(calls, [("pre_llm_call", inject_environment)])


if __name__ == "__main__":
    unittest.main()
