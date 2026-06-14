from fastapi import APIRouter

from routers.user.user_page import router as page_router
from routers.user.user_api_key import router as api_keys_router
from routers.user.user_models import router as models_router
from routers.user.user_generator import router as generate_router
from routers.user.user_publish import router as publish_router
from routers.user.user_prompt_routes import router as prompt_router
from routers.user.user_profile_routes import router as profile_router

router = APIRouter()
router.include_router(page_router)
router.include_router(api_keys_router)
router.include_router(models_router)
router.include_router(generate_router)
router.include_router(publish_router)
router.include_router(prompt_router)
router.include_router(profile_router)
