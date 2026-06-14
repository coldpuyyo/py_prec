# C:\Users\Cold_Puyo\Documents\Py_prec\services\trial_guard.py
from __future__ import annotations

import hashlib
import hmac
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import winreg  # Windows only
except Exception:
    winreg = None


# 앱마다 바꿔도 됨
APP_NAME_DEFAULT = "PyPrecApp"
TRIAL_DAYS_DEFAULT = 30

# HKCU 기준 (관리자 권한 불필요)
REG_SUBKEY = r"Software\PyPrecApp\Trial"

# 임의 키 (원하면 바꾸세요)
_HMAC_KEY = b"py_prec_trial_guard_v1_change_this_secret"
_STATE_FIELDS = ("v", "app", "first_run_ts", "expires_ts", "last_run_ts")


def _now_ts() -> int:
    return int(datetime.now(timezone.utc).timestamp())


def _machine_fingerprint() -> str:
    raw = "|".join([
        os.getenv("COMPUTERNAME", ""),
        os.getenv("PROCESSOR_IDENTIFIER", ""),
        os.getenv("USERNAME", ""),
    ])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _state_file_path(app_name: str) -> Path:
    base = os.getenv("LOCALAPPDATA")
    if not base:
        base = str(Path.home() / "AppData" / "Local")
    return Path(base) / app_name / "trial_state.json"


def _sign_payload(state: dict, machine_fp: str) -> str:
    payload = {k: state.get(k) for k in _STATE_FIELDS}
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    msg = f"{text}|{machine_fp}".encode("utf-8")
    return hmac.new(_HMAC_KEY, msg, hashlib.sha256).hexdigest()


def _make_state(app_name: str, trial_days: int, now_ts: int, machine_fp: str) -> dict:
    state = {
        "v": 1,
        "app": app_name,
        "first_run_ts": now_ts,
        "expires_ts": now_ts + (trial_days * 86400),
        "last_run_ts": now_ts,
    }
    state["sig"] = _sign_payload(state, machine_fp)
    return state


def _is_valid_state(state: dict, app_name: str, trial_days: int, machine_fp: str) -> bool:
    if not isinstance(state, dict):
        return False
    for k in _STATE_FIELDS:
        if k not in state:
            return False

    if state.get("app") != app_name:
        return False
    if state.get("v") != 1:
        return False

    try:
        first_run_ts = int(state["first_run_ts"])
        expires_ts = int(state["expires_ts"])
        last_run_ts = int(state["last_run_ts"])
    except Exception:
        return False

    if first_run_ts <= 0 or expires_ts <= 0 or last_run_ts <= 0:
        return False
    if expires_ts != first_run_ts + (trial_days * 86400):
        return False

    sig = str(state.get("sig", ""))
    if not sig:
        return False
    if sig != _sign_payload(state, machine_fp):
        return False

    return True


def _read_file_state(path: Path) -> dict | None:
    try:
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _write_file_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _read_registry_state() -> dict | None:
    if winreg is None:
        return None
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_SUBKEY, 0, winreg.KEY_READ) as key:
            raw, _ = winreg.QueryValueEx(key, "state")
        return json.loads(str(raw))
    except Exception:
        return None


def _write_registry_state(state: dict) -> None:
    if winreg is None:
        return
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, REG_SUBKEY) as key:
        winreg.SetValueEx(key, "state", 0, winreg.REG_SZ, json.dumps(state, ensure_ascii=False))


def _fmt_local(ts: int) -> str:
    return datetime.fromtimestamp(int(ts), tz=timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S")


def enforce_trial_or_exit(app_name: str = APP_NAME_DEFAULT, trial_days: int = TRIAL_DAYS_DEFAULT) -> None:
    now_ts = _now_ts()
    machine_fp = _machine_fingerprint()
    file_path = _state_file_path(app_name)

    file_state = _read_file_state(file_path)
    reg_state = _read_registry_state()

    valid_states = []
    if _is_valid_state(file_state, app_name, trial_days, machine_fp):
        valid_states.append(file_state)
    if _is_valid_state(reg_state, app_name, trial_days, machine_fp):
        valid_states.append(reg_state)

    if not valid_states:
        state = _make_state(app_name, trial_days, now_ts, machine_fp)
    else:
        # 둘 다 있으면 더 이른 first_run_ts를 기준으로 잠금
        state = min(valid_states, key=lambda s: int(s["first_run_ts"]))

    # 시계 되돌림 방지 (5분 이상 과거면 종료)
    if now_ts + 300 < int(state["last_run_ts"]):
        print("실행 실패: 시스템 시간이 이전 실행 시각보다 과거입니다.")
        sys.exit(1)

    # 만료 검사
    if now_ts > int(state["expires_ts"]):
        print(
            "실행 기간이 만료되었습니다.\n"
            f"최초 실행: {_fmt_local(int(state['first_run_ts']))}\n"
            f"만료 시각: {_fmt_local(int(state['expires_ts']))}"
        )
        sys.exit(1)

    # last_run 갱신 + 서명 재생성
    state["last_run_ts"] = max(now_ts, int(state["last_run_ts"]))
    state["sig"] = _sign_payload(state, machine_fp)

    # 파일/레지스트리 동기화
    _write_file_state(file_path, state)
    _write_registry_state(state)
