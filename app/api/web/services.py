"""Runtime-service endpoints for the local web console."""

from fastapi import APIRouter

from app.schemas import ServiceStatus
from app.services.service_status_service import ServiceStatusService

router = APIRouter()
service_status_service = ServiceStatusService()


@router.get("/services", response_model=list[ServiceStatus])
def list_services():
    """Return the configured runtime services and ports."""
    return service_status_service.list_services()
