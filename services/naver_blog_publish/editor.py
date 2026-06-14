from __future__ import annotations

import random
from typing import Any

from services.app_logger import get_logger

from .browser import _collect_scopes
from .constants import (
    DEFAULT_BODY_FONT_SIZE,
    DEFAULT_SUBTITLE_FONT_SIZE,
    DEFAULT_SUBTITLE_QUOTE_STYLE,
    HUMAN_TYPE_MODE,
)
from .content_parser import _split_publish_parts, _split_subtitle_block
from .debug import _debug_body_state, _debug_editor_state
from .formatting import (
    _apply_font_size_to_current_paragraph,
    _apply_quote_style_to_current_paragraph,
    _exit_quote_block_for_body,
    _focus_current_editor_selection,
    _last_quote_block_contains_text,
    _normalize_font_size,
    _normalize_quote_style,
    _place_caret_after_last_quote_block,
    _selection_plain_text_state,
    _selection_quote_state,
)
from .images import (
    _insert_hyper_link_image,
    _insert_random_images,
    _try_insert_random_bottom_image,
    _try_insert_random_middle_image,
    _try_insert_random_top_image,
)

logger = get_logger(__name__)


def _set_plain_text(target, text: str) -> bool:
    try:
        target.evaluate(
            """(el, value) => {
                const v = String(value ?? "");
                const tag = (el.tagName || "").toLowerCase();
                if (tag === "input" || tag === "textarea") {
                    el.value = v;
                    el.dispatchEvent(new Event("input", { bubbles: true }));
                    el.dispatchEvent(new Event("change", { bubbles: true }));
                    return true;
                }
                if (el.isContentEditable) {
                    el.innerHTML = "";
                    const lines = v.split("\\n");
                    for (const line of lines) {
                        const p = document.createElement("p");
                        p.textContent = line.length ? line : "\\u200b";
                        el.appendChild(p);
                    }
                    el.dispatchEvent(new Event("input", { bubbles: true }));
                    el.dispatchEvent(new Event("change", { bubbles: true }));
                    return true;
                }
                return false;
            }""",
            text,
        )
        return True
    except Exception:
        return False


def _human_type(page, text: str, min_delay: int = 35, max_delay: int = 95) -> None:
    text = str(text or "")
    for ch in text:
        if ch == "\n":
            page.keyboard.press("Enter")
        else:
            page.keyboard.type(ch, delay=random.randint(min_delay, max_delay))

        if random.random() < 0.03:
            page.wait_for_timeout(random.randint(120, 280))


def _normalize_delay_range(min_delay: int, max_delay: int, default_min: int = 30, default_max: int = 85) -> tuple[int, int]:
    try:
        mn = int(min_delay)
    except Exception:
        mn = default_min

    try:
        mx = int(max_delay)
    except Exception:
        mx = default_max

    mn = max(0, min(500, mn))
    mx = max(0, min(500, mx))

    if mn > mx:
        mn, mx = mx, mn

    return mn, mx


def _human_fill(scope, target, text: str, *, min_delay: int, max_delay: int) -> bool:
    owner_page = scope.page if hasattr(scope, "page") else scope
    try:
        target.click(timeout=2000)
    except Exception:
        return False

    _set_plain_text(target, "")

    _human_type(owner_page, text, min_delay=min_delay, max_delay=max_delay)
    return True


def _fill_title(scopes: list[Any], title: str, *, min_delay: int = 45, max_delay: int = 110) -> bool:
    selectors = [
        "[data-a11y-title='제목']",
        "[data-a11y-title='제목'] [contenteditable='true']",
    ]

    for scope in scopes:
        for selector in selectors:
            try:
                loc = scope.locator(selector)
                if loc.count() == 0:
                    continue

                if _human_fill(scope, loc.first, title, min_delay=min_delay, max_delay=max_delay):
                    return True
            except Exception:
                continue

    for scope in scopes:
        try:
            label = scope.get_by_text("제목", exact=False)
            if label.count() > 0:
                label.first.click(timeout=1000)
                owner_page = scope.page if hasattr(scope, "page") else scope
                _human_type(owner_page, title, min_delay, max_delay)
                return True
        except Exception:
            continue

    return False


def _is_title_like(target) -> bool:
    try:
        marker = " ".join([
            target.get_attribute("data-placeholder") or "",
            target.get_attribute("aria-label") or "",
            target.get_attribute("placeholder") or "",
            target.get_attribute("class") or "",
            target.get_attribute("id") or "",
        ]).lower()
    except Exception:
        return False

    return (
        "title" in marker
        or "제목" in marker
        or "documenttitle" in marker
        or "toolbar" in marker
        or "caption" in marker
        or "floating" in marker
    )


def _body_editable_selectors() -> list[str]:
    return [
        "[data-a11y-title='본문'] [contenteditable='true']",
        "[data-a11y-title='본문'] [role='textbox']",
        "[data-a11y-title='본문']",
        "article .se-component.se-text [contenteditable='true']",
        "div.se-component.se-text [contenteditable='true']",
        "p.se-text-paragraph [contenteditable='true']",
    ]


def _fill_body(scopes: list[Any], content: str, *, min_delay: int = 30, max_delay: int = 85) -> bool:
    selectors = _body_editable_selectors()

    def _owner_page(scope):
        return scope.page if hasattr(scope, "page") else scope

    for scope in scopes:
        for selector in selectors:
            try:
                loc = scope.locator(selector)
                count = loc.count()
            except Exception:
                continue

            if count == 0:
                continue

            for idx in range(min(count, 30)):
                try:
                    target = loc.nth(idx)
                except Exception:
                    continue

                if _is_title_like(target):
                    continue

                try:
                    box = target.bounding_box()
                    if box and box.get("y", 99999) < 120 and box.get("height", 0) < 120:
                        continue
                except Exception:
                    pass

                try:
                    target.click(timeout=1600)
                except Exception:
                    continue

                owner_page = _owner_page(scope)

                try:
                    _set_plain_text(target, "")
                except Exception:
                    pass

                _human_type(owner_page, content, min_delay, max_delay)
                return True

    return False


def _focus_body_for_append(scopes: list[Any]):
    selectors = _body_editable_selectors()
    best = None  # tuple(score, scope, target)

    for scope in scopes:
        for selector in selectors:
            try:
                loc = scope.locator(selector)
                count = loc.count()
            except Exception:
                continue

            if count == 0:
                continue

            for idx in range(min(count, 30)):
                try:
                    target = loc.nth(idx)
                except Exception:
                    continue

                if _is_title_like(target):
                    continue

                # 1) 이미지/캡션 계열 배제
                try:
                    is_image_related = bool(
                        target.evaluate(
                            "el => !!el.closest('.se-component-image, .se-image, .se-caption, [class*=caption], [class*=image]')"
                        )
                    )
                    if is_image_related:
                        continue
                except Exception:
                    pass

                # 2) 텍스트 컴포넌트 내부인지 강제 확인
                try:
                    is_text_component = bool(
                        target.evaluate(
                            "el => { const c = el.closest('.se-component'); return !!(c && c.classList && c.classList.contains('se-text')); }"
                        )
                    )
                    if not is_text_component:
                        continue
                except Exception:
                    continue

                try:
                    box = target.bounding_box()
                    if not box:
                        continue
                    if box.get("width", 0) < 20 or box.get("height", 0) < 8:
                        continue
                    score = float(box.get("y", 0)) + float(box.get("height", 0))
                    if best is None or score > best[0]:
                        best = (score, scope, target)
                except Exception:
                    continue

    if best:
        _, scope, target = best
        try:
            target.click(timeout=1800)
        except Exception:
            return None

        owner_page = scope.page if hasattr(scope, "page") else scope
        try:
            target.evaluate(
                """(el) => {
                    el.focus();
                    const sel = window.getSelection();
                    if (!sel) return;
                    const range = document.createRange();
                    range.selectNodeContents(el);
                    range.collapse(false);
                    sel.removeAllRanges();
                    sel.addRange(range);
                }"""
            )
        except Exception:
            pass
        return owner_page

    return None


def _force_caret_to_tail(scopes: list[Any]) -> bool:
    js = r"""
    () => {
      const root = document.querySelector("article") || document;

      // 텍스트/인용구 문단을 대상으로 마지막 문단 찾기
      const paras = Array.from(
        root.querySelectorAll(".se-component p.se-text-paragraph, p.se-text-paragraph")
      ).filter((p) => {
        return !p.closest(".se-component-image, .se-image, .se-caption, [class*=caption], [class*=image]");
      });
      if (!paras.length) return false;

      let para = null;
      // 비어있지 않은 마지막 문단 우선
      for (let i = paras.length - 1; i >= 0; i--) {
        const t = (paras[i].innerText || paras[i].textContent || "").trim();
        if (t.length) { para = paras[i]; break; }
      }
      if (!para) para = paras[paras.length - 1];

      // 실제 포커스 대상(편집 host)
      const host =
        para.closest("[contenteditable='true'], [role='textbox']") ||
        para.querySelector("[contenteditable='true'], [role='textbox']") ||
        para;

      if (!host) return false;
      host.focus();

      const sel = window.getSelection();
      if (!sel) return false;

      const range = document.createRange();

      // 문단 내 마지막 텍스트 노드 끝으로 caret 이동
      const walker = document.createTreeWalker(para, NodeFilter.SHOW_TEXT);
      let lastText = null;
      while (walker.nextNode()) {
        const n = walker.currentNode;
        if ((n.nodeValue || "").length > 0) lastText = n;
      }

      if (lastText) {
        range.setStart(lastText, (lastText.nodeValue || "").length);
        range.collapse(true);
      } else {
        range.selectNodeContents(para);
        range.collapse(false);
      }

      sel.removeAllRanges();
      sel.addRange(range);
      return true;
    }
    """
    for scope in scopes:
        try:
            ok = bool(scope.evaluate(js))
            if ok:
                return True
        except Exception:
            continue
    return False


def _owner_page_from_scopes(scopes: list[Any]):
    for scope in scopes:
        try:
            return scope.page if hasattr(scope, "page") else scope
        except Exception:
            continue
    return None


def _append_body(
    scopes: list[Any],
    content: str,
    *,
    force_refocus: bool = False,
    leading_enters: int = 0,
    min_delay: int = 30,
    max_delay: int = 85,
    font_size: str = "",
    use_current_caret: bool = False,
) -> bool:
    text = str(content or "").strip()
    if not text:
        return True

    page = _owner_page_from_scopes(scopes)
    if not page:
        return False

    if use_current_caret:
        if _selection_quote_state(_collect_scopes(page)) is True:
            if not _exit_quote_block_for_body(page, _collect_scopes(page)):
                logger.warning("body append blocked: current caret is still inside quote text_len=%s", len(text))
                return False
        if not _selection_plain_text_state(_collect_scopes(page)):
            logger.warning("body append blocked: current caret is not a plain text paragraph text_len=%s", len(text))
            return False
    elif not force_refocus:
        if not _force_caret_to_tail(scopes):
            page = _focus_body_for_append(scopes)
            if not page:
                return False
            _force_caret_to_tail(scopes)
    else:
        page = _focus_body_for_append(scopes)
        if not page:
            return False
        _force_caret_to_tail(scopes)

    for _ in range(max(0, int(leading_enters or 0))):
        try:
            page.keyboard.press("Enter")
        except Exception:
            pass

    if use_current_caret and not _selection_plain_text_state(_collect_scopes(page)):
        logger.warning("body append blocked after leading enters: caret is not plain text text_len=%s", len(text))
        return False

    quote_probe = next((line.strip() for line in text.splitlines() if line.strip()), text[:120].strip())

    if font_size:
        if not _apply_font_size_to_current_paragraph(page, _collect_scopes(page), font_size):
            logger.warning("body font size apply failed font_size=%s text_len=%s", font_size, len(text))
            return False
        if not _focus_current_editor_selection(_collect_scopes(page)):
            logger.warning("body editor focus restore failed font_size=%s text_len=%s", font_size, len(text))
            return False

    _human_type(page, text, min_delay, max_delay)
    if _selection_quote_state(_collect_scopes(page)) is True:
        logger.warning("body append failed: typed body is still inside quote text_len=%s", len(text))
        return False
    if quote_probe and _last_quote_block_contains_text(_collect_scopes(page), quote_probe):
        logger.warning("body append failed: typed body text found inside last quote text_len=%s", len(text))
        return False
    return True


def _append_quoted_subtitle(
    scopes: list[Any],
    content: str,
    *,
    force_refocus: bool = False,
    leading_enters: int = 0,
    min_delay: int = 30,
    max_delay: int = 85,
    font_size: str = "",
    quote_style: int = DEFAULT_SUBTITLE_QUOTE_STYLE,
    use_current_caret: bool = False,
) -> bool:
    text = str(content or "").strip()
    if not text:
        return True

    page = _owner_page_from_scopes(scopes)
    if not page:
        return False

    if use_current_caret:
        pass
    elif not force_refocus:
        if not _force_caret_to_tail(scopes):
            page = _focus_body_for_append(scopes)
            if not page:
                return False
            _force_caret_to_tail(scopes)
    else:
        page = _focus_body_for_append(scopes)
        if not page:
            return False
        _force_caret_to_tail(scopes)

    for _ in range(max(0, int(leading_enters or 0))):
        try:
            page.keyboard.press("Enter")
        except Exception:
            pass

    if not _apply_quote_style_to_current_paragraph(page, _collect_scopes(page), quote_style):
        logger.warning("quote style pre-apply failed quote_style=%s text_len=%s", quote_style, len(text))
        return False

    if font_size:
        if not _apply_font_size_to_current_paragraph(page, _collect_scopes(page), font_size):
            logger.warning("subtitle font size apply failed quote_style=%s font_size=%s text_len=%s", quote_style, font_size, len(text))
            return False
        if not _focus_current_editor_selection(_collect_scopes(page)):
            logger.warning("subtitle editor focus restore failed quote_style=%s font_size=%s text_len=%s", quote_style, font_size, len(text))
            return False

    _human_type(page, text, min_delay, max_delay)

    fresh_scopes = _collect_scopes(page)
    if _selection_quote_state(fresh_scopes) is not True and not _last_quote_block_contains_text(fresh_scopes, text):
        logger.warning("quoted subtitle did not remain inside quote quote_style=%s text_len=%s", quote_style, len(text))
        return False

    if not _place_caret_after_last_quote_block(page, _collect_scopes(page)):
        logger.warning("quote block caret placement failed quote_style=%s text_len=%s", quote_style, len(text))
        return False

    return True


def _press_enters(page, count: int) -> None:
    for _ in range(max(0, int(count or 0))):
        page.keyboard.press("Enter")
        page.wait_for_timeout(120)


def _publish_structured_body(
    page,
    scopes: list[Any],
    content: str,
    *,
    use_random_image: bool,
    middle_image_count: int,
    bottom_image_count: int,
    bottom_image_link: str,
    bottom_first_image_link: str,
    trace: str,
    typing_delay_min: int,
    typing_delay_max: int,
    conclusion_paragraph_count: int,
    body_font_size: str,
    subtitle_font_size: str,
    subtitle_quote_style: int,
) -> tuple[bool, str, list[Any]]:
    body_size = _normalize_font_size(body_font_size, DEFAULT_BODY_FONT_SIZE)
    subtitle_size = _normalize_font_size(subtitle_font_size, DEFAULT_SUBTITLE_FONT_SIZE)
    quote_style = _normalize_quote_style(subtitle_quote_style)

    intro_part, subtitle_sections, closing_part, hashtag_part = _split_publish_parts(
        content,
        conclusion_paragraph_count=conclusion_paragraph_count,
    )

    need_refocus = True
    editor_has_content = False
    wrote_text = False
    caret_ready_for_next = False

    def append_text_part(
        text: str,
        *,
        label: str,
        leading_enters: int,
        font_size: str,
        use_current_caret: bool = False,
    ) -> tuple[bool, str]:
        nonlocal scopes, need_refocus, editor_has_content, wrote_text

        if not str(text or "").strip():
            return True, ""

        if not _append_body(
            scopes,
            text,
            force_refocus=need_refocus,
            leading_enters=leading_enters,
            min_delay=typing_delay_min,
            max_delay=typing_delay_max,
            font_size=font_size,
            use_current_caret=use_current_caret,
        ):
            return False, f"{label} 입력이 실패했습니다."

        scopes = _collect_scopes(page)
        need_refocus = False
        editor_has_content = True
        wrote_text = True
        return True, ""

    def append_quoted_subtitle_part(
        text: str,
        *,
        label: str,
        leading_enters: int,
        font_size: str,
        quote_style: int,
        use_current_caret: bool = False,
    ) -> tuple[bool, str]:
        nonlocal scopes, need_refocus, editor_has_content, wrote_text

        if not str(text or "").strip():
            return True, ""

        if not _append_quoted_subtitle(
            scopes,
            text,
            force_refocus=need_refocus,
            leading_enters=leading_enters,
            min_delay=typing_delay_min,
            max_delay=typing_delay_max,
            font_size=font_size,
            quote_style=quote_style,
            use_current_caret=use_current_caret,
        ):
            return False, f"{label} 인용구 입력이 실패했습니다."

        scopes = _collect_scopes(page)
        need_refocus = False
        editor_has_content = True
        wrote_text = True
        return True, ""

    if use_random_image:
        # TOP 이미지를 본문 작성 전에 넣기 위해 본문 영역 먼저 포커스
        focus_page = _focus_body_for_append(scopes)
        if not focus_page:
            logger.warning(
                "[trace_id=%s] publish body focus before top image failed state=%s body_scopes=%s",
                trace,
                _debug_editor_state(page),
                _debug_body_state(scopes),
            )
            return (
                False,
                "TOP 이미지 삽입 전 본문 포커스가 실패했습니다. "
                + f"({_debug_editor_state(page)}, body_scopes={_debug_body_state(scopes)})",
                scopes,
            )
        scopes = _collect_scopes(page)

        ok, msg, scopes = _insert_random_images(
            page,
            scopes,
            count=1,
            insert_fn=_try_insert_random_top_image,
            trace=trace,
            stage="top",
        )
        if not ok:
            logger.warning("[trace_id=%s] publish top image insert failed message=%s", trace, msg)
            return False, f"이미지 삽입 실패(top): {msg}", scopes

        need_refocus = True
        editor_has_content = True

    if intro_part:
        leading = 2 if use_random_image else 0
        ok, msg = append_text_part(
            intro_part,
            label="첫 본문 구간",
            leading_enters=leading,
            font_size=body_size,
        )
        if not ok:
            logger.warning(
                "[trace_id=%s] publish intro body append failed state=%s body_scopes=%s",
                trace,
                _debug_editor_state(page),
                _debug_body_state(scopes),
            )
            return False, msg + f" ({_debug_editor_state(page)}, body_scopes={_debug_body_state(scopes)})", scopes

    for sec_idx, sec_text in enumerate(subtitle_sections, start=1):
        subtitle_line, body_text = _split_subtitle_block(sec_text)

        if subtitle_line:
            if not editor_has_content:
                subtitle_leading_enters = 0
            elif use_random_image and bool((intro_part or "").strip()) and sec_idx == 1:
                subtitle_leading_enters = 5
            else:
                subtitle_leading_enters = 2

            subtitle_use_current_caret = caret_ready_for_next
            if subtitle_use_current_caret:
                subtitle_leading_enters = 0
            caret_ready_for_next = False

            ok, msg = append_quoted_subtitle_part(
                subtitle_line,
                label=f"{sec_idx}번째 소제목",
                leading_enters=subtitle_leading_enters,
                font_size=subtitle_size,
                quote_style=quote_style,
                use_current_caret=subtitle_use_current_caret,
            )
            if not ok:
                return False, msg, scopes

            scopes = _collect_scopes(page)
            caret_ready_for_next = True
            need_refocus = True

        if body_text:
            body_use_current_caret = caret_ready_for_next
            body_leading_enters = 1 if body_use_current_caret else (3 if editor_has_content else 0)
            caret_ready_for_next = False

            ok, msg = append_text_part(
                body_text,
                label=f"{sec_idx}번째 본문",
                leading_enters=body_leading_enters,
                font_size=body_size,
                use_current_caret=body_use_current_caret,
            )
            if not ok:
                return False, msg, scopes

        if use_random_image:
            _press_enters(page, 3)
            
            ok, msg, scopes = _insert_random_images(
                page,
                scopes,
                count=middle_image_count,
                insert_fn=_try_insert_random_middle_image,
                trace=trace,
                stage=f"subtitle#{sec_idx}",
            )
            if not ok:
                return False, f"이미지 삽입 실패(소제목 {sec_idx}): {msg}", scopes

            need_refocus = True
            caret_ready_for_next = False
            if middle_image_count:
                editor_has_content = True

    if closing_part:
        closing_use_current_caret = caret_ready_for_next
        closing_leading_enters = 1 if closing_use_current_caret else (2 if editor_has_content else 0)
        caret_ready_for_next = False
        ok, msg = append_text_part(
            closing_part,
            label="결론",
            leading_enters=closing_leading_enters,
            font_size=body_size,
            use_current_caret=closing_use_current_caret,
        )
        if not ok:
            return False, msg, scopes
    
    _press_enters(page, 2)
    
    if use_random_image:
        if str(bottom_image_link or "").strip():
            ok, msg, scopes = _insert_hyper_link_image(
                page,
                scopes,
                link=bottom_image_link,
                trace=trace,
            )
            if not ok:
                logger.warning("[trace_id=%s] publish hyper image insert/link failed message=%s", trace, msg)
                return False, f"hyper 이미지 링크 삽입 실패: {msg}", scopes
            editor_has_content = True

        ok, msg, scopes = _insert_random_images(
            page,
            scopes,
            count=bottom_image_count,
            insert_fn=_try_insert_random_bottom_image,
            trace=trace,
            stage="bottom",
            first_image_link=bottom_first_image_link,
        )
        if not ok:
            logger.warning("[trace_id=%s] publish bottom image insert failed message=%s", trace, msg)
            return False, f"이미지 삽입 실패(bottom): {msg}", scopes

        need_refocus = True
        caret_ready_for_next = False
        if bottom_image_count:
            editor_has_content = True

    if hashtag_part:
        hashtag_use_current_caret = caret_ready_for_next
        hashtag_leading_enters = 1 if hashtag_use_current_caret else (2 if editor_has_content else 0)
        caret_ready_for_next = False
        ok, msg = append_text_part(
            hashtag_part,
            label="해시태그",
            leading_enters=hashtag_leading_enters,
            font_size=body_size,
            use_current_caret=hashtag_use_current_caret,
        )
        if not ok:
            return False, msg, scopes

    if not wrote_text:
        return False, "입력할 본문 텍스트를 찾지 못했습니다.", scopes

    return True, "", scopes
