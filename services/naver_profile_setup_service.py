from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from playwright.async_api import BrowserContext, Playwright, async_playwright
from playwright.async_api import Error as PlaywrightError

ROOT_DIR = Path(__file__).resolve().parents[1]
PROFILE_ROOT = ROOT_DIR / "profiles" / "naver"
ALLOWED_ROLES = {"scraper", "publisher"}


@dataclass
class SetupSession:
    playwright: Playwright
    context: BrowserContext
    account_key: str
    role: str
    started_at: str


_SESSIONS: dict[str, SetupSession] = {}
_LOCK = asyncio.Lock()


def _normalize_key(account_key: str) -> str:
    key = (account_key or "").strip()
    if not key:
        raise RuntimeError("account_key는 필수입니다.")
    return key


def _normalize_role(role: str) -> str:
    r = (role or "").strip().lower()
    if r not in ALLOWED_ROLES:
        raise RuntimeError("role은 scraper 또는 publisher만 허용됩니다.")
    return r


def _session_id(role: str, account_key: str) -> str:
    return f"{_normalize_role(role)}:{_normalize_key(account_key)}"


def _profile_dir(role: str, account_key: str) -> Path:
    return PROFILE_ROOT / _normalize_role(role) / _normalize_key(account_key)


async def _is_logged_in(context: BrowserContext) -> bool:
    try:
        cookies = await context.cookies("https://www.naver.com")
        names = {c.get("name", "") for c in cookies}
        return ("NID_AUT" in names) or ("NID_SES" in names)
    except Exception:
        return False


async def start_profile_setup(account_key: str, role: str = "scraper") -> dict[str, Any]:
    key = _normalize_key(account_key)
    normalized_role = _normalize_role(role)
    sid = _session_id(normalized_role, key)

    async with _LOCK:
        if sid in _SESSIONS:
            return {"ok": False, 
                    "message": (
                        "이미 해당 account_key로 설정 창이 열려 있습니다. "
                        f"\n로그인 창을 종료했으면 프로필 취소 버튼 클릭 후 다시 시도하세요.")}

        profile_dir = _profile_dir(normalized_role, key)
        profile_dir.mkdir(parents=True, exist_ok=True)
        
        lock_files = ["SingletonLock", "SingletonCookie", "SingletonSocket"]
        existing_locks = [name for name in lock_files if (profile_dir / name).exists()]
        if existing_locks:
            return {
                "ok": False,
                "message": (
                    "프로필 폴더가 다른 브라우저에서 사용 중일 수 있습니다. "
                    f"\n사용 중인 브라우저/이전 세션을 모두 종료 후 다시 시도하세요. "
                    f"(locks={existing_locks})"
                ),
            }

        pw = await async_playwright().start()
        context = None
        try:
            context = await pw.chromium.launch_persistent_context(
                user_data_dir=str(profile_dir),
                headless=False,
                args=["--disable-blink-features=AutomationControlled"],
                viewport={"width": 1400, "height": 900},
            )

            # pages[0] 재사용 대신 새 탭 생성(닫힌 탭 참조 방지)
            page = context.pages[0] if context.pages else await context.new_page()
            await page.goto(
                "https://nid.naver.com/nidlogin.login",
                wait_until="domcontentloaded",
                timeout=60000,
            )

            _SESSIONS[sid] = SetupSession(
                playwright=pw,
                context=context,
                account_key=key,
                role=normalized_role,
                started_at=datetime.now().isoformat(timespec="seconds"),
            )

        except (PlaywrightError) as e:
            # 실패 시 리소스 정리
            try:
                if context is not None:
                    await context.close()
            except Exception:
                pass
            try:
                await pw.stop()
            except Exception:
                pass

            return {
                "ok": False,
                "message": (
                    "브라우저가 시작 직후 종료되었습니다. "
                    "같은 프로필을 사용하는 브라우저를 모두 종료하고 다시 시도하세요. "
                    f"(profile={profile_dir}, error={e})"
                ),
            }
        except Exception:
            try:
                if context is not None:
                    await context.close()
            except Exception:
                pass
            try:
                await pw.stop()
            except Exception:
                pass
            raise

    return {
        "ok": True,
        "message": "로그인 브라우저를 열었습니다. 네이버 로그인 후 멤버 카페 글 열람까지 확인하고 완료 버튼을 누르세요.",
        "account_key": key,
        "role": normalized_role,
        "profile_path": str(_profile_dir(normalized_role, key)),
    }


async def get_profile_setup_status(account_key: str, role: str = "scraper") -> dict[str, Any]:
    key = _normalize_key(account_key)
    normalized_role = _normalize_role(role)
    sid = _session_id(normalized_role, key)

    async with _LOCK:
        session = _SESSIONS.get(sid)

    return {
        "ok": True,
        "account_key": key,
        "role": normalized_role,
        "running": bool(session),
        "profile_exists": _profile_dir(normalized_role, key).exists(),
        "logged_in": (await _is_logged_in(session.context)) if session else False,
        "started_at": session.started_at if session else None,
        "profile_path": str(_profile_dir(normalized_role, key)),
    }


async def finish_profile_setup(account_key: str, role: str = "scraper") -> dict[str, Any]:
    key = _normalize_key(account_key)
    normalized_role = _normalize_role(role)
    sid = _session_id(normalized_role, key)

    async with _LOCK:
        session = _SESSIONS.pop(sid, None)

    if not session:
        return {"ok": False, "message": "진행 중인 설정 세션이 없습니다."}

    logged_in = await _is_logged_in(session.context)

    try:
        await session.context.close()
    finally:
        await session.playwright.stop()

    return {
        "ok": True,
        "message": "프로필 설정을 종료했습니다.",
        "account_key": key,
        "role": normalized_role,
        "logged_in": logged_in,
        "profile_path": str(_profile_dir(normalized_role, key)),
    }


async def cancel_profile_setup(account_key: str, role: str = "scraper") -> dict[str, Any]:
    key = _normalize_key(account_key)
    normalized_role = _normalize_role(role)
    sid = _session_id(normalized_role, key)

    async with _LOCK:
        session = _SESSIONS.pop(sid, None)

    if not session:
        return {"ok": True, "message": "이미 종료된 상태입니다."}

    try:
        await session.context.close()
    finally:
        await session.playwright.stop()

    return {
        "ok": True,
        "message": "프로필 설정을 취소했습니다.",
        "account_key": key,
        "role": normalized_role,
    }
