from fastapi import Request
from fastapi.responses import JSONResponse, RedirectResponse, Response

from services.admin_auth import is_admin_logged_in


def require_admin_page(request: Request) -> Response | None:
    if not is_admin_logged_in(request.session):
        return RedirectResponse(url="/admin/login", status_code=303)
    return None


def require_admin_api(request: Request) -> Response | None:
    if not is_admin_logged_in(request.session):
        return JSONResponse(
            status_code=401,
            content={"ok": False, "message": "관리자 로그인이 필요합니다."},
        )
    return None
