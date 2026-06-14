from fastapi import APIRouter

from routers.admin.admin_auth_routes import router as auth_router
from routers.admin.admin_page_routes import router as page_router
from routers.admin.admin_prompt_routes import router as prompt_router
from routers.admin.admin_api_keys_routes import router as api_key_router
from routers.admin.admin_cafes_routes import router as cafe_router
from routers.admin.admin_vpn_routes import router as vpn_router

router = APIRouter()

router.include_router(vpn_router)
router.include_router(auth_router)
router.include_router(page_router)
router.include_router(prompt_router)
router.include_router(api_key_router)
router.include_router(cafe_router)
