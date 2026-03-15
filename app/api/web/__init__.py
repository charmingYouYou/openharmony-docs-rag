"""Web-console API router aggregation."""

from fastapi import APIRouter

from app.api.web import builds, config, services

router = APIRouter(prefix="/web")
router.include_router(builds.router)
router.include_router(config.router)
router.include_router(services.router)
