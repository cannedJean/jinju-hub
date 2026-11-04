from fastapi import APIRouter

from app.api.v1.endpoints import health

router = APIRouter()

# Mounted under settings.api_prefix by app.main. B3~B7 add their routers here.
router.include_router(health.router, tags=["health"])
