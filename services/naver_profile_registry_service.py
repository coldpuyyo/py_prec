from __future__ import annotations

import base64
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT_DIR / ".env"
PROFILES_JSON_PATH = ROOT_DIR / "data" / "naver_profiles.json"
ALLOWED_ROLES = {"scraper", "publisher"}
PASSWORD_PREFIX = "enc:v1:"

load_dotenv(ENV_PATH)


def _clean(value) -> str:
    return str(value or "").strip()


def _normalize_role(role: str) -> str:
    normalized = _clean(role).lower()
    if normalized not in ALLOWED_ROLES:
        raise RuntimeError("role은 scraper 또는 publisher만 허용됩니다.")
    return normalized


def _get_crypto_secret() -> str:
    return (
        _clean(os.getenv("NAVER_PROFILE_SECRET"))
        or _clean(os.getenv("SESSION_SECRET"))
        or _clean(os.getenv("ADMIN_PASSWORD"))
    )


def _get_cipher() -> Fernet:
    secret = _get_crypto_secret()
    if not secret:
        raise RuntimeError(
            "NAVER_PROFILE_SECRET 또는 SESSION_SECRET을 .env에 설정해야 프로필 비밀번호를 암호화할 수 있습니다."
        )

    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def _is_encrypted_password(value: str) -> bool:
    return _clean(value).startswith(PASSWORD_PREFIX)


def _encrypt_password(plain_text: str) -> str:
    value = _clean(plain_text)
    if not value:
        return ""

    if _is_encrypted_password(value):
        return value

    token = _get_cipher().encrypt(value.encode("utf-8")).decode("utf-8")
    return f"{PASSWORD_PREFIX}{token}"


def _decrypt_password(stored_value: str, account_key: str = "") -> str:
    value = _clean(stored_value)
    if not value:
        return ""

    if not _is_encrypted_password(value):
        return value

    token = value[len(PASSWORD_PREFIX):]
    try:
        return _get_cipher().decrypt(token.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        hint = _clean(account_key) or "unknown"
        raise RuntimeError(
            f"프로필 비밀번호 복호화에 실패했습니다. 암호화 키를 확인하세요. (account_key={hint})"
        )


def _serialize_profile(item: dict) -> dict:
    copied = dict(item)
    copied["login_password"] = _encrypt_password(_clean(copied.get("login_password")))
    return copied


def _read_profiles() -> list[dict]:
    if not PROFILES_JSON_PATH.exists():
        return []

    raw = PROFILES_JSON_PATH.read_text(encoding="utf-8-sig").strip()
    if not raw:
        return []

    data = json.loads(raw)
    if not isinstance(data, list):
        return []

    items: list[dict] = []
    migrate_needed = False

    for row in data:
        if not isinstance(row, dict):
            continue

        copied = dict(row)
        account_key = _clean(copied.get("account_key"))
        stored_password = _clean(copied.get("login_password"))
        copied["login_password"] = _decrypt_password(stored_password, account_key=account_key)
        if stored_password and not _is_encrypted_password(stored_password):
            migrate_needed = True

        items.append(copied)

    if migrate_needed:
        _write_profiles(items)

    return items


def _write_profiles(items: list[dict]) -> None:
    serialized = [_serialize_profile(x) for x in items if isinstance(x, dict)]
    PROFILES_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROFILES_JSON_PATH.write_text(
        json.dumps(serialized, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _to_public_profile(item: dict) -> dict:
    copied = dict(item)
    copied["has_login_password"] = bool(_clean(copied.get("login_password")))
    copied["login_password"] = ""
    return copied


def list_profiles(role: str = "", active_only: bool = False, include_secret: bool = False) -> list[dict]:
    items = _read_profiles()

    if role:
        normalized_role = _normalize_role(role)
        items = [x for x in items if _clean(x.get("role")).lower() == normalized_role]

    if active_only:
        items = [x for x in items if bool(x.get("active", True))]

    if not include_secret:
        items = [_to_public_profile(x) for x in items]

    return items


def get_profile(account_key: str) -> dict | None:
    key = _clean(account_key)
    for item in _read_profiles():
        if _clean(item.get("account_key")) == key:
            return item
    return None


def upsert_profile(payload: dict) -> dict:
    key = _clean(payload.get("account_key"))
    role = _normalize_role(payload.get("role", ""))
    label = _clean(payload.get("label"))
    blog_id = _clean(payload.get("blog_id"))
    login_id = _clean(payload.get("login_id"))
    login_password = _clean(payload.get("login_password"))
    active = bool(payload.get("active", True))

    if not key:
        return {"ok": False, "message": "account_key는 필수입니다."}

    now = datetime.now().isoformat(timespec="seconds")
    items = _read_profiles()
    target = next((x for x in items if _clean(x.get("account_key")) == key), None)

    if target:
        target["role"] = role
        target["label"] = label
        target["blog_id"] = blog_id
        target["active"] = active
        if login_id:
            target["login_id"] = login_id
        if login_password:
            target["login_password"] = login_password
        target["updated_at"] = now
    else:
        items.append({
            "account_key": key,
            "role": role,
            "label": label,
            "blog_id": blog_id,
            "login_id": login_id,
            "login_password": login_password,
            "active": active,
            "created_at": now,
            "updated_at": now,
        })

    _write_profiles(items)
    return {"ok": True}


def delete_profile(account_key: str) -> dict:
    key = _clean(account_key)
    if not key:
        return {"ok": False, "message": "account_key가 비어 있습니다."}

    items = _read_profiles()
    new_items = [x for x in items if _clean(x.get("account_key")) != key]
    if len(new_items) == len(items):
        return {"ok": False, "message": "삭제 대상이 없습니다."}

    _write_profiles(new_items)
    return {"ok": True}


def is_active_profile_for_role(account_key: str, role: str) -> bool:
    key = _clean(account_key)
    normalized_role = _normalize_role(role)
    profile = get_profile(key)
    if not profile:
        return False

    return bool(profile.get("active", True)) and _clean(profile.get("role")).lower() == normalized_role