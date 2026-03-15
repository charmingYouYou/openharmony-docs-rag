"""Env-file endpoints for the local web console."""

from fastapi import APIRouter, HTTPException

from app.schemas import EnvPayload, EnvUpdateRequest
from app.services.env_file_service import EnvFileService

router = APIRouter()
env_service = EnvFileService()


@router.get("/env", response_model=EnvPayload)
def read_env():
    """Return the raw .env file."""
    return env_service.read_env()


@router.put("/env", response_model=EnvPayload)
def write_env(request: EnvUpdateRequest):
    """Save raw .env file text."""
    try:
        return env_service.write_env(request.raw)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
