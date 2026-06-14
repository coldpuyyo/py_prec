from fastapi import APIRouter

from services.app_logger import get_logger
from services.naver_profile_registry_service import (
    delete_profile,
    list_profiles,
    upsert_profile,
)
from services.naver_profile_setup_service import (
    cancel_profile_setup,
    finish_profile_setup,
    get_profile_setup_status,
    start_profile_setup,
)

router = APIRouter()
logger = get_logger(__name__)


@router.post("/user/naver-profile/start")
async def user_naver_profile_start(data: dict):
    try:
        return await start_profile_setup(
            account_key=data.get("account_key", ""),
            role=data.get("role", "scraper"),
        )
    except Exception as e:
        logger.exception("user_naver_profile_start failed")
        return {"ok": False, "message": str(e)}


@router.get("/user/naver-profile/status")
async def user_naver_profile_status(account_key: str, role: str = "scraper"):
    try:
        return await get_profile_setup_status(account_key=account_key, role=role)
    except Exception as e:
        logger.exception("user_naver_profile_status failed account_key=%s role=%s", account_key, role)
        return {"ok": False, "message": str(e)}


@router.post("/user/naver-profile/finish")
async def user_naver_profile_finish(data: dict):
    try:
        return await finish_profile_setup(
            account_key=data.get("account_key", ""),
            role=data.get("role", "scraper"),
        )
    except Exception as e:
        logger.exception("user_naver_profile_finish failed")
        return {"ok": False, "message": str(e)}


@router.post("/user/naver-profile/cancel")
async def user_naver_profile_cancel(data: dict):
    try:
        return await cancel_profile_setup(
            account_key=data.get("account_key", ""),
            role=data.get("role", "scraper"),
        )
    except Exception as e:
        logger.exception("user_naver_profile_cancel failed")
        return {"ok": False, "message": str(e)}


@router.get("/user/naver-profiles/list")
def user_naver_profiles_list(role: str = "", active_only: bool = False):
    try:
        return {"ok": True, "items": list_profiles(role=role, active_only=active_only)}
    except Exception as e:
        logger.exception("user_naver_profiles_list failed role=%s active_only=%s", role, active_only)
        return {"ok": False, "message": str(e), "items": []}


@router.post("/user/naver-profiles/upsert")
def user_naver_profiles_upsert(data: dict):
    try:
        return upsert_profile(data)
    except Exception as e:
        logger.exception("user_naver_profiles_upsert failed")
        return {"ok": False, "message": str(e)}


@router.delete("/user/naver-profiles/{account_key}")
def user_naver_profiles_delete(account_key: str):
    try:
        return delete_profile(account_key)
    except Exception as e:
        logger.exception("user_naver_profiles_delete failed account_key=%s", account_key)
        return {"ok": False, "message": str(e)}
