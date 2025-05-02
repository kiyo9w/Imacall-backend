from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from typing import List

from app.api.deps import get_current_active_superuser
from app.services import ai_service
from app.models import Message # For response messages

router = APIRouter(
    prefix="/config", 
    tags=["config"], 
    dependencies=[Depends(get_current_active_superuser)] # Protect all config routes
)

# Endpoints will go here

@router.get("/ai/providers/available", response_model=List[str])
def get_available_ai_providers():
    """
    Get a list of available (initialized) AI provider names.
    Requires superuser privileges.
    """
    return ai_service.get_available_providers()

@router.get("/ai/providers/active", response_model=str)
def get_active_ai_provider():
    """
    Get the name of the currently active AI provider.
    Requires superuser privileges.
    """
    return ai_service.get_active_provider_name()

@router.put("/ai/providers/active", response_model=Message)
def set_active_ai_provider(provider_name: str):
    """
    Set the active AI provider.
    Requires superuser privileges.
    The provider must be available (initialized with a valid API key).
    """
    success = ai_service.set_active_provider(provider_name)
    if not success:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to set active provider. '{provider_name}' is not available or not initialized."
        )
    return Message(message=f"Active AI provider set to '{provider_name}'") 