from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path

from playwright.sync_api import BrowserContext, Playwright
from services.app_logger import get_logger

ROOT_DIR = Path(__file__).resolve().parents[1]
PROFILE_ROOT = ROOT_DIR / "profiles" / "naver"
ALLOWED_PROFILE_ROLES = {"scraper", "publisher"}
logger = get_logger(__name__)

def _normalize_role(profile_role: str) -> str:
    role = (profile_role or "").strip().lower()
    if role not in ALLOWED_PROFILE_ROLES:
        raise RuntimeError("profile_role은 scraper 또는 publisher만 허용됩니다.")
    return role


def _resolve_profile_dir(naver_account_key: str, profile_role: str = "scraper") -> Path:
    key = (naver_account_key or "").strip() or "default"
    role = _normalize_role(profile_role)
    return PROFILE_ROOT / role / key


def ensure_profile_exists(naver_account_key: str, profile_role: str = "scraper") -> Path:
    profile_dir = _resolve_profile_dir(naver_account_key, profile_role)
    if profile_dir.exists():
        logger.info("naver profile exists path=%s", profile_dir)
        return profile_dir

    # 레거시 호환: profiles/naver/<account_key>
    legacy_key = (naver_account_key or "").strip() or "default"
    legacy_profile_dir = PROFILE_ROOT / legacy_key
    if legacy_profile_dir.exists():
        logger.info("naver profile legacy path used path=%s", legacy_profile_dir)
        return legacy_profile_dir

    logger.error("naver profile missing path=%s", profile_dir)
    raise RuntimeError(
        f"로그인 프로필이 없습니다: {profile_dir}\n"
        f"먼저 해당 계정({naver_account_key or 'default'})으로 1회 수동 로그인 프로필을 만들어 주세요."
    )


@contextmanager
def open_naver_context(
    playwright: Playwright,
    *,
    member_required: bool,
    naver_account_key: str = "",
    profile_role: str = "scraper",
    headless: bool = True,
):
    browser = None
    context: BrowserContext | None = None
    
    logger.info(
        "open_naver_context start member_required=%s account_key=%s role=%s headless=%s",
        member_required,
        (naver_account_key or "").strip() or "default",
        profile_role,
        headless,
    )

    if member_required:
        profile_dir = ensure_profile_exists(naver_account_key, profile_role)
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=headless,
            args=["--disable-blink-features=AutomationControlled"],
            viewport={"width": 1400, "height": 900},
            permissions=["clipboard-read", "clipboard-write"],
        )
    else:
        browser = playwright.chromium.launch(
            headless=headless,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = browser.new_context(
            viewport={"width": 1400, "height": 900},
            permissions=["clipboard-read", "clipboard-write"],
        )

    try:
        yield context
    finally:
        if context:
            context.close()
        if browser:
            browser.close()
        logger.info(
            "open_naver_context closed member_required=%s account_key=%s role=%s",
            member_required,
            (naver_account_key or "").strip() or "default",
            profile_role,
        )
