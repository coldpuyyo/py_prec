from fastapi import APIRouter, Request

from routers.admin.admin_deps import require_admin_api
from services.prompt_service import (
    load_blogscrapgenarator_prompt,
    load_keywordgenarator_prompt,
    load_scrapgenarator_prompt,
    load_titlegenarator_prompt,
    update_blogscrapgenarator_prompt,
    update_keywordgenarator_prompt,
    update_scrapgenarator_prompt,
    update_titlegenarator_prompt,
)

router = APIRouter()


@router.get("/admin/scrapprompt/get")
def get_prompt(request: Request):
    guard = require_admin_api(request)
    if guard:
        return guard

    try:
        prompt_data = load_scrapgenarator_prompt()
        return {
            "ok": True,
            "blog_prompt": prompt_data.get("blog_prompt", ""),
        }
    except Exception as e:
        return {"ok": False, "message": str(e), "blog_prompt": ""}


@router.post("/admin/scrapsave-prompt")
def save_prompt(request: Request, data: dict):
    guard = require_admin_api(request)
    if guard:
        return guard

    try:
        prompt_data = load_scrapgenarator_prompt()
        prompt_data["blog_prompt"] = str(data.get("blog_prompt", "")).strip()
        update_scrapgenarator_prompt(prompt_data)
        return {"ok": True, "message": "저장 완료"}
    except Exception as e:
        return {"ok": False, "message": str(e)}
    
@router.get("/admin/keywordprompt/get")
def get_keyword_prompt(request: Request):
    guard = require_admin_api(request)
    if guard:
        return guard

    try:
        prompt_data = load_keywordgenarator_prompt()
        return {
            "ok": True,
            "blog_prompt": prompt_data.get("blog_prompt", ""),
        }
    except Exception as e:
        return {"ok": False, "message": str(e), "blog_prompt": ""}
 
    
@router.post("/admin/keywordsave-prompt")
def save_keyword_prompt(request: Request, data: dict):
    guard = require_admin_api(request)
    if guard:
        return guard

    try:
        prompt_data = load_keywordgenarator_prompt()
        prompt_data["blog_prompt"] = str(data.get("blog_prompt", "")).strip()
        update_keywordgenarator_prompt(prompt_data)
        return {"ok": True, "message": "저장 완료"}
    except Exception as e:
        return {"ok": False, "message": str(e)}


@router.get("/admin/blogscrapprompt/get")
def get_blogscrap_prompt(request: Request):
    guard = require_admin_api(request)
    if guard:
        return guard

    try:
        prompt_data = load_blogscrapgenarator_prompt()
        return {
            "ok": True,
            "blog_prompt": prompt_data.get("blog_prompt", ""),
        }
    except Exception as e:
        return {"ok": False, "message": str(e), "blog_prompt": ""}


@router.post("/admin/blogscrapsave-prompt")
def save_blogscrap_prompt(request: Request, data: dict):
    guard = require_admin_api(request)
    if guard:
        return guard

    try:
        prompt_data = load_blogscrapgenarator_prompt()
        prompt_data["blog_prompt"] = str(data.get("blog_prompt", "")).strip()
        update_blogscrapgenarator_prompt(prompt_data)
        return {"ok": True, "message": "저장 완료"}
    except Exception as e:
        return {"ok": False, "message": str(e)}
    
@router.get("/admin/titleprompt/get")
def get_title_prompt(request: Request):
    guard = require_admin_api(request)
    if guard:
        return guard

    try:
        prompt_data = load_titlegenarator_prompt()
        return {
            "ok": True,
            "title_prompt": prompt_data.get("title_prompt", ""),
        }
    except Exception as e:
        return {"ok": False, "message": str(e), "title_prompt": ""}
    
@router.post("/admin/titlesave-prompt")
def save_title_prompt(request: Request, data: dict):
    guard = require_admin_api(request)
    if guard:
        return guard

    try:
        prompt_data = load_titlegenarator_prompt()
        prompt_data["title_prompt"] = str(data.get("title_prompt", "")).strip()
        update_titlegenarator_prompt(prompt_data)
        return {"ok": True, "message": "저장 완료"}
    except Exception as e:
        return {"ok": False, "message": str(e)}
