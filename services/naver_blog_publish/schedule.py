from __future__ import annotations

import re
import time
from datetime import datetime
from typing import Any

from services.app_logger import get_logger

from .browser import (
    _click_first_visible,
    _click_publish_once,
    _collect_scopes,
    _dismiss_popups,
    _is_login_page,
    _is_write_page_url,
    _try_click_common_buttons,
)
from .debug import _debug_editor_state

logger = get_logger(__name__)

DATE_INPUT_SELECTORS = [
    "input[class*='input_date__']",
    "input[type='date']",
    "input[aria-label*='날짜']",
    "input[title*='날짜']",
    "input[placeholder*='날짜']",
    "input[aria-label*='일자']",
    "input[title*='일자']",
    "input[placeholder*='일자']",
    "input[aria-label*='예약일']",
    "input[title*='예약일']",
    "input[placeholder*='예약일']",
    "input[aria-label*='발행일']",
    "input[title*='발행일']",
    "input[placeholder*='발행일']",
    "input[name*='date' i]",
    "input[id*='date' i]",
    "input[class*='date' i]",
    "input[name*='reserve' i]",
    "input[id*='reserve' i]",
    "input[class*='reserve' i]",
    "input[name*='schedule' i]",
    "input[id*='schedule' i]",
    "input[class*='schedule' i]",
]

DATE_TRIGGER_SELECTORS = DATE_INPUT_SELECTORS + [
    "button[aria-label*='날짜']",
    "button[title*='날짜']",
    "button[aria-label*='예약일']",
    "button[title*='예약일']",
    "button[aria-label*='발행일']",
    "button[title*='발행일']",
    "button[class*='date' i]",
    "button[class*='reserve' i]",
    "button[class*='schedule' i]",
    "[role='button'][aria-label*='날짜']",
    "[role='button'][aria-label*='예약일']",
    "[role='button'][aria-label*='발행일']",
    "[role='button'][class*='date' i]",
    "[role='button'][class*='reserve' i]",
    "[role='button'][class*='schedule' i]",
]


def _parse_schedule_parts(scheduled_at: str) -> dict[str, str]:
    scheduled_dt = datetime.fromisoformat((scheduled_at or "").strip())
    return {
        "datetime_local": scheduled_dt.strftime("%Y-%m-%dT%H:%M"),
        "date_dash": scheduled_dt.strftime("%Y-%m-%d"),
        "date_dot": scheduled_dt.strftime("%Y.%m.%d"),
        "date_dot_spaced": f"{scheduled_dt.year}. {scheduled_dt.month}. {scheduled_dt.day}.",
        "date_dot_short": f"{scheduled_dt.year}.{scheduled_dt.month}.{scheduled_dt.day}",
        "date_korean": f"{scheduled_dt.year}년 {scheduled_dt.month}월 {scheduled_dt.day}일",
        "year": scheduled_dt.strftime("%Y"),
        "month": str(scheduled_dt.month),
        "month_2": scheduled_dt.strftime("%m"),
        "day": str(scheduled_dt.day),
        "day_2": scheduled_dt.strftime("%d"),
        "time": scheduled_dt.strftime("%H:%M"),
        "hour": str(scheduled_dt.hour),
        "hour_2": scheduled_dt.strftime("%H"),
        "minute": str(scheduled_dt.minute),
        "minute_2": scheduled_dt.strftime("%M"),
        "display": scheduled_dt.strftime("%Y-%m-%d %H:%M"),
    }


def _target_text(target) -> str:
    try:
        return str(
            target.evaluate(
                """el => [
                    el.value || "",
                    el.innerText || "",
                    el.textContent || "",
                    el.getAttribute("aria-label") || "",
                    el.getAttribute("title") || ""
                ].join(" ")"""
            )
            or ""
        )
    except Exception:
        return ""


def _numbers_in_text(value: str) -> list[int]:
    numbers: list[int] = []
    for item in re.findall(r"\d+", str(value or "")):
        try:
            numbers.append(int(item))
        except Exception:
            continue
    return numbers


def _text_has_target_date(value: str, parts: dict[str, str]) -> bool:
    text = str(value or "")
    if not text.strip():
        return False

    year = int(parts["year"])
    month = int(parts["month"])
    day = int(parts["day"])
    compact = re.sub(r"\s+", "", text)
    exact_candidates = {
        parts["date_dash"],
        parts["date_dot"],
        parts["date_dot_short"],
        parts["date_korean"].replace(" ", ""),
        f"{year}.{month}.{day}.",
        f"{year}.{month}.{day}",
        f"{year}-{int(parts['month']):02d}-{int(parts['day']):02d}",
    }
    if any(candidate and candidate in compact for candidate in exact_candidates):
        return True

    numbers = _numbers_in_text(text)
    for idx in range(max(0, len(numbers) - 2)):
        if numbers[idx] == year and numbers[idx + 1] == month and numbers[idx + 2] == day:
            return True

    # Some date pickers display only month/day after the year has already been implied.
    has_explicit_year = bool(re.search(r"\b20\d{2}\b|\b19\d{2}\b", text))
    if not has_explicit_year:
        for idx in range(max(0, len(numbers) - 1)):
            if numbers[idx] == month and numbers[idx + 1] == day:
                return True

    return False


def _target_has_date(target, parts: dict[str, str]) -> bool:
    return _text_has_target_date(_target_text(target), parts)


def _target_is_readonly(target) -> bool:
    try:
        return bool(
            target.evaluate(
                """el => {
                    const readonlyAttr = el.hasAttribute("readonly");
                    const ariaReadonly = String(el.getAttribute("aria-readonly") || "").toLowerCase() === "true";
                    return !!el.readOnly || readonlyAttr || ariaReadonly;
                }"""
            )
        )
    except Exception:
        return False


def _set_form_value(target, value: str, verify_fn=None) -> bool:
    try:
        target.scroll_into_view_if_needed(timeout=600)
    except Exception:
        pass

    if _target_is_readonly(target):
        return bool(verify_fn and verify_fn(target))

    try:
        target.fill(value, timeout=1200)
        try:
            target.press("Tab", timeout=500)
        except Exception:
            pass
        time.sleep(0.15)
        if verify_fn is None or verify_fn(target):
            return True
    except Exception:
        pass

    try:
        target.evaluate(
            """(el, value) => {
                const proto = Object.getPrototypeOf(el);
                const descriptor = proto ? Object.getOwnPropertyDescriptor(proto, "value") : null;
                if (descriptor && descriptor.set) {
                    descriptor.set.call(el, value);
                } else {
                    el.value = value;
                }
                el.dispatchEvent(new Event("input", { bubbles: true }));
                el.dispatchEvent(new Event("change", { bubbles: true }));
                el.dispatchEvent(new Event("blur", { bubbles: true }));
            }""",
            value,
        )
        try:
            target.press("Tab", timeout=500)
        except Exception:
            pass
        time.sleep(0.15)
        if verify_fn is None or verify_fn(target):
            return True
    except Exception:
        pass

    return False


def _fill_first_visible_control(scopes: list[Any], selectors: list[str], values: list[str], verify_fn=None) -> bool:
    for scope in scopes:
        for selector in selectors:
            try:
                loc = scope.locator(selector)
                count = loc.count()
            except Exception:
                continue

            for idx in range(min(count, 20)):
                try:
                    target = loc.nth(idx)
                    if not target.is_visible():
                        continue
                except Exception:
                    continue

                for value in values:
                    if _set_form_value(target, value, verify_fn=verify_fn):
                        return True
    return False


def _click_schedule_option(scopes: list[Any]) -> bool:
    role_targets = []
    for scope in scopes:
        try:
            role_targets.append(scope.get_by_role("radio", name="예약"))
        except Exception:
            pass
        try:
            role_targets.append(scope.get_by_label("예약", exact=True))
        except Exception:
            pass
        try:
            role_targets.append(scope.get_by_text("예약", exact=True))
        except Exception:
            pass

    for loc in role_targets:
        try:
            count = loc.count()
        except Exception:
            continue
        for idx in range(min(count, 10)):
            try:
                target = loc.nth(idx)
                if not target.is_visible():
                    continue
                target.click(timeout=1400)
                return True
            except Exception:
                try:
                    target.click(timeout=1400, force=True)
                    return True
                except Exception:
                    continue

    return _click_first_visible(
        scopes,
        [
            "label:has-text('예약')",
            "[role='radio']:has-text('예약')",
            "button:has-text('예약')",
            "span:has-text('예약')",
        ],
        timeout_ms=1400,
    )


def _option_number(value: str) -> int | None:
    match = re.search(r"\d+", str(value or ""))
    if not match:
        return None
    try:
        return int(match.group(0))
    except Exception:
        return None


def _selected_option_matches_number(target, expected: int, value_candidates: set[str] | None = None) -> bool:
    try:
        selected = target.evaluate(
            """el => {
                const opt = el.selectedOptions && el.selectedOptions.length ? el.selectedOptions[0] : null;
                if (!opt) return { value: el.value || "", text: "" };
                return { value: opt.value || "", text: opt.textContent || "" };
            }"""
        )
    except Exception:
        return False

    if not isinstance(selected, dict):
        return False

    value = str(selected.get("value", "") or "").strip()
    text = str(selected.get("text", "") or "").strip()
    if value_candidates and value in value_candidates:
        return True
    return _option_number(value) == expected or _option_number(text) == expected


def _select_option_by_number(target, expected: int, *, value_candidates: set[str] | None = None) -> bool:
    try:
        options = target.evaluate(
            """el => Array.from(el.options || []).map((opt) => ({
                value: opt.value || "",
                text: opt.textContent || ""
            }))"""
        )
    except Exception:
        return False

    if not isinstance(options, list):
        return False

    for option in options:
        if not isinstance(option, dict):
            continue
        value = str(option.get("value", "") or "").strip()
        text = str(option.get("text", "") or "").strip()
        if value_candidates and value in value_candidates:
            selected_value = value
        elif _option_number(value) == expected or _option_number(text) == expected:
            selected_value = value
        else:
            continue

        try:
            if selected_value:
                target.select_option(value=selected_value, timeout=1200)
            else:
                target.select_option(label=text, timeout=1200)
            time.sleep(0.1)
            if _selected_option_matches_number(target, expected, value_candidates=value_candidates):
                return True
        except Exception:
            continue
    return False


def _select_schedule_time(scopes: list[Any], parts: dict[str, str]) -> bool:
    expected_hour = int(parts["hour"])
    expected_minute = int(parts["minute"])
    hour_ok = False
    minute_ok = False

    for scope in scopes:
        try:
            loc = scope.locator("select")
            count = loc.count()
        except Exception:
            continue

        for idx in range(min(count, 30)):
            try:
                target = loc.nth(idx)
                if not target.is_visible():
                    continue
                options_text = target.evaluate(
                    "el => Array.from(el.options || []).map((opt) => (opt.value || '') + ' ' + (opt.textContent || '')).join(' ')"
                )
                marker = " ".join([
                    target.get_attribute("id") or "",
                    target.get_attribute("name") or "",
                    target.get_attribute("class") or "",
                    target.get_attribute("aria-label") or "",
                    target.get_attribute("title") or "",
                    str(options_text or ""),
                ]).lower()
            except Exception:
                continue

            hour_like = (
                "hour" in marker
                or "시" in marker
                or all(re.search(rf"(^|\D){n:02d}($|\D)|(^|\D){n}($|\D)", marker) for n in range(24))
            )
            minute_like = (
                "minute" in marker
                or "분" in marker
                or all(re.search(rf"(^|\D){n:02d}($|\D)|(^|\D){n}($|\D)", marker) for n in [0, 10, 20, 30, 40, 50])
            )

            if not hour_ok and hour_like:
                hour_ok = _select_option_by_number(
                    target,
                    expected_hour,
                    value_candidates={parts["hour"], parts["hour_2"]},
                )
                if hour_ok:
                    continue

            if not minute_ok and minute_like:
                minute_ok = _select_option_by_number(
                    target,
                    expected_minute,
                    value_candidates={parts["minute"], parts["minute_2"]},
                )

            if hour_ok and minute_ok:
                return True

    if not hour_ok:
        hour_ok = _fill_first_visible_control(
            scopes,
            [
                "input[aria-label*='시']",
                "input[title*='시']",
                "input[placeholder*='시']",
                "input[name*='hour' i]",
                "input[id*='hour' i]",
            ],
            [parts["hour_2"], parts["hour"]],
        )

    if not minute_ok:
        minute_ok = _fill_first_visible_control(
            scopes,
            [
                "input[aria-label*='분']",
                "input[title*='분']",
                "input[placeholder*='분']",
                "input[name*='minute' i]",
                "input[id*='minute' i]",
            ],
            [parts["minute_2"], parts["minute"]],
        )

    return hour_ok and minute_ok


def _select_schedule_date_parts(scopes: list[Any], parts: dict[str, str]) -> bool:
    year_ok = False
    month_ok = False
    day_ok = False

    for scope in scopes:
        try:
            loc = scope.locator("select")
            count = loc.count()
        except Exception:
            continue

        for idx in range(min(count, 30)):
            try:
                target = loc.nth(idx)
                if not target.is_visible():
                    continue
                marker = " ".join([
                    target.get_attribute("id") or "",
                    target.get_attribute("name") or "",
                    target.get_attribute("class") or "",
                    target.get_attribute("aria-label") or "",
                    target.get_attribute("title") or "",
                    target.evaluate("el => Array.from(el.options || []).map((opt) => opt.textContent || '').join(' ')") or "",
                ]).lower()
            except Exception:
                continue

            if not year_ok and ("year" in marker or "년" in marker):
                year_ok = _select_option_by_number(target, int(parts["year"]), value_candidates={parts["year"]})
                continue

            if not month_ok and ("month" in marker or "월" in marker):
                month_ok = _select_option_by_number(
                    target,
                    int(parts["month"]),
                    value_candidates={parts["month"], parts["month_2"]},
                )
                continue

            if not day_ok and ("day" in marker or "일" in marker):
                day_ok = _select_option_by_number(
                    target,
                    int(parts["day"]),
                    value_candidates={parts["day"], parts["day_2"]},
                )

    return year_ok and month_ok and day_ok


def _date_candidate_texts(scopes: list[Any]) -> list[str]:
    texts: list[str] = []
    seen: set[str] = set()
    for scope in scopes:
        for selector in DATE_TRIGGER_SELECTORS:
            try:
                loc = scope.locator(selector)
                count = loc.count()
            except Exception:
                continue

            for idx in range(min(count, 25)):
                try:
                    target = loc.nth(idx)
                    if not target.is_visible():
                        continue
                except Exception:
                    continue

                text = re.sub(r"\s+", " ", _target_text(target)).strip()
                if text and text not in seen:
                    seen.add(text)
                    texts.append(text[:120])
    return texts


def _detect_applied_schedule_date(scopes: list[Any], parts: dict[str, str]) -> tuple[bool, str]:
    for text in _date_candidate_texts(scopes):
        if _text_has_target_date(text, parts):
            return True, text
    return False, ""


def _fill_schedule_date_inputs(scopes: list[Any], parts: dict[str, str], trace: str) -> bool:
    verify_fn = lambda target: _target_has_date(target, parts)

    if _fill_first_visible_control(
        scopes,
        ["input[type='date']"],
        [parts["date_dash"]],
        verify_fn=verify_fn,
    ):
        logger.info("[trace_id=%s] schedule date applied via input[type=date] value=%s", trace, parts["date_dash"])
        return True

    text_selectors = [selector for selector in DATE_INPUT_SELECTORS if selector != "input[type='date']"]
    text_values = [
        parts["date_dot_spaced"],
        parts["date_dot"],
        parts["date_dash"],
        parts["date_dot_short"],
        parts["date_korean"],
    ]
    if _fill_first_visible_control(scopes, text_selectors, text_values, verify_fn=verify_fn):
        ok, detected = _detect_applied_schedule_date(scopes, parts)
        logger.info(
            "[trace_id=%s] schedule date applied via text input requested=%s detected=%s",
            trace,
            parts["date_dot_spaced"],
            detected,
        )
        return ok

    return False


def _scope_text(scope) -> str:
    try:
        return str(scope.evaluate("() => (document.body && document.body.innerText) ? document.body.innerText : ''") or "")
    except Exception:
        return ""


def _calendar_month_visible(scopes: list[Any], parts: dict[str, str]) -> bool:
    year = int(parts["year"])
    month = int(parts["month"])
    for scope in scopes:
        text = _scope_text(scope)
        if not text:
            continue
        compact = re.sub(r"\s+", "", text)
        month_candidates = [
            f"{year}.{month}",
            f"{year}.{int(parts['month']):02d}",
            f"{year}년{month}월",
            f"{year}-{int(parts['month']):02d}",
        ]
        if any(candidate in compact for candidate in month_candidates):
            return True

        numbers = _numbers_in_text(text)
        for idx in range(max(0, len(numbers) - 1)):
            if numbers[idx] == year and numbers[idx + 1] == month:
                return True
    return False


def _calendar_day_is_disabled(target) -> bool:
    try:
        return bool(
            target.evaluate(
                """el => {
                    const cls = String(el.className || "").toLowerCase();
                    const ariaDisabled = String(el.getAttribute("aria-disabled") || "").toLowerCase();
                    const disabled = !!el.disabled || ariaDisabled === "true";
                    return disabled || cls.includes("disabled") || cls.includes("dimmed") || cls.includes("outside");
                }"""
            )
        )
    except Exception:
        return False


def _click_calendar_day(scopes: list[Any], parts: dict[str, str], trace: str) -> bool:
    day = str(int(parts["day"]))
    day_2 = parts["day_2"]
    full_date_markers = [
        parts["date_dash"],
        parts["date_dot"],
        parts["date_dot_spaced"],
        parts["date_korean"],
    ]
    selectors = [
        "button",
        "[role='button']",
        "[role='gridcell']",
        "td",
        "a",
    ]

    for scope in scopes:
        for selector in selectors:
            try:
                loc = scope.locator(selector)
                count = loc.count()
            except Exception:
                continue

            for idx in range(min(count, 120)):
                try:
                    target = loc.nth(idx)
                    if not target.is_visible():
                        continue
                    if _calendar_day_is_disabled(target):
                        continue
                    text = re.sub(r"\s+", " ", _target_text(target)).strip()
                    visible_text = re.sub(r"\s+", " ", target.inner_text(timeout=300)).strip()
                except Exception:
                    continue

                compact = re.sub(r"\s+", "", text)
                text_matches_full_date = any(marker and marker.replace(" ", "") in compact for marker in full_date_markers)
                text_matches_day = visible_text in {day, day_2} or text in {day, day_2}
                if not text_matches_full_date and not text_matches_day:
                    continue

                try:
                    target.click(timeout=1400)
                    logger.info("[trace_id=%s] schedule calendar day clicked text=%s", trace, text[:80])
                    time.sleep(0.25)
                    return True
                except Exception:
                    try:
                        target.click(timeout=1400, force=True)
                        logger.info("[trace_id=%s] schedule calendar day force-clicked text=%s", trace, text[:80])
                        time.sleep(0.25)
                        return True
                    except Exception:
                        continue
    return False


def _click_calendar_nav(scopes: list[Any], direction: str) -> bool:
    if direction == "previous":
        selectors = [
            "button[aria-label*='이전']",
            "button[title*='이전']",
            "button:has-text('이전')",
            "button:has-text('<')",
            "[role='button'][aria-label*='이전']",
        ]
    else:
        selectors = [
            "button[aria-label*='다음']",
            "button[title*='다음']",
            "button:has-text('다음')",
            "button:has-text('>')",
            "[role='button'][aria-label*='다음']",
        ]
    return _click_first_visible(scopes, selectors, timeout_ms=1000)


def _open_schedule_calendar(scopes: list[Any], trace: str) -> bool:
    for scope in scopes:
        for selector in DATE_TRIGGER_SELECTORS:
            try:
                loc = scope.locator(selector)
                count = loc.count()
            except Exception:
                continue

            for idx in range(min(count, 25)):
                try:
                    target = loc.nth(idx)
                    if not target.is_visible():
                        continue
                    target.click(timeout=1200)
                    logger.info("[trace_id=%s] schedule calendar trigger clicked selector=%s", trace, selector)
                    time.sleep(0.25)
                    return True
                except Exception:
                    try:
                        target.click(timeout=1200, force=True)
                        logger.info("[trace_id=%s] schedule calendar trigger force-clicked selector=%s", trace, selector)
                        time.sleep(0.25)
                        return True
                    except Exception:
                        continue
    return False


def _select_schedule_date_via_calendar(scopes: list[Any], parts: dict[str, str], trace: str) -> bool:
    if not _open_schedule_calendar(scopes, trace):
        return False

    requested = datetime(int(parts["year"]), int(parts["month"]), int(parts["day"]))
    current_month_allowed = requested.year == datetime.now().year and requested.month == datetime.now().month

    for attempt in range(15):
        month_visible = _calendar_month_visible(scopes, parts)
        if month_visible or (attempt == 0 and current_month_allowed):
            if _click_calendar_day(scopes, parts, trace):
                ok, detected = _detect_applied_schedule_date(scopes, parts)
                logger.info(
                    "[trace_id=%s] schedule calendar date verification requested=%s detected=%s ok=%s",
                    trace,
                    parts["date_dot_spaced"],
                    detected,
                    ok,
                )
                return ok

        if not _click_calendar_nav(scopes, "next"):
            logger.info("[trace_id=%s] schedule calendar next navigation unavailable attempt=%s", trace, attempt)
            break
        time.sleep(0.25)

    return False


def _fill_schedule_date(scopes: list[Any], parts: dict[str, str], trace: str) -> bool:
    logger.info("[trace_id=%s] schedule date apply start requested=%s", trace, parts["date_dot_spaced"])

    if _fill_schedule_date_inputs(scopes, parts, trace):
        return True

    if _select_schedule_date_parts(scopes, parts):
        logger.info("[trace_id=%s] schedule date applied via select controls requested=%s", trace, parts["date_dot_spaced"])
        return True

    if _select_schedule_date_via_calendar(scopes, parts, trace):
        return True

    ok, detected = _detect_applied_schedule_date(scopes, parts)
    if ok:
        return True

    candidates = " | ".join(_date_candidate_texts(scopes)[:6])
    logger.warning(
        "[trace_id=%s] schedule date apply failed requested=%s detected=%s candidates=%s",
        trace,
        parts["date_dot_spaced"],
        detected,
        candidates,
    )
    return False


def _fill_schedule_datetime(scopes: list[Any], scheduled_at: str, trace: str) -> tuple[bool, str, str]:
    try:
        parts = _parse_schedule_parts(scheduled_at)
    except Exception:
        return False, "예약발행 시간 형식이 올바르지 않습니다.", ""

    if _fill_first_visible_control(
        scopes,
        [
            "input[type='datetime-local']",
            "input[name*='datetime' i]",
            "input[id*='datetime' i]",
            "input[class*='datetime' i]",
        ],
        [parts["datetime_local"]],
        verify_fn=lambda target: _target_has_date(target, parts),
    ):
        logger.info("[trace_id=%s] schedule datetime applied requested=%s", trace, parts["datetime_local"])
        return True, "", parts["display"]

    date_ok = _fill_schedule_date(scopes, parts, trace)

    if not date_ok:
        candidates = " | ".join(_date_candidate_texts(scopes)[:6])
        return (
            False,
            f"네이버 예약발행 날짜가 요청한 날짜({parts['date_dot_spaced']})로 적용되지 않았습니다. 감지값: {candidates or '없음'}",
            parts["display"],
        )

    time_ok = _fill_first_visible_control(
        scopes,
        [
            "input[type='time']",
            "input[aria-label*='시간']",
            "input[title*='시간']",
            "input[placeholder*='시간']",
        ],
        [parts["time"]],
    ) or _select_schedule_time(scopes, parts)

    if not time_ok:
        return False, "네이버 예약발행 시간 입력칸을 찾지 못했습니다.", parts["display"]

    return True, "", parts["display"]


def _publish_scheduled_flow(page, scopes: list[Any], scheduled_at: str, trace: str) -> tuple[bool, str, str]:
    _dismiss_popups(scopes)
    if not _click_publish_once(scopes, timeout_ms=2600):
        return False, "발행 설정 팝업을 열지 못했습니다.", ""

    page.wait_for_timeout(1300)
    scopes = _collect_scopes(page)

    if not _click_schedule_option(scopes):
        return False, "네이버 발행 설정에서 예약 옵션을 찾지 못했습니다.", ""

    page.wait_for_timeout(500)
    scopes = _collect_scopes(page)
    fill_ok, fill_message, display_at = _fill_schedule_datetime(scopes, scheduled_at, trace)
    if not fill_ok:
        return False, fill_message, display_at

    page.wait_for_timeout(500)
    scopes = _collect_scopes(page)
    if not _click_publish_once(scopes, timeout_ms=2600):
        return False, "예약발행 최종 버튼 클릭에 실패했습니다.", display_at

    deadline = time.monotonic() + 8.0
    while time.monotonic() < deadline:
        if _is_login_page(page):
            return False, "예약발행 도중 로그인 페이지로 이동했습니다.", display_at
        if not _is_write_page_url(page.url or ""):
            return True, "", display_at
        page.wait_for_timeout(350)

    scopes = _collect_scopes(page)
    if _try_click_common_buttons(scopes, ["확인"], timeout_ms=1800):
        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline:
            if not _is_write_page_url(page.url or ""):
                return True, "", display_at
            page.wait_for_timeout(350)

    logger.warning("[trace_id=%s] scheduled publish result not confirmed state=%s", trace, _debug_editor_state(page))
    return False, "예약발행 최종 처리 후 완료 상태를 확인하지 못했습니다. 네이버 발행 팝업 상태를 확인하세요.", display_at
