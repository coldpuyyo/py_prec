from fastapi import APIRouter, Request

from routers.admin.admin_deps import require_admin_api
from services.vpn_config_service import get_vpn_config_for_admin, update_vpn_config
from services.app_logger import get_logger

router = APIRouter()
logger = get_logger(__name__)

@router.get("/admin/vpn/config")
def admin_vpn_config_get(request: Request):
    guard = require_admin_api(request)
    if guard:
        return guard
    try:
        return {"ok": True, "config": get_vpn_config_for_admin()}
    except Exception as exc:
        logger.exception("admin_vpn_config_get failed")
        return {"ok": False, "message": str(exc), "config": {}}


@router.post("/admin/vpn/config")
def admin_vpn_config_update(request: Request, data: dict):
    guard = require_admin_api(request)
    if guard:
        return guard
    try:
        return update_vpn_config(data)
    except Exception as exc:
        logger.exception("admin_vpn_config_update failed")
        return {"ok": False, "message": str(exc)}
