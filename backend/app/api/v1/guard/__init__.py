from fastapi import APIRouter
from .scan import router as scan_router
from .explain import router as explain_router
from .stats import router as stats_router
from .config import router as config_router
from .health import router as health_router

router = APIRouter()
router.include_router(scan_router)
router.include_router(explain_router)
router.include_router(stats_router)
router.include_router(config_router)
router.include_router(health_router)
