from fastapi import APIRouter

from app.api.v1.analytics import router as analytics_router
from app.api.v1.auth import router as auth_router
from app.api.v1.conversations import router as conversations_router
from app.api.v1.fashion import router as fashion_router
from app.api.v1.health import router as health_router
from app.api.v1.jobs import router as jobs_router
from app.api.v1.orders import router as orders_router
from app.api.v1.payments import router as payments_router
from app.api.v1.products import router as products_router
from app.api.v1.shops import router as shops_router
from app.api.v1.semantic_search import router as semantic_search_router
from app.api.v1.simulator import router as simulator_router
from app.api.v1.webhooks import router as webhooks_router

router = APIRouter()

router.include_router(health_router)
router.include_router(auth_router)
router.include_router(shops_router)
router.include_router(products_router)
router.include_router(orders_router)
router.include_router(conversations_router)
router.include_router(semantic_search_router)
router.include_router(payments_router)
router.include_router(webhooks_router)
router.include_router(jobs_router)

router.include_router(fashion_router)
router.include_router(simulator_router)
router.include_router(analytics_router)
