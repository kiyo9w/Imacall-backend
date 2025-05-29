from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from typing import List

from app.api.deps import get_current_active_superuser, SessionDep
from app.services import ai_service
from app.models import Message # For response messages

router = APIRouter(
    prefix="/config", 
    tags=["config"], 
    dependencies=[Depends(get_current_active_superuser)] # Protect all config routes
)

# Endpoints will go here

@router.get("/ai/providers/available", response_model=List[str])
def get_available_ai_providers(
    current_user: Session = Depends(get_current_active_superuser) # Admin only
):
    """
    Get a list of available (initialized) AI provider names.
    Requires superuser privileges.
    """
    return ai_service.get_available_providers()

@router.get("/ai/providers/active", response_model=dict)
def get_active_ai_provider(
    session: SessionDep, # Added session dependency
    current_user: Session = Depends(get_current_active_superuser) # Admin only
    # SessionDep will be used by the ai_service internally if needed for DB access
):
    """
    Get the name of the currently active AI provider.
    Requires superuser privileges.
    """
    try:
        # Pass the session to the service function
        provider_name = ai_service.get_active_ai_provider_name_from_service(session=session)
        return {"active_provider_name": provider_name}
    except Exception as e:
        # Log the exception e
        raise HTTPException(status_code=500, detail=f"Failed to get active AI provider: {str(e)}")

@router.put("/ai/providers/active", response_model=Message)
def set_active_ai_provider(
    provider_name: str, 
    session: SessionDep, # SessionDep is crucial here for the write operation
    current_user: Session = Depends(get_current_active_superuser) # Admin only
):
    """
    Set the active AI provider.
    Requires superuser privileges.
    The provider must be available (initialized with a valid API key).
    """
    try:
        # The refactored ai_service.set_active_provider will require the session
        ai_service.set_active_provider(name=provider_name, session=session)
        return Message(message=f"Active AI provider set to '{provider_name}'")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Log the exception e
        raise HTTPException(status_code=500, detail=f"Failed to set active AI provider: {str(e)}") 