from fastapi import APIRouter, Request

from routers.admin.admin_deps import require_admin_api
from services.cafe_admin_service import list_cafes, create_cafe, update_cafe, delete_cafe

router = APIRouter()


@router.get("/admin/cafes/list")
def admin_cafes_list(request: Request):
    guard = require_admin_api(request)
    if guard:
        return guard
    return {"ok": True, "items": list_cafes()}


@router.post("/admin/cafes/create")
def admin_cafes_create(request: Request, data: dict):
    guard = require_admin_api(request)
    if guard:
        return guard
    return create_cafe(data)


@router.put("/admin/cafes/{cafe_id}")
def admin_cafes_update(request: Request, cafe_id: str, data: dict):
    guard = require_admin_api(request)
    if guard:
        return guard
    return update_cafe(cafe_id, data)


@router.delete("/admin/cafes/{cafe_id}")
def admin_cafes_delete(request: Request, cafe_id: str):
    guard = require_admin_api(request)
    if guard:
        return guard
    return delete_cafe(cafe_id)
