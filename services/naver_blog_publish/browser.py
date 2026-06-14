from __future__ import annotations

import re
import time
from typing import Any

from .constants import WRITE_URLS


def _is_login_page(page) -> bool:
    url = (page.url or "").lower()
    if "nid.naver.com/nidlogin.login" in url:
        return True
    if page.locator("input#id").count() > 0 and page.locator("input#pw").count() > 0:
        return True
    return False


def _collect_scopes(page) -> list[Any]:
    scopes: list[Any] = []
    main_frame = page.frame(name="mainFrame")
    if main_frame:
        scopes.append(main_frame)

    scopes.append(page)

    for frame in page.frames:
        if frame not in scopes:
            scopes.append(frame)
    return scopes


def _try_click_common_buttons(scopes: list[Any], labels: list[str], timeout_ms: int = 900) -> bool:
    for scope in scopes:
        for label in labels:
            try:
                btn = scope.get_by_role("button", name=label)
                if btn.count() > 0:
                    btn.first.click(timeout=timeout_ms)
                    return True
            except Exception:
                continue
    return False


def _dismiss_popups(scopes: list[Any]) -> None:
    _try_click_common_buttons(scopes, ["닫기", "나중에", "확인"], timeout_ms=700)

    selector_candidates = [
        "button[aria-label='닫기']",
        "button[title='닫기']",
        "button[class*='close']",
        "[role='dialog'] button:has-text('닫기')",
    ]
    for scope in scopes:
        for selector in selector_candidates:
            try:
                loc = scope.locator(selector)
                if loc.count() > 0:
                    loc.first.click(timeout=600)
                    return
            except Exception:
                continue


def _extract_blog_id_from_url(url: str) -> str:
    text = (url or "").strip()
    if not text:
        return ""

    match = re.search(r"[?&]blogId=([A-Za-z0-9._-]+)", text)
    if match:
        return match.group(1)

    match = re.search(r"blog\.naver\.com/([A-Za-z0-9._-]+)(?:/|$)", text)
    if match:
        candidate = match.group(1)
        if candidate.lower() not in {"postwriteform.naver", "mylog"}:
            return candidate
    return ""


def _extract_blog_id_from_page(page) -> str:
    current = _extract_blog_id_from_url(page.url or "")
    if current:
        return current

    try:
        hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.getAttribute('href') || '')")
        for href in hrefs:
            blog_id = _extract_blog_id_from_url(href or "")
            if blog_id:
                return blog_id
    except Exception:
        pass

    try:
        html = page.content()
        match = re.search(r"blogId[\"']?\s*[:=]\s*[\"']([A-Za-z0-9._-]+)[\"']", html)
        if match:
            return match.group(1)
    except Exception:
        pass

    return ""


def _build_write_urls(blog_id: str = "") -> list[str]:
    urls: list[str] = []
    if blog_id:
        urls.extend([
            f"https://blog.naver.com/PostWriteForm.naver?blogId={blog_id}&Redirect=Write&redirect=Write",
            f"https://blog.naver.com/PostWriteForm.naver?blogId={blog_id}&Redirect=Write&redirect=Write&widgetTypeCall=true&noTrackingCode=true",
            f"https://blog.naver.com/{blog_id}?Redirect=Write&",
        ])
    urls.extend(WRITE_URLS)
    return urls


def _has_editor_surface(scopes: list[Any]) -> bool:
    selectors = [
        "[data-a11y-title='제목']",
        "[data-a11y-title='제목'] [contenteditable='true']",
        "[data-a11y-title='본문']",
        "[data-a11y-title='본문'] [contenteditable='true']",
    ]

    for scope in scopes:
        try:
            for selector in selectors:
                if scope.locator(selector).count() > 0:
                    return True
        except Exception:
            continue

    for scope in scopes:
        try:
            publish_btn = scope.get_by_role("button", name="발행")
            if publish_btn.count() > 0:
                return True
        except Exception:
            continue
    return False


def _open_write_via_blog_home(context, page, blog_id: str) -> tuple[bool, Any]:
    if not blog_id:
        return False, page

    try:
        page.goto(f"https://blog.naver.com/{blog_id}?Redirect=Write&", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(2200)
    except Exception:
        return False, page

    scopes = _collect_scopes(page)
    if _has_editor_surface(scopes):
        return True, page

    try:
        targets = [
            page.get_by_role("link", name="글쓰기"),
            page.get_by_role("button", name="글쓰기"),
            page.get_by_text("글쓰기", exact=False),
        ]
        for target in targets:
            if target.count() == 0:
                continue

            before_pages = list(context.pages)
            try:
                target.first.click(timeout=2500)
            except Exception:
                continue

            page.wait_for_timeout(2500)
            if len(context.pages) > len(before_pages):
                page = context.pages[-1]

            scopes = _collect_scopes(page)
            if _has_editor_surface(scopes):
                return True, page
    except Exception:
        return False, page

    return False, page


def _click_first_visible(scopes: list[Any], selectors: list[str], *, timeout_ms: int = 1200) -> bool:
    for scope in scopes:
        for selector in selectors:
            try:
                loc = scope.locator(selector)
                count = loc.count()
            except Exception:
                continue

            if count == 0:
                continue

            for idx in range(min(count, 40)):
                try:
                    target = loc.nth(idx)
                except Exception:
                    continue

                try:
                    if not target.is_visible():
                        continue
                except Exception:
                    continue

                try:
                    target.scroll_into_view_if_needed(timeout=500)
                except Exception:
                    pass

                try:
                    target.click(timeout=timeout_ms)
                    return True
                except Exception:
                    try:
                        target.click(timeout=timeout_ms, force=True)
                        return True
                    except Exception:
                        continue
    return False


def _is_write_page_url(url: str) -> bool:
    text = (url or "").lower()
    return (
        "postwriteform.naver" in text
        or "redirect=write" in text
        or "/mylog/postwriteform.naver" in text
    )


def _click_publish_once(scopes: list[Any], timeout_ms: int = 2400) -> bool:
    direct_selectors = [
        "button[data-testid='seOnePublishBtn']",
        "button[data-click-area*='publish']",
        "[data-testid='seOnePublishBtn']",
        "button.confirm_btn__WEaBq",
        "[role='button'][data-click-area*='publish']",
    ]
    for scope in scopes:
        for selector in direct_selectors:
            try:
                loc = scope.locator(selector)
                if loc.count() == 0:
                    continue
                loc.first.click(timeout=timeout_ms)
                return True
            except Exception:
                continue

    if _try_click_common_buttons(scopes, ["발행", "등록", "확인"], timeout_ms=timeout_ms):
        return True

    fallback_selectors = [
        "button:has-text('발행')",
        "a:has-text('발행')",
        "[role='button']:has-text('발행')",
        "button:has-text('등록')",
        "button:has-text('확인')",
    ]
    for scope in scopes:
        for selector in fallback_selectors:
            try:
                loc = scope.locator(selector)
                if loc.count() == 0:
                    continue
                loc.first.click(timeout=timeout_ms)
                return True
            except Exception:
                continue
    return False


def _publish_flow(page, scopes: list[Any]) -> bool:
    for _ in range(4):
        _dismiss_popups(scopes)
        if not _click_publish_once(scopes, timeout_ms=2600):
            return False

        deadline = time.monotonic() + 6.5
        while time.monotonic() < deadline:
            if not _is_write_page_url(page.url or ""):
                return True
            page.wait_for_timeout(300)

        scopes = _collect_scopes(page)

    return not _is_write_page_url(page.url or "")


def _detect_result_url(page) -> str:
    deadline = time.monotonic() + 12.0
    while time.monotonic() < deadline:
        url = page.url or ""
        if _is_login_page(page):
            return ""
        if "blog.naver.com" in url.lower() and not _is_write_page_url(url):
            return url
        page.wait_for_timeout(350)
    return ""
