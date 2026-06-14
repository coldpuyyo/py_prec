from fastapi import APIRouter, Request

from routers.admin.admin_deps import require_admin_api
from services.ai_runtime import get_api_key_status_for_admin, update_api_keys

router = APIRouter()


@router.get("/admin/api-keys/status")
def admin_api_keys_status(request: Request):
    guard = require_admin_api(request)
    if guard:
        return guard
    return {"ok": True, **get_api_key_status_for_admin()}


@router.post("/admin/api-keys/update")
def admin_api_keys_update(request: Request, data: dict):
    guard = require_admin_api(request)
    if guard:
        return guard

    return update_api_keys(
        gemini_api_key=data.get("gemini_api_key", ""),
        openai_api_key=data.get("openai_api_key", ""),
    )
