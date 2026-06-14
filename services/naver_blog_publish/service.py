from __future__ import annotations

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from services.app_logger import get_logger
from services.naver_context_service import open_naver_context
from services.naver_login_service import ensure_naver_login
from services.naver_profile_registry_service import get_profile

from .browser import (
    _build_write_urls,
    _collect_scopes,
    _detect_result_url,
    _dismiss_popups,
    _extract_blog_id_from_page,
    _has_editor_surface,
    _is_login_page,
    _open_write_via_blog_home,
    _publish_flow,
)
from .constants import DEFAULT_BODY_FONT_SIZE, DEFAULT_SUBTITLE_FONT_SIZE, DEFAULT_SUBTITLE_QUOTE_STYLE
from .debug import _debug_body_state, _debug_editor_state, _extract_body_text_snippet
from .editor import _fill_title, _normalize_delay_range, _publish_structured_body
from .formatting import _normalize_font_size, _normalize_quote_style
from .schedule import _publish_scheduled_flow

logger = get_logger(__name__)


def publish_naver_blog_post(
    title: str,
    content: str,
    publisher_profile_key: str,
    blog_id: str = "",
    publish_mode: str = "now",
    scheduled_at: str = "",
    include_random_image: bool = False,
    middle_image_count: int = 1,
    bottom_image_count: int = 1,
    trace_id: str = "",
    typing_delay_min: int = 30,
    typing_delay_max: int = 85,
    conclusion_paragraph_count: int = 1,
    body_font_size: str = DEFAULT_BODY_FONT_SIZE,
    subtitle_font_size: str = DEFAULT_SUBTITLE_FONT_SIZE,
    subtitle_quote_style: int = DEFAULT_SUBTITLE_QUOTE_STYLE,
    bottom_image_link: str = "",
    bottom_first_image_link: str = "",
) -> dict:
    trace = (trace_id or "").strip() or "-"
    title = (title or "").strip()
    content = (content or "").strip()
    profile_key = (publisher_profile_key or "").strip()
    manual_blog_id = (blog_id or "").strip()
    publish_mode = (publish_mode or "now").strip().lower()
    scheduled_at = (scheduled_at or "").strip()
    bottom_image_link = (bottom_image_link or "").strip()
    bottom_first_image_link = (bottom_first_image_link or "").strip()
    is_scheduled_publish = publish_mode == "scheduled"
    use_random_image = bool(include_random_image)
    typing_delay_min, typing_delay_max = _normalize_delay_range(typing_delay_min, typing_delay_max, 30, 85)
    body_font_size = _normalize_font_size(body_font_size, DEFAULT_BODY_FONT_SIZE)
    subtitle_font_size = _normalize_font_size(subtitle_font_size, DEFAULT_SUBTITLE_FONT_SIZE)
    subtitle_quote_style = _normalize_quote_style(subtitle_quote_style)

    logger.info(
        "[trace_id=%s] publish_naver_blog_post start profile_key=%s blog_id=%s publish_mode=%s scheduled_at=%s include_random_image=%s has_hyper_image_link=%s has_bottom_first_image_link=%s title_len=%s content_len=%s body_size=%s subtitle_size=%s subtitle_quote=%s",
        trace,
        profile_key,
        manual_blog_id,
        publish_mode,
        scheduled_at,
        use_random_image,
        bool(bottom_image_link),
        bool(bottom_first_image_link),
        len(title),
        len(content),
        body_font_size,
        subtitle_font_size,
        subtitle_quote_style,
    )

    if not title:
        logger.warning("[trace_id=%s] publish failed: empty title", trace)
        return {"ok": False, "message": "발행 제목이 비어 있습니다."}
    if not content:
        logger.warning("[trace_id=%s] publish failed: empty content", trace)
        return {"ok": False, "message": "발행 본문이 비어 있습니다."}
    if not profile_key:
        logger.warning("[trace_id=%s] publish failed: empty publisher_profile_key", trace)
        return {"ok": False, "message": "발행 프로필 키가 비어 있습니다."}
    if publish_mode not in {"now", "scheduled"}:
        logger.warning("[trace_id=%s] publish failed: invalid publish_mode=%s", trace, publish_mode)
        return {"ok": False, "message": "발행 방식 값이 올바르지 않습니다."}
    if is_scheduled_publish and not scheduled_at:
        logger.warning("[trace_id=%s] publish failed: empty scheduled_at", trace)
        return {"ok": False, "message": "예약발행 시간이 비어 있습니다."}

    try:
        with sync_playwright() as playwright:
            with open_naver_context(
                playwright,
                member_required=True,
                naver_account_key=profile_key,
                profile_role="publisher",
                headless=False,
            ) as context:
                logger.info("[trace_id=%s] publish context opened profile_key=%s", trace, profile_key)
                
                login_ok, login_reason = ensure_naver_login(context, profile_key, expected_role="publisher")
                logger.info("[trace_id=%s] publish login result ok=%s reason=%s", trace, login_ok, login_reason)
                if not login_ok:
                    logger.warning("[trace_id=%s] publish login failed reason=%s", trace, login_reason)
                    return {"ok": False, "message": f"발행 계정 로그인 실패: {login_reason}"}

                page = context.new_page()

                resolved_blog_id = manual_blog_id
                if not resolved_blog_id:
                    try:
                        profile = get_profile(profile_key)
                        if profile and str(profile.get("role", "")).lower() == "publisher":
                            resolved_blog_id = (str(profile.get("blog_id", "")) or "").strip()
                    except Exception:
                        resolved_blog_id = ""

                try:
                    page.goto("https://blog.naver.com/", wait_until="domcontentloaded", timeout=60000)
                    page.wait_for_timeout(1300)
                    if not resolved_blog_id:
                        resolved_blog_id = _extract_blog_id_from_page(page)
                except Exception:
                    pass
                
                logger.info(
                    "[trace_id=%s] publish resolved_blog_id=%s manual_blog_id=%s",
                    trace,
                    resolved_blog_id,
                    manual_blog_id,
                )

                opened = False
                tried_urls: list[str] = []
                for write_url in _build_write_urls(resolved_blog_id):
                    tried_urls.append(write_url)
                    try:
                        page.goto(write_url, wait_until="domcontentloaded", timeout=60000)
                        page.wait_for_timeout(2600)
                        logger.info("[trace_id=%s] publish write page opened url=%s", trace, write_url)

                        if _is_login_page(page):
                            relog_ok, relog_reason = ensure_naver_login(
                                context,
                                profile_key,
                                expected_role="publisher",
                            )
                            logger.info("[trace_id=%s] publish relogin result ok=%s reason=%s", trace, relog_ok, relog_reason)
                            if not relog_ok:
                                return {"ok": False, "message": f"발행 계정 로그인 재시도 실패: {relog_reason}"}
                            page.goto(write_url, wait_until="domcontentloaded", timeout=60000)
                            page.wait_for_timeout(2200)

                        scopes = _collect_scopes(page)
                        if not _has_editor_surface(scopes):
                            continue

                        opened = True
                        break
                    except Exception:
                        continue

                if not opened:
                    opened, page = _open_write_via_blog_home(context, page, resolved_blog_id)
                    if opened and resolved_blog_id:
                        tried_urls.append(f"https://blog.naver.com/{resolved_blog_id}?Redirect=Write&")
                        logger.info("[trace_id=%s] publish write page opened url=%s", trace, tried_urls[-1])
                logger.info("[trace_id=%s] publish editor opened=%s tried_urls_count=%s", trace, opened, len(tried_urls))

                if not opened:
                    logger.warning("[trace_id=%s] publish editor not opened tried_urls=%s", trace, tried_urls)
                    if _is_login_page(page):
                        return {
                            "ok": False,
                            "message": "블로그 글쓰기 화면을 열지 못했습니다. 로그인 페이지로 이동했습니다. 2차 인증/보안 설정을 확인하세요.",
                        }
                    hint = _extract_body_text_snippet(page)
                    return {
                        "ok": False,
                        "message": (
                            "블로그 글쓰기 에디터를 열지 못했습니다. 계정의 블로그 개설/권한/블로그ID를 확인하세요. "
                            f"(blog_id={resolved_blog_id or 'none'}, tried={tried_urls}, hint={hint})"
                        ),
                    }

                if _is_login_page(page):
                    logger.warning("[trace_id=%s] publish redirected to login page after editor open", trace)
                    return {
                        "ok": False,
                        "message": "발행 도중 로그인 페이지로 이동했습니다. publisher 프로필 로그인 상태를 확인하세요.",
                    }

                scopes = _collect_scopes(page)
                _dismiss_popups(scopes)

                logger.info("[trace_id=%s] publish title fill start", trace)

                if not _fill_title(scopes, title, min_delay=typing_delay_min, max_delay=typing_delay_max):
                    logger.warning("[trace_id=%s] publish title fill failed state=%s", trace, _debug_editor_state(page))
                    return {
                        "ok": False,
                        "message": f"글쓰기 화면에서 제목 입력 위치를 찾지 못했습니다. ({_debug_editor_state(page)})",
                    }

                logger.info("[trace_id=%s] publish body fill start random_image=%s", trace, use_random_image)

                body_ok, body_message, scopes = _publish_structured_body(
                    page,
                    scopes,
                    content,
                    use_random_image=use_random_image,
                    middle_image_count=middle_image_count,
                    bottom_image_count=bottom_image_count,
                    bottom_image_link=bottom_image_link,
                    bottom_first_image_link=bottom_first_image_link,
                    trace=trace,
                    typing_delay_min=typing_delay_min,
                    typing_delay_max=typing_delay_max,
                    conclusion_paragraph_count=conclusion_paragraph_count,
                    body_font_size=body_font_size,
                    subtitle_font_size=subtitle_font_size,
                    subtitle_quote_style=subtitle_quote_style,
                )
                if not body_ok:
                    logger.warning(
                        "[trace_id=%s] publish structured body failed message=%s state=%s body_scopes=%s",
                        trace,
                        body_message,
                        _debug_editor_state(page),
                        _debug_body_state(scopes),
                    )
                    return {
                        "ok": False,
                        "message": body_message,
                    }
                
                if is_scheduled_publish:
                    schedule_ok, schedule_message, scheduled_display = _publish_scheduled_flow(
                        page,
                        scopes,
                        scheduled_at,
                        trace,
                    )
                    if not schedule_ok:
                        logger.warning("[trace_id=%s] scheduled publish flow failed message=%s", trace, schedule_message)
                        return {"ok": False, "message": schedule_message}

                    logger.info("[trace_id=%s] scheduled publish success scheduled_at=%s", trace, scheduled_display)
                    return {
                        "ok": True,
                        "message": "블로그 예약발행이 완료되었습니다.",
                        "publish_mode": "scheduled",
                        "scheduled_at": scheduled_display or scheduled_at,
                    }

                if not _publish_flow(page, scopes):
                    logger.warning("[trace_id=%s] publish flow failed", trace)
                    return {"ok": False, "message": "발행 버튼 클릭에 실패했습니다. 발행 팝업 상태를 확인하세요."}

                logger.info("[trace_id=%s] publish detect url start", trace)
                published_url = _detect_result_url(page)
                if not published_url:
                    logger.warning("[trace_id=%s] publish result url missing state=%s", trace, _debug_editor_state(page))
                    return {
                        "ok": False,
                        "message": (
                            "발행 버튼 클릭 후 결과 URL을 확인하지 못했습니다. "
                            + f"({_debug_editor_state(page)})"
                        ),
                    }
                logger.info("[trace_id=%s] publish success url=%s", trace, published_url)
                return {"ok": True, "message": "블로그 발행이 완료되었습니다.", "url": published_url}

    except PlaywrightTimeoutError:
        logger.exception("[trace_id=%s] publish timeout", trace)
        return {"ok": False, "message": "블로그 발행 중 타임아웃이 발생했습니다."}
    except PlaywrightError as exc:
        logger.exception("[trace_id=%s] publish playwright error", trace)
        return {"ok": False, "message": f"Playwright 오류: {str(exc)}"}
    except Exception as exc:
        logger.exception("[trace_id=%s] publish unexpected error", trace)
        return {"ok": False, "message": str(exc)}
