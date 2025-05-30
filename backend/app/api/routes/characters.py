# Placeholder for character submission and listing routes 

import uuid
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlmodel import Session, select, func

from app.api.deps import SessionDep, CurrentUser
from app import crud
from app.models import (
    Character, CharacterCreate, CharacterUpdateUser, CharacterPublic, CharactersPublic, CharacterStatus, Message
)

router = APIRouter(prefix="/characters", tags=["characters"])

# Sort options type for validation
SortOption = Literal[
    "most_popular", "most_recent", "highest_rated", "name_asc", "name_desc", "oldest"
]


@router.get("/", response_model=CharactersPublic)
def list_approved_characters(
    session: SessionDep, 
    skip: int = 0, 
    limit: int = 100,
    search: str | None = Query(None, description="Search term to filter characters by name, description, category, tags, or personality"),
    category: str | None = Query(None, description="Filter characters by category (case-insensitive)"),
    sort_by: SortOption = Query("most_popular", description="Sort characters by specified criteria")
) -> Any:
    """
    Retrieve approved characters with optional search, category filtering, and sorting.
    
    **Search**: Searches across name, description, category, tags, personality traits, and scenario
    **Category**: Filter by category (case-insensitive, use 'all' or omit for no filter)
    **Sort Options**:
    - most_popular: Sort by popularity score (default)
    - most_recent: Sort by creation date (newest first)
    - highest_rated: Sort by highest rating/popularity
    - name_asc: Sort by name A-Z
    - name_desc: Sort by name Z-A
    - oldest: Sort by creation date (oldest first)
    """
    count = crud.characters.get_characters_count(
        session=session, 
        status=CharacterStatus.APPROVED,
        search=search,
        category=category
    )
    characters = crud.characters.get_characters(
        session=session, 
        skip=skip, 
        limit=limit, 
        status=CharacterStatus.APPROVED,
        search=search,
        category=category,
        sort_by=sort_by
    )
    return CharactersPublic(data=characters, count=count)


@router.get("/categories", response_model=list[str])
def get_available_categories(session: SessionDep) -> Any:
    """
    Get list of available categories from approved characters.
    """
    categories = crud.characters.get_available_categories(
        session=session, 
        status=CharacterStatus.APPROVED
    )
    return categories


@router.get("/my-submissions", response_model=CharactersPublic)
def list_my_character_submissions(
    session: SessionDep, 
    current_user: CurrentUser, 
    skip: int = 0, 
    limit: int = 100,
    search: str | None = Query(None, description="Search term to filter your submitted characters"),
    category: str | None = Query(None, description="Filter your submitted characters by category"),
    sort_by: SortOption = Query("most_recent", description="Sort your submitted characters")
) -> Any:
    """
    Retrieve characters submitted by the current user with search and filtering.
    Includes characters with any status (pending, approved, rejected).
    """
    count = crud.characters.get_characters_count(
        session=session, 
        creator_id=current_user.id,
        search=search,
        category=category
    )
    characters = crud.characters.get_characters(
        session=session, 
        creator_id=current_user.id, 
        skip=skip, 
        limit=limit,
        search=search,
        category=category,
        sort_by=sort_by
    )
    return CharactersPublic(data=characters, count=count)


@router.get("/my-submissions/{id}", response_model=CharacterPublic)
def get_my_character_submission(
    session: SessionDep, current_user: CurrentUser, id: uuid.UUID
) -> Any:
    """
    Get a specific character that the current user submitted.
    Works regardless of character status.
    """
    character = crud.characters.get_character(session=session, character_id=id)
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    if character.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this character")
    return character


@router.put("/my-submissions/{id}", response_model=CharacterPublic)
def update_my_character_submission(
    *, session: SessionDep, current_user: CurrentUser, id: uuid.UUID, character_in: CharacterUpdateUser
) -> Any:
    """
    Update a character that the current user submitted.
    Users can only edit content fields, not admin fields like status.
    """
    db_character = crud.characters.get_character(session=session, character_id=id)
    if not db_character:
        raise HTTPException(status_code=404, detail="Character not found")
    
    try:
        character = crud.characters.update_character_by_user(
            session=session, db_character=db_character, character_in=character_in, user_id=current_user.id
        )
        return character
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/{id}", response_model=CharacterPublic)
def get_approved_character(
    session: SessionDep, id: uuid.UUID
) -> Any:
    """
    Get a specific approved character by ID.
    """
    character = crud.characters.get_character(session=session, character_id=id)
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    if character.status != CharacterStatus.APPROVED:
        # Hide non-approved characters from this public endpoint
        raise HTTPException(status_code=404, detail="Character not found") # Or 403 Forbidden
    return character


@router.post("/submit", response_model=CharacterPublic, status_code=201)
def submit_character(
    *, session: SessionDep, current_user: CurrentUser, character_in: CharacterCreate
) -> Any:
    """
    Submit a new character for review.
    Status defaults to 'pending'.
    """
    character = crud.characters.create_character(
        session=session, character_create=character_in, creator_id=current_user.id
    )
    return character 