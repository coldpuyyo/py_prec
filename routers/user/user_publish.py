import traceback
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter

from schemas.user import BlogPublishRequest
from services.app_logger import get_logger
from services.naver_blog_publish_service import publish_naver_blog_post
from services.naver_profile_registry_service import list_profiles
from services.vpn_service import (
    ensure_vpn_connected_before_publish,
    disconnect_vpn_after_publish,
)

router = APIRouter()
logger = get_logger(__name__)
KST = timezone(timedelta(hours=9))


def _normalize_publish_schedule(data: BlogPublishRequest) -> tuple[bool, str, str, str]:
    mode = (data.publish_mode or "now").strip().lower()
    if mode not in {"now", "scheduled"}:
        return False, "발행 방식 값이 올바르지 않습니다.", "now", ""

    if mode == "now":
        return True, "", "now", ""

    raw = (data.scheduled_at or "").strip()
    if not raw:
        return False, "예약발행 시간을 입력하세요.", mode, ""

    try:
        scheduled_dt = datetime.fromisoformat(raw)
    except ValueError:
        return False, "예약발행 시간 형식이 올바르지 않습니다.", mode, raw

    if scheduled_dt.tzinfo is None:
        scheduled_dt = scheduled_dt.replace(tzinfo=KST)
    else:
        scheduled_dt = scheduled_dt.astimezone(KST)

    if scheduled_dt <= datetime.now(KST):
        return False, "예약발행 시간은 현재보다 이후여야 합니다.", mode, raw

    if scheduled_dt.minute % 10 != 0 or scheduled_dt.second != 0 or scheduled_dt.microsecond != 0:
        return False, "네이버 예약발행 시간은 10분 단위로 입력하세요.", mode, raw

    return True, "", mode, scheduled_dt.strftime("%Y-%m-%dT%H:%M")

@router.get("/user/publisher-profiles")
def user_publisher_profiles():
    logger.info("user_publisher_profiles requested")
    try:
        items = list_profiles(role="publisher", active_only=True)
        logger.info("user_publisher_profiles success count=%s", len(items))
        return {"ok": True, "items": items}
    except Exception as e:
        logger.exception("user_publisher_profiles failed")
        return {"ok": False, "items": [], "message": str(e)}


@router.post("/user/publish")
def user_publish_blog(data: BlogPublishRequest):
    trace_id = uuid.uuid4().hex[:12]
    schedule_ok, schedule_message, publish_mode, scheduled_at = _normalize_publish_schedule(data)
    
    logger.info(
        "[trace_id=%s] user_publish_blog start profile=%s blog_id=%s publish_mode=%s scheduled_at=%s include_random_image=%s has_hyper_image_link=%s has_bottom_first_image_link=%s has_vpn_override=%s",
        trace_id,
        data.publisher_profile_key,
        data.blog_id,
        publish_mode,
        scheduled_at,
        data.include_random_image,
        bool((data.bottom_image_link or "").strip()),
        bool((data.bottom_first_image_link or "").strip()),
        bool((data.vpn_activation_code or "").strip()),
    )

    if not schedule_ok:
        logger.warning("[trace_id=%s] user_publish_blog schedule validation failed message=%s", trace_id, schedule_message)
        return {"ok": False, "message": schedule_message, "trace_id": trace_id}

    vpn_connected = False
    publish_result: dict = {"ok": False, "message": "unknown error"}
    disconnect_result: dict | None = None

    try:
        vpn_result = ensure_vpn_connected_before_publish(
            activation_code_override=data.vpn_activation_code,
        )
        if not vpn_result.get("ok"):
            debug = vpn_result.get("debug", {}) or {}
            detail = ""

            steps = debug.get("steps") if isinstance(debug, dict) else None
            if isinstance(steps, list) and steps:
                last = steps[-1]
                if isinstance(last, dict):
                    detail = str(last.get("output", "")).strip()

            message = vpn_result.get("message", "VPN command failed")
            if detail:
                message = f"{message}: {detail[:700]}"
                
            logger.warning(
                "[trace_id=%s] user_publish_blog vpn precheck failed message=%s detail=%s",
                trace_id,
                vpn_result.get("message", ""),
                detail[:300],
            )

            return {
                "ok": False,
                "message": message,
                "vpn_debug": debug,
            }

        vpn_connected = not vpn_result.get("skipped", False)
        logger.info(
            "[trace_id=%s] user_publish_blog vpn precheck ok skipped=%s",
            trace_id,
            vpn_result.get("skipped", False),
        )

        publish_result = publish_naver_blog_post(
            title=data.title,
            content=data.content,
            publisher_profile_key=data.publisher_profile_key,
            blog_id=data.blog_id,
            publish_mode=publish_mode,
            scheduled_at=scheduled_at,
            include_random_image=data.include_random_image,
            middle_image_count=max(0, min(10, int(data.middle_image_count or 0))),
            bottom_image_count=max(0, min(10, int(data.bottom_image_count or 0))),
            bottom_image_link=(data.bottom_image_link or "").strip(),
            bottom_first_image_link=(data.bottom_first_image_link or "").strip(),
            typing_delay_min=max(0, min(500, int(data.typing_delay_min or 30))),
            typing_delay_max=max(0, min(500, int(data.typing_delay_max or 85))),
            conclusion_paragraph_count=max(0, min(10, int(data.conclusion_paragraph_count or 0))),
            body_font_size=data.body_font_size,
            subtitle_font_size=data.subtitle_font_size,
            subtitle_quote_style=max(1, min(5, int(data.subtitle_quote_style or 1))),
        )
        
        logger.info(
            "[trace_id=%s] user_publish_blog publish finished ok=%s message=%s",
            trace_id,
            publish_result.get("ok"),
            str(publish_result.get("message", ""))[:200],
        )
        
    except Exception as e:
        logger.exception(
            "[trace_id=%s] user_publish_blog exception profile=%s",
            trace_id,
            data.publisher_profile_key,
        )
        return {
            "ok": False,
            "message": str(e),
            "vpn_debug": {"traceback": traceback.format_exc()},
        }
    finally:
        if vpn_connected:
            disconnect_result = disconnect_vpn_after_publish()
            logger.info(
                "[trace_id=%s] user_publish_blog vpn disconnect result ok=%s message=%s",
                trace_id,
                disconnect_result.get("ok") if isinstance(disconnect_result, dict) else None,
                disconnect_result.get("message", "") if isinstance(disconnect_result, dict) else "",
            )

    if disconnect_result and not disconnect_result.get("ok"):
        warning_msg = disconnect_result.get("message", "VPN disconnect failed")
        if publish_result.get("ok"):
            publish_result["disconnect_warning"] = warning_msg
            publish_result["disconnect_debug"] = disconnect_result.get("debug", {})
        else:
            base = str(publish_result.get("message", "")).strip()
            publish_result["message"] = f"{base} / disconnect warning: {warning_msg}".strip()
            publish_result["disconnect_debug"] = disconnect_result.get("debug", {})

    publish_result.setdefault("trace_id", trace_id)
    return publish_result
    
