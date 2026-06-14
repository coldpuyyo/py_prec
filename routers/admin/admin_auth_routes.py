from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from services.admin_auth import verify_admin_credentials, is_admin_logged_in

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parents[2]
LOGIN_HTML = BASE_DIR / "static" / "admin" / "admin_login.html"


@router.get("/admin/login", response_class=HTMLResponse)
def admin_login_page(request: Request):
    if is_admin_logged_in(request.session):
        return RedirectResponse(url="/admin", status_code=303)
    return HTMLResponse(LOGIN_HTML.read_text(encoding="utf-8"))


@router.post("/admin/login")
def admin_login(request: Request, data: dict):
    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()

    if not verify_admin_credentials(username, password):
        return {"ok": False, "message": "아이디 또는 비밀번호가 올바르지 않습니다."}

    request.session["admin_logged_in"] = True
    request.session["admin_username"] = username
    return {"ok": True}


@router.post("/admin/logout")
def admin_logout(request: Request):
    request.session.clear()
    return {"ok": True}
