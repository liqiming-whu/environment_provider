"""Optional psutil-based battery provider."""

from __future__ import annotations


def get_battery() -> dict[str, object]:
    try:
        import psutil

        battery = psutil.sensors_battery()
        if battery is None:
            return {"available": False, "battery_percent": None, "charging": None}
        return {
            "available": True,
            "battery_percent": round(float(battery.percent)),
            "charging": bool(battery.power_plugged),
        }
    except Exception:
        return {"available": False, "battery_percent": None, "charging": None}
