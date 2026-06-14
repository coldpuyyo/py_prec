import json
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parents[2]
TEMPLATE_PATH = BASE_DIR / "static" / "user" / "user.html"
PROFILE_TEMPLATE_PATH = BASE_DIR / "static" / "user" / "user_profile.html"
CATEGORIES_PATH = BASE_DIR / "data" / "categories.json"


@router.get("/user", response_class=HTMLResponse)
def user_page():
    return TEMPLATE_PATH.read_text(encoding="utf-8")


@router.get("/user/profile", response_class=HTMLResponse)
def user_profile_page():
    return PROFILE_TEMPLATE_PATH.read_text(encoding="utf-8")


@router.get("/user/categories")
def user_categories():
    try:
        categories = json.loads(CATEGORIES_PATH.read_text(encoding="utf-8"))
        return {"ok": True, "categories": categories}
    except Exception as e:
        return {"ok": False, "categories": [], "message": str(e)}
