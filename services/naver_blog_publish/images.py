from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from services.publish_image_service import (
    build_random_bottom_image_variant,
    build_random_hyper_image_variant,
    build_random_middle_image_variant,
    build_random_top_image_variant,
)

from .browser import _click_first_visible, _collect_scopes, _try_click_common_buttons


def _image_direct_selectors() -> list[str]:
    return [
        "button[data-name='image']",
        "button[data-testid*='image']",
        "button[data-testid*='photo']",
        "button[aria-label*='사진']",
        "button[aria-label*='이미지']",
        "button:has-text('사진')",
        "button:has-text('이미지')",
    ]


def _image_add_button_selectors() -> list[str]:
    return [
        "button[data-testid='seToolbarAddBasicButton']",
        "button[aria-label*='추가']",
        "button:has-text('추가')",
        "button:has-text('+')",
    ]


def _image_menu_selectors() -> list[str]:
    return [
        "[role='menuitem']:has-text('사진')",
        "[role='menuitem']:has-text('이미지')",
        "button:has-text('사진')",
        "button:has-text('이미지')",
    ]


def _click_image_insert_button(scopes: list[Any]) -> bool:
    for scope in scopes:
        for selector in _image_direct_selectors():
            try:
                loc = scope.locator(selector)
                if loc.count() == 0:
                    continue
                loc.first.click(timeout=2200)
                return True
            except Exception:
                continue

    for scope in scopes:
        for selector in _image_add_button_selectors():
            try:
                btn = scope.locator(selector)
                if btn.count() == 0:
                    continue
                btn.first.click(timeout=1800)
                scope.wait_for_timeout(250)
            except Exception:
                continue

            for menu_selector in _image_menu_selectors():
                try:
                    item = scope.locator(menu_selector)
                    if item.count() == 0:
                        continue
                    item.first.click(timeout=1800)
                    return True
                except Exception:
                    continue
    return False


def _upload_image_via_file_input(scopes: list[Any], image_path: str) -> bool:
    for scope in scopes:
        try:
            loc = scope.locator("input[type='file']")
            count = loc.count()
        except Exception:
            continue

        for idx in range(min(count, 20)):
            try:
                item = loc.nth(idx)
                accept = (item.get_attribute("accept") or "").lower()
                if accept and ("image" not in accept):
                    continue
                item.set_input_files(image_path, timeout=7000)
                return True
            except Exception:
                continue
    return False


def _upload_image_via_file_chooser(page, scopes: list[Any], image_path: str) -> bool:
    for scope in scopes:
        for selector in _image_direct_selectors():
            try:
                loc = scope.locator(selector)
                if loc.count() == 0:
                    continue
                with page.expect_file_chooser(timeout=3000) as chooser_info:
                    loc.first.click(timeout=2200)
                chooser = chooser_info.value
                chooser.set_files(image_path)
                return True
            except Exception:
                continue

    for scope in scopes:
        for add_selector in _image_add_button_selectors():
            try:
                add_btn = scope.locator(add_selector)
                if add_btn.count() == 0:
                    continue
                add_btn.first.click(timeout=1800)
                scope.wait_for_timeout(250)
            except Exception:
                continue

            for menu_selector in _image_menu_selectors():
                try:
                    menu_item = scope.locator(menu_selector)
                    if menu_item.count() == 0:
                        continue
                    with page.expect_file_chooser(timeout=3000) as chooser_info:
                        menu_item.first.click(timeout=2000)
                    chooser = chooser_info.value
                    chooser.set_files(image_path)
                    return True
                except Exception:
                    continue
    return False


def _try_insert_random_top_image(page, scopes: list[Any]) -> tuple[bool, str]:
    variant = build_random_top_image_variant()
    if not variant.get("ok"):
        return False, str(variant.get("message", "이미지 변형 생성 실패"))

    image_path = str(variant.get("image_path", "")).strip()
    if not image_path:
        return False, "생성된 이미지 경로가 비어 있습니다."
    if not Path(image_path).exists():
        return False, f"생성된 이미지 파일이 없습니다: {image_path}"

    if _upload_image_via_file_input(scopes, image_path):
        page.wait_for_timeout(3000)
        return True, image_path

    if _upload_image_via_file_chooser(page, scopes, image_path):
        page.wait_for_timeout(3500)
        return True, image_path

    _click_image_insert_button(scopes)
    page.wait_for_timeout(1200)

    for _ in range(3):
        fresh_scopes = _collect_scopes(page)
        if _upload_image_via_file_input(fresh_scopes, image_path):
            page.wait_for_timeout(3500)
            return True, image_path
        if _upload_image_via_file_chooser(page, fresh_scopes, image_path):
            page.wait_for_timeout(3500)
            return True, image_path
        page.wait_for_timeout(900)

    return False, f"이미지 업로드 input[type=file]을 찾지 못했습니다. image={image_path}"


def _try_insert_random_middle_image(page, scopes: list[Any]) -> tuple[bool, str]:
    variant = build_random_middle_image_variant()
    if not variant.get("ok"):
        return False, str(variant.get("message", "이미지 변형 생성 실패"))

    image_path = str(variant.get("image_path", "")).strip()
    if not image_path:
        return False, "생성된 이미지 경로가 비어 있습니다."
    if not Path(image_path).exists():
        return False, f"생성된 이미지 파일이 없습니다: {image_path}"

    before = _count_editor_images(_collect_scopes(page))
    if _upload_image_via_file_input(scopes, image_path):
        if _wait_image_count_increase(page, before, 9000):
            return True, image_path

    if _upload_image_via_file_chooser(page, scopes, image_path):
        page.wait_for_timeout(3500)
        return True, image_path

    _click_image_insert_button(scopes)
    page.wait_for_timeout(1200)

    for _ in range(3):
        fresh_scopes = _collect_scopes(page)
        if _upload_image_via_file_input(fresh_scopes, image_path):
            page.wait_for_timeout(3500)
            return True, image_path
        if _upload_image_via_file_chooser(page, fresh_scopes, image_path):
            page.wait_for_timeout(3500)
            return True, image_path
        page.wait_for_timeout(900)

    return False, f"이미지 업로드 input[type=file]을 찾지 못했습니다. image={image_path}"


def _try_insert_random_bottom_image(page, scopes: list[Any]) -> tuple[bool, str]:
    variant = build_random_bottom_image_variant()
    if not variant.get("ok"):
        return False, str(variant.get("message", "이미지 변형 생성 실패"))

    image_path = str(variant.get("image_path", "")).strip()
    if not image_path:
        return False, "생성된 이미지 경로가 비어 있습니다."
    if not Path(image_path).exists():
        return False, f"생성된 이미지 파일이 없습니다: {image_path}"

    if _upload_image_via_file_input(scopes, image_path):
        page.wait_for_timeout(3000)
        return True, image_path

    if _upload_image_via_file_chooser(page, scopes, image_path):
        page.wait_for_timeout(3500)
        return True, image_path

    _click_image_insert_button(scopes)
    page.wait_for_timeout(1200)

    for _ in range(3):
        fresh_scopes = _collect_scopes(page)
        if _upload_image_via_file_input(fresh_scopes, image_path):
            page.wait_for_timeout(3500)
            return True, image_path
        if _upload_image_via_file_chooser(page, fresh_scopes, image_path):
            page.wait_for_timeout(3500)
            return True, image_path
        page.wait_for_timeout(900)

    return False, f"이미지 업로드 input[type=file]을 찾지 못했습니다. image={image_path}"


def _try_insert_random_hyper_image(page, scopes: list[Any]) -> tuple[bool, str]:
    variant = build_random_hyper_image_variant()
    if not variant.get("ok"):
        return False, str(variant.get("message", "hyper 이미지 변형 생성 실패"))

    image_path = str(variant.get("image_path", "")).strip()
    if not image_path:
        return False, "생성된 hyper 이미지 경로가 비어 있습니다."
    if not Path(image_path).exists():
        return False, f"생성된 hyper 이미지 파일이 없습니다: {image_path}"

    if _upload_image_via_file_input(scopes, image_path):
        page.wait_for_timeout(3000)
        return True, image_path

    if _upload_image_via_file_chooser(page, scopes, image_path):
        page.wait_for_timeout(3500)
        return True, image_path

    _click_image_insert_button(scopes)
    page.wait_for_timeout(1200)

    for _ in range(3):
        fresh_scopes = _collect_scopes(page)
        if _upload_image_via_file_input(fresh_scopes, image_path):
            page.wait_for_timeout(3500)
            return True, image_path
        if _upload_image_via_file_chooser(page, fresh_scopes, image_path):
            page.wait_for_timeout(3500)
            return True, image_path
        page.wait_for_timeout(900)

    return False, f"hyper 이미지 업로드 input[type=file]을 찾지 못했습니다. image={image_path}"


def _is_last_image_center(scopes: list[Any]) -> bool:
    js = """
    () => {
      const root = document.querySelector("article") || document;
      const items = Array.from(
        root.querySelectorAll(".se-component-image .se-section-image, .se-image .se-section-image, .se-section-image")
      );
      if (!items.length) return false;
      const last = items[items.length - 1];
      return last.classList.contains("se-section-align-center");
    }
    """
    for scope in scopes:
        try:
            if bool(scope.evaluate(js)):
                return True
        except Exception:
            continue
    return False


def _open_align_dropdown(scopes: list[Any]) -> bool:
    selectors = [
        "button[data-name='align-drop-down-with-justify']",
        ".se-toolbar-item-align button.se-property-toolbar-drop-down-button",
        ".se-toolbar-item-align button[class*='align'][class*='toolbar-button']",
    ]
    for scope in scopes:
        for sel in selectors:
            try:
                loc = scope.locator(sel)
                if loc.count() == 0:
                    continue
                loc.first.click(timeout=1200)
                return True
            except Exception:
                continue
    return False


def _click_center_align_control(page, scopes: list[Any]) -> bool:
    # 이미 가운데면 성공 처리
    if _is_last_image_center(scopes):
        return True

    # 1) 드롭다운 열기 -> 가운데 버튼 클릭
    _open_align_dropdown(scopes)
    center_selectors = [
        "button.se-align-center-toolbar-button",
        "button[class*='align-center-toolbar-button']",
        "button[aria-label*='가운데']",
        "button[title*='가운데']",
        "button:has-text('가운데')",
        "[role='menuitem']:has-text('가운데')",
    ]

    for scope in scopes:
        for sel in center_selectors:
            try:
                loc = scope.locator(sel)
                if loc.count() == 0:
                    continue
                loc.first.click(timeout=1200)
                page.wait_for_timeout(150)
                if _is_last_image_center(_collect_scopes(page)):
                    return True
            except Exception:
                continue

    # 2) 텍스트 기반 버튼 클릭
    if _try_click_common_buttons(scopes, ["가운데 정렬", "가운데", "중앙 정렬", "중앙"], timeout_ms=1200):
        page.wait_for_timeout(150)
        if _is_last_image_center(_collect_scopes(page)):
            return True

    # 3) 단축키 fallback (검증 필수)
    for key in ["Control+Shift+E", "Control+E", "Control+Shift+C"]:
        try:
            page.keyboard.press(key)
            page.wait_for_timeout(150)
            if _is_last_image_center(_collect_scopes(page)):
                return True
        except Exception:
            continue

    return False


def _select_last_image_component(scopes: list[Any]) -> bool:
    selectors = [
        "article .se-component.se-image .se-section-image",
        "article .se-component.se-image",
        "article .se-image .se-section-image",
        "article .se-image",
        ".se-component.se-image .se-section-image",
        ".se-component.se-image",
        ".se-image .se-section-image",
        ".se-image",
    ]
    for scope in scopes:
        for sel in selectors:
            try:
                loc = scope.locator(sel)
                cnt = loc.count()
                if cnt == 0:
                    continue
                target = loc.nth(cnt - 1)
                try:
                    target.scroll_into_view_if_needed(timeout=1000)
                except Exception:
                    pass
                target.click(timeout=1600, force=True)
                return True
            except Exception:
                continue
    return False


def _align_last_image_center(page, scopes: list[Any]) -> bool:
    # 실패를 숨기지 말고 실제 성공/실패를 반환
    if not _select_last_image_component(scopes):
        return False

    for _ in range(3):
        fresh = _collect_scopes(page)
        if _click_center_align_control(page, fresh):
            if _is_last_image_center(_collect_scopes(page)):
                return True
        page.wait_for_timeout(120)

    return False


def _link_button_selectors() -> list[str]:
    return [
        ".se-property-toolbar button:has(span.se-toolbar-icon):has(span.se-blind:has-text('링크'))",
        ".se-property-toolbar [role='button']:has(span.se-toolbar-icon):has(span.se-blind:has-text('링크'))",
        ".se-image-toolbar button:has(span.se-toolbar-icon):has(span.se-blind:has-text('링크'))",
        ".se-image-toolbar [role='button']:has(span.se-toolbar-icon):has(span.se-blind:has-text('링크'))",
        "[class*='property'] button:has(span.se-toolbar-icon):has(span.se-blind:has-text('링크'))",
        "[class*='property'] [role='button']:has(span.se-toolbar-icon):has(span.se-blind:has-text('링크'))",
        "[class*='image'] button:has(span.se-toolbar-icon):has(span.se-blind:has-text('링크'))",
        "[class*='image'] [role='button']:has(span.se-toolbar-icon):has(span.se-blind:has-text('링크'))",
        "[class*='floating'] button:has(span.se-toolbar-icon):has(span.se-blind:has-text('링크'))",
        "[class*='floating'] [role='button']:has(span.se-toolbar-icon):has(span.se-blind:has-text('링크'))",
        ".se-property-toolbar-button[data-name*='link']",
    ]


def _link_url_input_selectors() -> list[str]:
    return [
        "input[type='url']",
        "input[name*='url' i]",
        "input[id*='url' i]",
        "input[class*='url' i]",
        "input[placeholder*='URL']",
        "input[placeholder*='url' i]",
        "input[placeholder*='링크']",
        "input[aria-label*='URL']",
        "input[aria-label*='url' i]",
        "input[aria-label*='링크']",
        "input[title*='URL']",
        "input[title*='url' i]",
        "input[title*='링크']",
        "textarea[placeholder*='URL']",
        "textarea[placeholder*='url' i]",
        "textarea[placeholder*='링크']",
        "[contenteditable='true'][aria-label*='URL']",
        "[contenteditable='true'][aria-label*='url' i]",
        "[contenteditable='true'][aria-label*='링크']",
    ]


def _link_confirm_selectors() -> list[str]:
    return [
        "button[data-name*='apply']",
        "button[data-name*='confirm']",
        "button[class*='apply']",
        "button[class*='confirm']",
        "button:has-text('적용')",
        "button:has-text('확인')",
        "button:has-text('완료')",
        "[role='button']:has-text('적용')",
        "[role='button']:has-text('확인')",
        "[role='button']:has-text('완료')",
    ]


def _click_nearest_image_link_button(page, scopes: list[Any]) -> bool:
    js = r"""
    () => {
      const visible = (el) => {
        if (!el || !el.getClientRects || el.getClientRects().length === 0) return false;
        const style = window.getComputedStyle(el);
        if (!style || style.visibility === "hidden" || style.display === "none") return false;
        const rect = el.getBoundingClientRect();
        return rect.width > 0 && rect.height > 0;
      };

      const root = document.querySelector("article") || document;
      const images = Array.from(
        root.querySelectorAll(
          ".se-component.se-image, .se-component-image, .se-image, .se-section-image"
        )
      ).filter(visible);
      if (!images.length) return false;

      const image = images[images.length - 1];
      const imageRect = image.getBoundingClientRect();
      const imageCx = imageRect.left + imageRect.width / 2;
      const imageCy = imageRect.top + imageRect.height / 2;

      const buttons = Array.from(document.querySelectorAll("button, [role='button']"))
        .filter((button) => {
          if (!visible(button)) return false;
          if (!button.querySelector("span.se-toolbar-icon")) return false;
          return Array.from(button.querySelectorAll("span.se-blind")).some((span) => {
            return (span.textContent || "").replace(/\s+/g, " ").trim() === "링크";
          });
        })
        .map((button) => {
          const rect = button.getBoundingClientRect();
          const bx = rect.left + rect.width / 2;
          const by = rect.top + rect.height / 2;
          const marker = [
            button.className || "",
            button.closest("[class*='property']") ? "property" : "",
            button.closest("[class*='image']") ? "image" : "",
            button.closest("[class*='floating']") ? "floating" : "",
            button.closest("[class*='toolbar']") ? "toolbar" : "",
          ].join(" ").toLowerCase();
          const distance = Math.hypot(bx - imageCx, by - imageCy);
          let score = distance;
          if (marker.includes("property")) score -= 10000;
          if (marker.includes("image")) score -= 5000;
          if (marker.includes("floating")) score -= 2500;
          return { button, marker, distance, score };
        })
        .filter((item) => {
          return (
            item.marker.includes("property") ||
            item.marker.includes("image") ||
            item.marker.includes("floating") ||
            item.distance < 260
          );
        });

      if (!buttons.length) return false;
      buttons.sort((a, b) => a.score - b.score);
      buttons[0].button.click();
      return true;
    }
    """
    for scope in scopes:
        try:
            if bool(scope.evaluate(js)):
                page.wait_for_timeout(250)
                return True
        except Exception:
            continue
    return False


def _open_link_dialog(page, scopes: list[Any]) -> bool:
    if _click_nearest_image_link_button(page, scopes):
        page.wait_for_timeout(250)
        return True

    if _click_first_visible(scopes, _link_button_selectors(), timeout_ms=1300):
        page.wait_for_timeout(250)
        return True

    return False


def _fill_link_url_input(page, scopes: list[Any], url: str) -> bool:
    text = str(url or "").strip()
    if not text:
        return False

    for scope in scopes:
        for selector in _link_url_input_selectors():
            try:
                loc = scope.locator(selector)
                count = loc.count()
            except Exception:
                continue

            if count == 0:
                continue

            for idx in range(min(count, 20)):
                try:
                    target = loc.nth(idx)
                    if not target.is_visible():
                        continue
                except Exception:
                    continue

                try:
                    target.fill(text, timeout=1200)
                    return True
                except Exception:
                    pass

                try:
                    target.click(timeout=1000, force=True)
                    page.keyboard.press("Control+A")
                    page.keyboard.type(text)
                    return True
                except Exception:
                    continue

    return False


def _confirm_link_dialog(page, scopes: list[Any]) -> bool:
    if _click_first_visible(scopes, _link_confirm_selectors(), timeout_ms=1300):
        page.wait_for_timeout(350)
        return True

    if _try_click_common_buttons(scopes, ["적용", "확인", "완료"], timeout_ms=1200):
        page.wait_for_timeout(350)
        return True

    try:
        page.keyboard.press("Enter")
        page.wait_for_timeout(350)
        return True
    except Exception:
        return False


def _apply_link_to_last_image(page, scopes: list[Any], url: str) -> bool:
    link = str(url or "").strip()
    if not link:
        return True

    for _ in range(3):
        fresh = _collect_scopes(page)
        if not _select_last_image_component(fresh):
            page.wait_for_timeout(200)
            continue

        fresh = _collect_scopes(page)
        if not _open_link_dialog(page, fresh):
            page.wait_for_timeout(250)
            continue

        fresh = _collect_scopes(page)
        if not _fill_link_url_input(page, fresh, link):
            page.wait_for_timeout(250)
            continue

        fresh = _collect_scopes(page)
        if _confirm_link_dialog(page, fresh):
            return True

        page.wait_for_timeout(250)

    return False


def _insert_random_images(
    page,
    scopes: list[Any],
    count: int,
    insert_fn,
    trace: str,
    stage: str,
    first_image_link: str = "",
):
    try:
        n = max(0, int(count or 0))
    except Exception:
        n = 0

    if n == 0:
        return True, "", scopes

    for idx in range(n):
        ok, msg = insert_fn(page, scopes)
        if not ok:
            return False, f"{stage}({idx+1}/{n}) {msg}", scopes

        scopes = _collect_scopes(page)

        aligned = _align_last_image_center(page, scopes)
        if not aligned:
            return False, f"{stage}({idx+1}/{n}) 이미지 컴포넌트 선택/가운데 정렬 실패", scopes

        page.wait_for_timeout(250)

        if not _is_last_image_center(_collect_scopes(page)):
            return False, f"{stage}({idx+1}/{n}) 이미지 가운데 정렬 검증 실패", scopes

        page.wait_for_timeout(250)

        link = str(first_image_link or "").strip()
        if idx == 0 and link:
            if not _apply_link_to_last_image(page, _collect_scopes(page), link):
                return False, f"{stage}({idx+1}/{n}) 첫 이미지 링크 주입 실패", scopes
            scopes = _collect_scopes(page)
            page.wait_for_timeout(250)

    return True, "", scopes


def _insert_hyper_link_image(page, scopes: list[Any], link: str, trace: str):
    url = str(link or "").strip()
    if not url:
        return True, "", scopes

    ok, msg, scopes = _insert_random_images(
        page,
        scopes,
        count=1,
        insert_fn=_try_insert_random_hyper_image,
        trace=trace,
        stage="hyper",
    )
    if not ok:
        return False, msg, scopes

    if not _apply_link_to_last_image(page, _collect_scopes(page), url):
        return False, "hyper 이미지 링크 주입 실패", scopes

    scopes = _collect_scopes(page)
    page.wait_for_timeout(250)
    return True, "", scopes


def _count_editor_images(scopes: list[Any]) -> int:
    js = """
    () => {
      const root = document.querySelector("article") || document;
      return root.querySelectorAll(".se-component-image, .se-image").length;
    }
    """
    for scope in scopes:
        try:
            return int(scope.evaluate(js) or 0)
        except Exception:
            continue
    return 0


def _wait_image_count_increase(page, before: int, timeout_ms: int = 8000) -> bool:
    start = time.time()
    while (time.time() - start) * 1000 < timeout_ms:
        scopes = _collect_scopes(page)
        now = _count_editor_images(scopes)
        if now >= before + 1:
            return True
        page.wait_for_timeout(250)
    return False
