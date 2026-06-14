from fastapi import APIRouter

from schemas.user import ApiKeySaveRequest
from services.ai_runtime import get_api_key_status, save_missing_api_keys

router = APIRouter()


@router.get("/user/api-keys/status")
def api_key_status():
    status = get_api_key_status()
    return {
        "ok": True,
        "gemini_exists": status["gemini_exists"],
        "openai_exists": status["openai_exists"],
        "all_ready": status["gemini_exists"] and status["openai_exists"],
    }


@router.post("/user/api-keys/save")
def save_api_keys(data: ApiKeySaveRequest):
    result = save_missing_api_keys(
        gemini_api_key=data.gemini_api_key,
        openai_api_key=data.openai_api_key,
    )

    if not result["ok"]:
        missing_labels = []
        if "gemini" in result.get("missing", []):
            missing_labels.append("Gemini")
        if "gpt" in result.get("missing", []):
            missing_labels.append("GPT")

        return {
            "ok": False,
            "message": f"누락된 키를 입력해 주세요: {', '.join(missing_labels)}",
            **result,
        }

    return {
        "ok": True,
        "message": "API 키 저장 완료",
        **result,
    }
