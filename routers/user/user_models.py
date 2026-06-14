from fastapi import APIRouter

from services.ai_runtime import get_supported_models

router = APIRouter()


@router.get("/user/models")
def user_models(provider: str):
    try:
        models = get_supported_models(provider)
        return {"ok": True, "provider": provider, "models": models}
    except Exception as e:
        return {"ok": False, "message": str(e), "models": []}
