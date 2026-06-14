# services/ai_runtime.py
from __future__ import annotations

import os
import re
import json
from pathlib import Path
from dotenv import dotenv_values

ROOT_DIR = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT_DIR / ".env"
MODELS_PATH = ROOT_DIR / "data" / "models.json"

GEMINI_DEFAULT_MODEL = "gemini-2.5-flash"
GPT_DEFAULT_MODEL = "gpt-4.1-mini"


def _normalize(value: str | None) -> str:
    return (value or "").strip().strip('"').strip("'")


def _load_key_values() -> dict[str, str]:
    values: dict[str, str] = {}

    if ENV_PATH.exists():
        file_values = dotenv_values(ENV_PATH)
        for key, value in file_values.items():
            values[key] = _normalize(value)

    for key in ("GEMINI_API_KEY", "OPENAI_API_KEY"):
        if not values.get(key):
            values[key] = _normalize(os.getenv(key))

    return values


def get_api_key_status() -> dict[str, bool]:
    values = _load_key_values()
    return {
        "gemini_exists": bool(values.get("GEMINI_API_KEY")),
        "openai_exists": bool(values.get("OPENAI_API_KEY")),
    }


def get_api_key(provider: str) -> str:
    values = _load_key_values()
    provider = (provider or "").lower()

    if provider == "gemini":
        return values.get("GEMINI_API_KEY", "")
    if provider in {"gpt", "openai"}:
        return values.get("OPENAI_API_KEY", "")
    return ""


def _upsert_env_key(key: str, value: str) -> None:
    value = _normalize(value)
    if not value:
        return

    if ENV_PATH.exists():
        lines = ENV_PATH.read_text(encoding="utf-8").splitlines()
    else:
        lines = []

    pattern = re.compile(rf"^\s*{re.escape(key)}\s*=")
    replaced = False
    new_lines: list[str] = []

    for line in lines:
        if pattern.match(line):
            if not replaced:
                new_lines.append(f"{key}={value}")
                replaced = True
            continue
        new_lines.append(line)

    if not replaced:
        new_lines.append(f"{key}={value}")

    ENV_PATH.write_text("\n".join(new_lines).strip() + "\n", encoding="utf-8")


def save_missing_api_keys(gemini_api_key: str = "", openai_api_key: str = "") -> dict:
    status = get_api_key_status()

    if not status["gemini_exists"] and _normalize(gemini_api_key):
        _upsert_env_key("GEMINI_API_KEY", gemini_api_key)
    if not status["openai_exists"] and _normalize(openai_api_key):
        _upsert_env_key("OPENAI_API_KEY", openai_api_key)

    new_status = get_api_key_status()
    missing = []
    if not new_status["gemini_exists"]:
        missing.append("gemini")
    if not new_status["openai_exists"]:
        missing.append("gpt")

    return {
        "ok": len(missing) == 0,
        "missing": missing,
        "status": new_status,
    }


def _mask_key(value: str) -> str:
    v = _normalize(value)
    if not v:
        return ""
    if len(v) <= 8:
        return "*" * len(v)
    return f"{v[:4]}...{v[-4:]}"


def get_api_key_status_for_admin() -> dict:
    values = _load_key_values()
    gemini = values.get("GEMINI_API_KEY", "")
    openai = values.get("OPENAI_API_KEY", "")
    return {
        "gemini_exists": bool(gemini),
        "openai_exists": bool(openai),
        "gemini_masked": _mask_key(gemini),
        "openai_masked": _mask_key(openai),
    }


def update_api_keys(gemini_api_key: str = "", openai_api_key: str = "") -> dict:
    gemini = _normalize(gemini_api_key)
    openai = _normalize(openai_api_key)

    updated = []

    if gemini:
        _upsert_env_key("GEMINI_API_KEY", gemini)
        updated.append("gemini")

    if openai:
        _upsert_env_key("OPENAI_API_KEY", openai)
        updated.append("gpt")

    if not updated:
        return {
            "ok": False,
            "message": "변경할 키를 1개 이상 입력해 주세요.",
            "updated": [],
            "status": get_api_key_status_for_admin(),
        }

    return {
        "ok": True,
        "message": "API 키가 저장되었습니다.",
        "updated": updated,
        "status": get_api_key_status_for_admin(),
    }

def _normalize_provider(provider: str) -> str:
    p = (provider or "").strip().lower()
    if p == "openai":
        p = "gpt"
    return p


def _load_model_config() -> dict[str, list[str]]:
    # 기본값 (models.json이 없으면 이 값 사용)
    default = {
        "gemini": [GEMINI_DEFAULT_MODEL, "gemini-2.5-pro"],
        "gpt": [GPT_DEFAULT_MODEL, "gpt-4.1", "gpt-4o-mini"],
    }

    if not MODELS_PATH.exists():
        return default

    try:
        raw = json.loads(MODELS_PATH.read_text(encoding="utf-8"))
        result: dict[str, list[str]] = {"gemini": [], "gpt": []}
        for key in ("gemini", "gpt"):
            values = raw.get(key, [])
            if isinstance(values, list):
                cleaned = [str(v).strip() for v in values if str(v).strip()]
                result[key] = cleaned or default[key]
            else:
                result[key] = default[key]
        return result
    except Exception:
        return default


def get_supported_models(provider: str) -> list[str]:
    p = _normalize_provider(provider)
    if p not in {"gemini", "gpt"}:
        raise ValueError(f"지원하지 않는 provider: {provider}")
    return _load_model_config().get(p, [])