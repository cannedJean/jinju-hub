from fastapi import APIRouter

from app.api.v1.endpoints import health, meta, places

router = APIRouter()

# Mounted under settings.api_prefix by app.main. B4~B7 add their routers here.
router.include_router(health.router, tags=["health"])
router.include_router(meta.router, tags=["meta"])
router.include_router(places.router, tags=["places"])
