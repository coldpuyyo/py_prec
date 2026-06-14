from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from routers.admin.admin_deps import require_admin_page

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parents[2]
DASHBOARD_HTML = BASE_DIR / "static" / "admin" / "admin_dashboard.html"
CAFES_HTML = BASE_DIR / "static" / "admin" / "admin_cafes.html"


@router.get("/admin", response_class=HTMLResponse)
def admin_page(request: Request):
    guard = require_admin_page(request)
    if guard:
        return guard
    return HTMLResponse(DASHBOARD_HTML.read_text(encoding="utf-8"))


@router.get("/admin/cafes", response_class=HTMLResponse)
def admin_cafes_page(request: Request):
    guard = require_admin_page(request)
    if guard:
        return guard
    return HTMLResponse(CAFES_HTML.read_text(encoding="utf-8"))
