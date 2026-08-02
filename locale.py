"""Resolve the output locale without coupling to Hermes internals."""

from __future__ import annotations

import locale as system_locale
import os

SUPPORTED = {"zh_CN", "en_US"}


def normalize_language(value: str | None) -> str | None:
    if not value:
        return None
    normalized = value.replace("-", "_").split(".", 1)[0].strip()
    lowered = normalized.lower()
    if lowered.startswith("zh"):
        return "zh_CN"
    if lowered.startswith("en"):
        return "en_US"
    return normalized if normalized in SUPPORTED else None


def resolve_language(mode: str | None, hermes_language: str | None = None) -> str:
    configured = normalize_language(mode)
    if configured:
        return configured
    hermes = normalize_language(hermes_language)
    if hermes:
        return hermes
    os_language = os.environ.get("LC_ALL") or os.environ.get("LC_MESSAGES") or os.environ.get("LANG")
    detected = normalize_language(os_language)
    if detected:
        return detected
    try:
        detected = normalize_language(system_locale.getlocale()[0])
    except Exception:
        detected = None
    return detected or "en_US"

