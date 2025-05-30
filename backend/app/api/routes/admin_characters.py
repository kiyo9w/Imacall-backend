# Placeholder for admin character management routes 

import uuid
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlmodel import Session, select, func

from app.api.deps import SessionDep, CurrentUser, get_current_active_superuser
from app import crud
from app.models import (
    Character, CharacterUpdate, CharacterRejectRequest, CharacterPublic, CharactersPublic, CharacterStatus, Message, CharacterAdmin
)

router = APIRouter(prefix="/admin/characters", tags=["admin-characters"],
                   dependencies=[Depends(get_current_active_superuser)])

# Sort options type for validation
SortOption = Literal[
    "most_popular", "most_recent", "highest_rated", "name_asc", "name_desc", "oldest"
]


@router.get("/", response_model=CharactersPublic)
def list_all_characters(
    session: SessionDep, 
    skip: int = 0, 
    limit: int = 100, 
    status: CharacterStatus | None = Query(None, description="Filter by character status"),
    search: str | None = Query(None, description="Search term to filter characters"),
    category: str | None = Query(None, description="Filter characters by category"),
    sort_by: SortOption = Query("most_recent", description="Sort characters by specified criteria")
) -> Any:
    """
    Retrieve all characters across all users and statuses with advanced filtering.
    
    **Admin Features**:
    - View characters with any status (pending, approved, rejected)
    - Search across all character fields
    - Filter by category and status
    - Sort by various criteria
    """
    count = crud.characters.get_characters_count(
        session=session, 
        status=status,
        search=search,
        category=category
    )
    characters = crud.characters.get_characters(
        session=session, 
        skip=skip, 
        limit=limit, 
        status=status,
        search=search,
        category=category,
        sort_by=sort_by
    )
    return CharactersPublic(data=characters, count=count)


@router.get("/pending", response_model=CharactersPublic)
def list_pending_characters(
    session: SessionDep, 
    skip: int = 0, 
    limit: int = 100,
    search: str | None = Query(None, description="Search pending characters"),
    category: str | None = Query(None, description="Filter pending characters by category"),
    sort_by: SortOption = Query("most_recent", description="Sort pending characters")
) -> Any:
    """
    Retrieve all characters with pending status. Shortcut for /admin/characters/?status=pending
    """
    count = crud.characters.get_characters_count(
        session=session, 
        status=CharacterStatus.PENDING,
        search=search,
        category=category
    )
    characters = crud.characters.get_characters(
        session=session, 
        skip=skip, 
        limit=limit, 
        status=CharacterStatus.PENDING,
        search=search,
        category=category,
        sort_by=sort_by
    )
    return CharactersPublic(data=characters, count=count)


@router.get("/categories", response_model=list[str])
def get_all_categories(session: SessionDep) -> Any:
    """
    Get list of all available categories from all characters (admin view).
    """
    categories = crud.characters.get_available_categories(session=session)
    return categories


@router.patch("/{id}/approve", response_model=CharacterPublic)
def approve_character(session: SessionDep, id: uuid.UUID) -> Any:
    """
    Approve a character submission.
    Admin can approve characters with any status.
    """
    db_character = crud.characters.get_character(session=session, character_id=id)
    if not db_character:
        raise HTTPException(status_code=404, detail="Character not found")

    character_update = CharacterUpdate(status=CharacterStatus.APPROVED)
    character = crud.characters.update_character(
        session=session, db_character=db_character, character_in=character_update
    )
    return character


@router.patch("/{id}/reject", response_model=CharacterPublic)
def reject_character(session: SessionDep, id: uuid.UUID, request: CharacterRejectRequest | None = None) -> Any:
    """
    Reject a character submission.
    Admin can reject characters with any status and optionally provide feedback.
    """
    db_character = crud.characters.get_character(session=session, character_id=id)
    if not db_character:
        raise HTTPException(status_code=404, detail="Character not found")

    # Prepare update data
    update_data = {"status": CharacterStatus.REJECTED}
    if request and request.admin_feedback is not None:
        update_data["admin_feedback"] = request.admin_feedback
    
    character_update = CharacterUpdate(**update_data)
    character = crud.characters.update_character(
        session=session, db_character=db_character, character_in=character_update
    )
    return character


@router.get("/{id}", response_model=CharacterAdmin)
def get_character_admin(session: SessionDep, id: uuid.UUID) -> Any:
    """
    Get a specific character by ID (admin view).
    Returns character regardless of status and includes all fields.
    """
    db_character = crud.characters.get_character(session=session, character_id=id)
    if not db_character:
        raise HTTPException(status_code=404, detail="Character not found")
    
    return db_character


@router.put("/{id}", response_model=CharacterAdmin)
def update_character_admin(
    *, session: SessionDep, id: uuid.UUID, character_in: CharacterUpdate
) -> Any:
    """
    Update any character (admin only).
    Admin can edit characters regardless of status.
    """
    db_character = crud.characters.get_character(session=session, character_id=id)
    if not db_character:
        raise HTTPException(status_code=404, detail="Character not found")

    character = crud.characters.update_character(
        session=session, db_character=db_character, character_in=character_in
    )
    return character


@router.delete("/{id}")
def delete_character_admin(
    session: SessionDep, id: uuid.UUID
) -> Message:
    """
    Delete a character (admin only).
    """
    db_character = crud.characters.get_character(session=session, character_id=id)
    if not db_character:
        raise HTTPException(status_code=404, detail="Character not found")

    crud.characters.delete_character(session=session, db_character=db_character)
    return Message(message="Character deleted successfully") 