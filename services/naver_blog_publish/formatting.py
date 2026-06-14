from __future__ import annotations

import re
from html import escape
from typing import Any

from services.app_logger import get_logger

from .browser import _click_first_visible, _collect_scopes
from .constants import DEFAULT_BODY_FONT_SIZE, DEFAULT_SUBTITLE_QUOTE_STYLE, PUBLISH_FONT_SIZES

logger = get_logger(__name__)


def _normalize_font_size(value: str | int, default: str) -> str:
    text = str(value or "").strip()
    if text in PUBLISH_FONT_SIZES:
        return text

    match = re.search(r"\d+", text)
    if match and match.group(0) in PUBLISH_FONT_SIZES:
        return match.group(0)

    return default


def _normalize_quote_style(value: str | int, default: int = DEFAULT_SUBTITLE_QUOTE_STYLE) -> int:
    try:
        n = int(value)
    except Exception:
        n = default
    return max(1, min(5, n))


def _quote_label(value: int) -> str:
    return f"인용구 {_normalize_quote_style(value)}"


def _font_size_menu_selectors() -> list[str]:
    return [
        "button[data-name='fontSize']",
        "button[data-name='font-size']",
        "button[data-name='font_size']",
        "button[data-name*='fontSize']",
        "button[data-name*='font-size']",
        "button[data-name*='font_size']",
        "[role='button'][data-name*='fontSize']",
        "[role='button'][data-name*='font-size']",
        ".se-toolbar-item-fontSize button",
        ".se-toolbar-item-font-size button",
        ".se-toolbar-font-size button",
        ".se-toolbar-item:has-text('글자 크기') button",
        ".se-toolbar-item:has-text('글씨 크기') button",
        "button[aria-label*='글자 크기']",
        "button[title*='글자 크기']",
        "[role='button'][aria-label*='글자 크기']",
        "[role='button'][title*='글자 크기']",
        "button[aria-label*='글씨 크기']",
        "button[title*='글씨 크기']",
        "[role='button'][aria-label*='글씨 크기']",
        "[role='button'][title*='글씨 크기']",
        "button:has-text('글자 크기')",
        "[role='button']:has-text('글자 크기')",
        "button:has-text('글씨 크기')",
        "[role='button']:has-text('글씨 크기')",
    ]


def _font_size_option_selectors(size: str) -> list[str]:
    labels = [size, f"{size}px", f"{size} px", f"{size}pt", f"{size} pt"]
    selectors: list[str] = []
    for label in labels:
        text = label.replace("\\", "\\\\").replace("'", "\\'")
        selectors.extend([
            f"button:has(span.se-toolbar-tooltip:has-text('{text}'))",
            f"[role='button']:has(span.se-toolbar-tooltip:has-text('{text}'))",
            f"[role='menuitem']:has(span.se-toolbar-tooltip:has-text('{text}'))",
            f"[role='option']:has(span.se-toolbar-tooltip:has-text('{text}'))",
            f"li:has(span.se-toolbar-tooltip:has-text('{text}'))",
            f".se-toolbar-button:has(span.se-toolbar-tooltip:has-text('{text}'))",
            f"button[aria-label='{text}']",
            f"button[title='{text}']",
            f"[role='button'][aria-label='{text}']",
            f"[role='button'][title='{text}']",
            f"[role='menuitem'][aria-label='{text}']",
            f"[role='menuitem'][title='{text}']",
            f"[role='option'][aria-label='{text}']",
            f"[role='option'][title='{text}']",
            f"button:has-text('{text}')",
            f"[role='button']:has-text('{text}')",
            f"[role='menuitem']:has-text('{text}')",
            f"[role='option']:has-text('{text}')",
            f"li:has-text('{text}')",
        ])
    return selectors


def _apply_font_size_to_current_paragraph(page, scopes: list[Any], font_size: str) -> bool:
    size = _normalize_font_size(font_size, DEFAULT_BODY_FONT_SIZE)
    if not size:
        return True

    fresh = _collect_scopes(page)
    if not _click_first_visible(fresh, _font_size_menu_selectors(), timeout_ms=1200):
        logger.warning("font size apply failed: menu not found size=%s", size)
        return False

    page.wait_for_timeout(180)
    fresh = _collect_scopes(page)
    if _click_first_visible(fresh, _font_size_option_selectors(size), timeout_ms=1200):
        page.wait_for_timeout(220)
        return True

    logger.warning("font size apply failed: option not found size=%s", size)
    return False


def _focus_current_editor_selection(scopes: list[Any]) -> bool:
    js = r"""
    () => {
      const sel = window.getSelection();
      if (!sel || !sel.anchorNode) return false;

      let el = sel.anchorNode.nodeType === Node.ELEMENT_NODE
        ? sel.anchorNode
        : sel.anchorNode.parentElement;
      if (!el) return false;

      const article = document.querySelector("article");
      if (article && !article.contains(el)) return false;
      if (el.closest("[role='toolbar'], .se-toolbar, [class*='toolbar']")) return false;

      const host =
        el.closest("[contenteditable='true'], [role='textbox']") ||
        el.querySelector("[contenteditable='true'], [role='textbox']");
      if (!host) return false;

      host.focus();
      return true;
    }
    """
    for scope in scopes:
        try:
            if bool(scope.evaluate(js)):
                return True
        except Exception:
            continue
    return False


def _quote_menu_selectors() -> list[str]:
    return [
        "button[data-name*='quote']",
        "button[data-name*='quotation']",
        "button[data-name*='blockquote']",
        "[role='button'][data-name*='quote']",
        "[role='button'][data-name*='quotation']",
        ".se-toolbar-item-quote button",
        ".se-toolbar-item-quotation button",
        ".se-toolbar-item-blockquote button",
        "button[aria-label*='인용구']",
        "button[title*='인용구']",
        "[role='button'][aria-label*='인용구']",
        "[role='button'][title*='인용구']",
        "button:has-text('인용구')",
        "[role='button']:has-text('인용구')",
    ]


def _quote_option_selectors(label: str) -> list[str]:
    text = label.replace("\\", "\\\\").replace("'", "\\'")
    return [
        f"button:has(span.se-toolbar-tooltip:has-text('{text}'))",
        f"[role='button']:has(span.se-toolbar-tooltip:has-text('{text}'))",
        f"[role='menuitem']:has(span.se-toolbar-tooltip:has-text('{text}'))",
        f"li:has(span.se-toolbar-tooltip:has-text('{text}'))",
        f".se-toolbar-button:has(span.se-toolbar-tooltip:has-text('{text}'))",
        f"button[aria-label*='{text}']",
        f"button[title*='{text}']",
        f"[role='button'][aria-label*='{text}']",
        f"[role='button'][title*='{text}']",
        f"[role='menuitem'][aria-label*='{text}']",
        f"[role='menuitem'][title*='{text}']",
        f"button:has-text('{text}')",
        f"[role='button']:has-text('{text}')",
        f"[role='menuitem']:has-text('{text}')",
    ]


def _quote_block_selectors() -> list[str]:
    return [
        "article .se-component[class*='quotation']",
        "article .se-component[class*='quote']",
        "article .se-component[class*='blockquote']",
        "article [class*='se-quotation']",
        "article [class*='se-quote']",
        "article [class*='blockquote']",
        "article blockquote",
        ".se-component[class*='quotation']",
        ".se-component[class*='quote']",
        ".se-component[class*='blockquote']",
        "[class*='se-quotation']",
        "[class*='se-quote']",
        "[class*='blockquote']",
        "blockquote",
    ]


def _selection_quote_state(scopes: list[Any]) -> bool | None:
    js = r"""
    () => {
      const sel = window.getSelection();
      if (!sel || !sel.anchorNode) return null;

      let el = sel.anchorNode.nodeType === Node.ELEMENT_NODE
        ? sel.anchorNode
        : sel.anchorNode.parentElement;
      if (!el) return null;

      const article = document.querySelector("article");
      if (article && !article.contains(el)) return null;

      const textRoot =
        el.closest("p.se-text-paragraph, .se-module-text, .se-component, blockquote, [contenteditable='true']") ||
        el;

      function textValue(value) {
        if (!value) return "";
        if (typeof value === "string") return value;
        if (typeof value.baseVal === "string") return value.baseVal;
        return String(value);
      }

      function markerFor(node) {
        if (!node || node.nodeType !== Node.ELEMENT_NODE) return "";
        return [
          node.tagName || "",
          textValue(node.className),
          node.getAttribute("data-name") || "",
          node.getAttribute("data-type") || "",
          node.getAttribute("data-module") || "",
          node.getAttribute("role") || "",
          node.getAttribute("aria-label") || "",
          node.getAttribute("title") || "",
        ].join(" ").toLowerCase();
      }

      for (let cur = textRoot; cur && cur !== document; cur = cur.parentElement) {
        const marker = markerFor(cur);
        if (
          marker.includes("quote") ||
          marker.includes("quotation") ||
          marker.includes("blockquote") ||
          marker.includes("인용구") ||
          (cur.tagName || "").toLowerCase() === "blockquote"
        ) {
          return true;
        }
        if (cur.classList && cur.classList.contains("se-component")) {
          break;
        }
      }

      return false;
    }
    """
    for scope in scopes:
        try:
            state = scope.evaluate(js)
            if state is not None:
                return bool(state)
        except Exception:
            continue
    return None


def _selection_plain_text_state(scopes: list[Any]) -> bool:
    js = r"""
    () => {
      const sel = window.getSelection();
      if (!sel || !sel.anchorNode) return false;

      let el = sel.anchorNode.nodeType === Node.ELEMENT_NODE
        ? sel.anchorNode
        : sel.anchorNode.parentElement;
      if (!el) return false;

      const article = document.querySelector("article");
      if (article && !article.contains(el)) return false;
      if (el.closest("[role='toolbar'], .se-toolbar, [class*='toolbar']")) return false;

      const component = el.closest(".se-component");
      const paragraph = el.closest("p.se-text-paragraph, .se-module-text, [contenteditable='true']");
      if (!component && !paragraph) return false;

      function textValue(value) {
        if (!value) return "";
        if (typeof value === "string") return value;
        if (typeof value.baseVal === "string") return value.baseVal;
        return String(value);
      }

      const marker = [
        component ? textValue(component.className) : "",
        paragraph ? textValue(paragraph.className) : "",
        component ? component.getAttribute("data-name") || "" : "",
        component ? component.getAttribute("data-type") || "" : "",
        paragraph ? paragraph.getAttribute("data-name") || "" : "",
        paragraph ? paragraph.getAttribute("data-type") || "" : "",
      ].join(" ").toLowerCase();

      if (
        marker.includes("quote") ||
        marker.includes("quotation") ||
        marker.includes("blockquote") ||
        marker.includes("인용구") ||
        !!el.closest("blockquote")
      ) {
        return false;
      }

      return (
        marker.includes("se-text") ||
        !!el.closest(".se-component.se-text, p.se-text-paragraph, .se-module-text, [contenteditable='true']")
      );
    }
    """
    for scope in scopes:
        try:
            if bool(scope.evaluate(js)):
                return True
        except Exception:
            continue
    return False


def _click_below_last_quote_block(page, scopes: list[Any]) -> bool:
    for scope in scopes:
        for selector in _quote_block_selectors():
            try:
                loc = scope.locator(selector)
                count = loc.count()
            except Exception:
                continue

            if count == 0:
                continue

            for idx in range(min(count, 20) - 1, -1, -1):
                try:
                    target = loc.nth(idx)
                    if not target.is_visible():
                        continue
                    if not bool(
                        target.evaluate(
                            """el => {
                              const marker = [
                                el.closest("article") ? "article" : "",
                                el.closest("[contenteditable='true']") ? "editable" : "",
                                el.closest("[role='toolbar'], .se-toolbar, [class*='toolbar']") ? "toolbar" : "",
                              ].join(" ");
                              return (marker.includes("article") || marker.includes("editable")) && !marker.includes("toolbar");
                            }"""
                        )
                    ):
                        continue
                    target.scroll_into_view_if_needed(timeout=700)
                    box = target.bounding_box()
                except Exception:
                    continue

                if not box:
                    continue

                try:
                    width = float(box.get("width", 0))
                    height = float(box.get("height", 0))
                    base_x = float(box.get("x", 0)) + max(24.0, min(width / 2, width - 12.0))
                    base_y = float(box.get("y", 0)) + height

                    for y_offset in (24.0, 40.0, 64.0, 92.0):
                        page.mouse.click(base_x, base_y + y_offset)
                        page.wait_for_timeout(220)
                        if _selection_plain_text_state(_collect_scopes(page)):
                            return True
                except Exception:
                    continue
    return False


def _last_quote_block_contains_text(scopes: list[Any], expected_text: str) -> bool:
    expected = str(expected_text or "").strip()
    if not expected:
        return False

    js = r"""
    ({ selectors, expected }) => {
      const normalize = (value) => String(value || "")
        .replace(/\u200b/g, "")
        .replace(/\s+/g, " ")
        .trim();

      const wanted = normalize(expected);
      if (!wanted) return false;

      const root = document.querySelector("article") || document;
      const seen = new Set();
      const candidates = [];

      for (const selector of selectors) {
        for (const el of Array.from(root.querySelectorAll(selector))) {
          if (seen.has(el)) continue;
          seen.add(el);
          if (el.closest("[role='toolbar'], .se-toolbar, [class*='toolbar']")) continue;
          if (!el.getClientRects || el.getClientRects().length === 0) continue;
          candidates.push(el);
        }
      }

      if (!candidates.length) return false;
      candidates.sort((a, b) => {
        if (a === b) return 0;
        const pos = a.compareDocumentPosition(b);
        return pos & Node.DOCUMENT_POSITION_FOLLOWING ? -1 : 1;
      });

      const quote = candidates[candidates.length - 1];
      return normalize(quote.innerText || quote.textContent || "").includes(wanted);
    }
    """

    payload = {"selectors": _quote_block_selectors(), "expected": expected}
    for scope in scopes:
        try:
            if bool(scope.evaluate(js, payload)):
                return True
        except Exception:
            continue
    return False


def _place_caret_after_last_quote_block(page, scopes: list[Any]) -> bool:
    return _click_below_last_quote_block(page, scopes)


def _apply_quote_style_to_current_paragraph(page, scopes: list[Any], quote_style: int) -> bool:
    label = _quote_label(quote_style)

    fresh = _collect_scopes(page)

    if _click_first_visible(fresh, _quote_option_selectors(label), timeout_ms=1200):
        page.wait_for_timeout(250)
        return True

    if not _click_first_visible(fresh, _quote_menu_selectors(), timeout_ms=1200):
        logger.warning("quote apply failed: quote menu not found label=%s", label)
        return False

    page.wait_for_timeout(180)
    fresh = _collect_scopes(page)
    if _click_first_visible(fresh, _quote_option_selectors(label), timeout_ms=1200):
        page.wait_for_timeout(250)
        return True

    logger.warning("quote apply failed: quote option not found label=%s", label)
    return False


def _exit_quote_block_for_body(page, scopes: list[Any]) -> bool:
    if _selection_quote_state(_collect_scopes(page)) is False:
        return True

    return _place_caret_after_last_quote_block(page, scopes)


def _build_rich_text_clipboard_html(text: str, *, font_size: str) -> str:
    size = _normalize_font_size(font_size, DEFAULT_BODY_FONT_SIZE)
    fs_class = f"se-fs-fs{size}" if size else ""

    style_parts = []
    if size:
        style_parts.append(f"font-size: {size}px")
    style_attr = "; ".join(style_parts)
    if style_attr:
        style_attr += ";"

    class_attr = fs_class
    escaped_class = escape(class_attr, quote=True)
    escaped_style = escape(style_attr, quote=True)

    lines = str(text or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if not lines:
        lines = [""]

    paragraphs: list[str] = []
    for line in lines:
        if not line.strip():
            paragraphs.append("<p><br></p>")
            continue

        escaped_line = escape(line, quote=False)
        paragraphs.append(
            (
                f'<p class="{escaped_class}" style="{escaped_style}">'
                f'<span class="{escaped_class}" style="{escaped_style}">{escaped_line}</span>'
                "</p>"
            )
        )

    return '<meta charset="utf-8">' + "".join(paragraphs)


def _write_clipboard_rich_text(page, *, html: str, plain_text: str) -> bool:
    origin = ""
    try:
        match = re.match(r"^https?://[^/]+", page.url or "")
        if match:
            origin = match.group(0)
    except Exception:
        origin = ""

    try:
        if origin:
            page.context.grant_permissions(["clipboard-read", "clipboard-write"], origin=origin)
        else:
            page.context.grant_permissions(["clipboard-read", "clipboard-write"])
    except Exception:
        pass

    js = """
    async ({ html, plainText }) => {
      if (!navigator.clipboard || !window.ClipboardItem) {
        return { ok: false, reason: "clipboard_api_unavailable" };
      }

      const item = new ClipboardItem({
        "text/html": new Blob([html], { type: "text/html" }),
        "text/plain": new Blob([plainText], { type: "text/plain" })
      });
      await navigator.clipboard.write([item]);
      return { ok: true };
    }
    """

    try:
        result = page.evaluate(js, {"html": html, "plainText": plain_text})
        if isinstance(result, dict):
            if result.get("ok"):
                return True
            logger.warning("rich clipboard write failed reason=%s", result.get("reason", "unknown"))
            return False
        return bool(result)
    except Exception as exc:
        logger.warning("rich clipboard write exception=%s", exc)
        return False


def _paste_rich_text(page, text: str, *, font_size: str) -> bool:
    plain = str(text or "")
    html = _build_rich_text_clipboard_html(plain, font_size=font_size)

    if not _write_clipboard_rich_text(page, html=html, plain_text=plain):
        return False

    try:
        page.keyboard.press("Control+V")
        page.wait_for_timeout(250)
        return True
    except Exception as exc:
        logger.warning("rich text paste failed exception=%s", exc)
        return False
