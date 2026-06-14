from __future__ import annotations

from typing import Any


def _debug_editor_state(page) -> str:
    try:
        frame_names = []
        for frame in page.frames:
            name = (frame.name or "").strip() or "(no-name)"
            frame_url = (frame.url or "").strip()
            frame_names.append(f"{name}:{frame_url[:90]}")
        return f"url={page.url}, frames={len(page.frames)} [{', '.join(frame_names)}]"
    except Exception:
        return f"url={page.url}"


def _extract_body_text_snippet(page, limit: int = 260) -> str:
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


def _debug_body_state(scopes: list[Any]) -> str:
    parts: list[str] = []
    for idx, scope in enumerate(scopes):
        try:
            count = scope.locator("[contenteditable='true']").count()
            parts.append(f"s{idx}:{count}")
        except Exception:
            parts.append(f"s{idx}:err")
        if idx >= 7:
            break
    return ", ".join(parts)
