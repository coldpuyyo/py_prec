from __future__ import annotations

from services.naver_profile_registry_service import get_profile
from services.app_logger import get_logger

LOGIN_URL = "https://nid.naver.com/nidlogin.login?mode=form&url=https://www.naver.com/"
logger = get_logger(__name__)

def _is_login_page(page) -> bool:
    url = (page.url or "").lower()
    if "nid.naver.com/nidlogin.login" in url:
        return True
    if page.locator("input#id").count() > 0 and page.locator("input#pw").count() > 0:
        return True
    return False


def _extract_login_hint(page, limit: int = 220) -> str:
    selectors = [
        ".message_area",
        ".error_message",
        ".error_text",
        ".notice",
        ".captcha_desc",
    ]
    for selector in selectors:
        try:
            loc = page.locator(selector)
            if loc.count() > 0:
                text = (loc.first.inner_text() or "").strip()
                if text:
                    return text[:limit]
        except Exception:
            continue

    try:
        text = page.evaluate(
            """() => {
              const t = (document.body && document.body.innerText) ? document.body.innerText : "";
              return t.replace(/\\s+/g, " ").trim();
            }"""
        )
        return (text or "")[:limit]
    except Exception:
        return ""


def is_naver_logged_in(context) -> bool:
    try:
        cookies = context.cookies("https://www.naver.com")
        names = {c.get("name", "") for c in cookies}
        return ("NID_AUT" in names) and ("NID_SES" in names)
    except Exception:
        return False


def _clear_and_type(page, selector: str, value: str, *, delay: int = 60) -> None:
    loc = page.locator(selector).first
    loc.click(timeout=4000)
    try:
        loc.fill("", timeout=2000)
    except Exception:
        pass
    page.keyboard.press("Control+A")
    page.keyboard.press("Delete")
    page.keyboard.type(value, delay=delay)


def _try_submit(page) -> None:
    clicked = False
    for selector in ("button[type='submit']", "button#log\\.login", "#log\\.login"):
        try:
            page.click(selector, timeout=2500)
            clicked = True
            break
        except Exception:
            continue

    if not clicked:
        page.keyboard.press("Enter")


def _login_once(page, login_id: str, login_password: str, mode: str) -> None:
    page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_selector("input#id", timeout=10000)
    page.wait_for_selector("input#pw", timeout=10000)

    if mode == "fill":
        page.fill("input#id", login_id, timeout=5000)
        page.fill("input#pw", login_password, timeout=5000)
    else:
        _clear_and_type(page, "input#id", login_id, delay=80)
        _clear_and_type(page, "input#pw", login_password, delay=80)

    _try_submit(page)
    page.wait_for_timeout(3500)


def ensure_naver_login(context, account_key: str, expected_role: str = "") -> tuple[bool, str]:
    key = str(account_key or "").strip()
    logger.info("ensure_naver_login start account_key=%s expected_role=%s", key or "empty", expected_role)
    
    if not key:
        logger.warning("ensure_naver_login failed empty account_key")
        return False, "account_key가 비어 있습니다."

    if is_naver_logged_in(context):
        logger.info("ensure_naver_login already logged in account_key=%s", key)
        return True, "already_logged_in"

    profile = get_profile(key)
    if not profile:
        logger.warning("ensure_naver_login profile not found account_key=%s", key)
        return False, f"네이버 프로필이 없습니다: {key}"

    if not bool(profile.get("active", True)):
        logger.warning("ensure_naver_login inactive profile account_key=%s", key)
        return False, f"비활성 프로필입니다: {key}"

    role = str(profile.get("role", "")).strip().lower()
    if expected_role and role != expected_role.strip().lower():
        logger.warning(
            "ensure_naver_login role mismatch account_key=%s expected=%s actual=%s",
            key, expected_role, role or "none",
        )
        return False, f"프로필 역할 불일치: expected={expected_role}, actual={role or 'none'}"

    login_id = str(profile.get("login_id", "")).strip()
    login_password = str(profile.get("login_password", "")).strip()
    if not login_id or not login_password:
        logger.warning("ensure_naver_login missing id/pw account_key=%s", key)
        return False, "자동 로그인을 위한 네이버 ID/PW가 저장되지 않았습니다."

    page = context.new_page()
    try:
        for mode in ("fill", "type"):
            logger.info("ensure_naver_login attempt mode=%s account_key=%s", mode, key)
            _login_once(page, login_id, login_password, mode)

            if is_naver_logged_in(context):
                logger.info("ensure_naver_login success mode=%s account_key=%s", mode, key)
                return True, f"login_ok_{mode}"

            if not _is_login_page(page):
                page.wait_for_timeout(1500)
                if is_naver_logged_in(context):
                    logger.info("ensure_naver_login delayed success mode=%s account_key=%s", mode, key)
                    return True, f"login_ok_{mode}_delayed"

        hint = _extract_login_hint(page)
        logger.warning(
            "ensure_naver_login failed still on login page account_key=%s url=%s hint=%s",
            key, page.url, hint[:120],
        )
        return False, f"자동 로그인 후에도 로그인 페이지입니다. 2차 인증/보안문자를 확인하세요. (url={page.url}, hint={hint})"
    except Exception as e:
        logger.exception("ensure_naver_login exception account_key=%s", key)
        return False, f"자동 로그인 처리 중 오류: {e}"
    finally:
        try:
            page.close()
        except Exception:
            pass

