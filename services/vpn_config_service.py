from __future__ import annotations

import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
VPN_CONFIG_PATH = ROOT_DIR / "data" / "vpn_config.json"

DEFAULT_VPN_CONFIG = {
    "enabled": False,
    "run_as_admin": True,
    "cli_dir": r"C:\\Program Files\\ExpressVPN\\",
    "activation_code": "",
    "activate_before_publish": True,
    "connect_location": "smart",
    "command_timeout_sec": 120,
    "settle_wait_sec": 3,
}


def _clean(value: object) -> str:
    return str(value or "").strip()


def _to_bool(value: object, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return bool(value)
    text = _clean(value).lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    return default


def _to_int(value: object, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except Exception:
        parsed = default
    return max(minimum, min(maximum, parsed))


def _normalize(payload: dict | None) -> dict:
    src = payload if isinstance(payload, dict) else {}
    cfg = dict(DEFAULT_VPN_CONFIG)

    cfg["enabled"] = _to_bool(src.get("enabled"), cfg["enabled"])
    cfg["run_as_admin"] = _to_bool(src.get("run_as_admin"), cfg["run_as_admin"])
    cfg["activate_before_publish"] = _to_bool(
        src.get("activate_before_publish"),
        cfg["activate_before_publish"],
    )

    cli_dir = _clean(src.get("cli_dir")) or cfg["cli_dir"]
    cfg["cli_dir"] = cli_dir

    cfg["activation_code"] = _clean(src.get("activation_code"))
    cfg["connect_location"] = _clean(src.get("connect_location")) or "smart"
    cfg["command_timeout_sec"] = _to_int(src.get("command_timeout_sec"), 120, 10, 900)
    cfg["settle_wait_sec"] = _to_int(src.get("settle_wait_sec"), 3, 0, 60)

    return cfg


def load_vpn_config() -> dict:
    if not VPN_CONFIG_PATH.exists():
        VPN_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        VPN_CONFIG_PATH.write_text(
            json.dumps(DEFAULT_VPN_CONFIG, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return dict(DEFAULT_VPN_CONFIG)

    try:
        raw = VPN_CONFIG_PATH.read_text(encoding="utf-8-sig").strip()
        if not raw:
            return dict(DEFAULT_VPN_CONFIG)
        parsed = json.loads(raw)
        return _normalize(parsed)
    except Exception:
        return dict(DEFAULT_VPN_CONFIG)


def save_vpn_config(payload: dict | None) -> dict:
    cfg = _normalize(payload)
    VPN_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    VPN_CONFIG_PATH.write_text(
        json.dumps(cfg, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return cfg


def _mask(value: str) -> str:
    text = _clean(value)
    if not text:
        return ""
    if len(text) <= 8:
        return "*" * len(text)
    return f"{text[:4]}...{text[-4:]}"


def get_vpn_config_for_admin() -> dict:
    cfg = load_vpn_config()
    return {
        **cfg,
        "has_activation_code": bool(cfg.get("activation_code")),
        "activation_code_masked": _mask(_clean(cfg.get("activation_code"))),
        "activation_code": "",
    }


def update_vpn_config(payload: dict | None) -> dict:
    current = load_vpn_config()
    src = payload if isinstance(payload, dict) else {}
    merged = dict(current)

    for key in DEFAULT_VPN_CONFIG.keys():
        if key in src:
            merged[key] = src.get(key)

    # activation_code empty string means "keep old value"
    activation_code = _clean(src.get("activation_code"))
    if "activation_code" in src and activation_code:
        merged["activation_code"] = activation_code
    elif "activation_code" not in src:
        merged["activation_code"] = current.get("activation_code", "")
    else:
        merged["activation_code"] = current.get("activation_code", "")

    saved = save_vpn_config(merged)
    return {"ok": True, "config": get_vpn_config_for_admin(), "saved": saved}


def resolve_activation_code(override_code: str = "") -> str:
    override = _clean(override_code)
    if override:
        return override
    cfg = load_vpn_config()
    return _clean(cfg.get("activation_code"))
