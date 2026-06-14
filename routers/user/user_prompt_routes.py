from fastapi import APIRouter

from services.prompt_service import load_titlegenarator_prompt, update_titlegenarator_prompt

router = APIRouter()

@router.get("/user/titleprompt/get")
def get_title_prompt():
    try:
        prompt_data = load_titlegenarator_prompt()
        return {
            "ok": True,
            "title_prompt": prompt_data.get("title_prompt", ""),
        }
    except Exception as e:
        return {"ok": False, "message": str(e), "title_prompt": ""}
    
@router.post("/user/titlesave-prompt")
def save_title_prompt(data: dict):
    try:
        prompt_data = load_titlegenarator_prompt()
        prompt_data["title_prompt"] = str(data.get("title_prompt", "")).strip()
        update_titlegenarator_prompt(prompt_data)
        return {"ok": True, "message": "저장 완료"}
    except Exception as e:
        return {"ok": False, "message": str(e)}