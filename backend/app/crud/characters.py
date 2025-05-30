# Placeholder for character CRUD operations 

import uuid
from typing import Sequence, Literal
from sqlmodel import Session, select, col, func, or_, desc, asc

from app.models import Character, CharacterCreate, CharacterUpdate, CharacterUpdateUser, CharacterStatus, User

# Define valid sort options
SortOption = Literal[
    "most_popular", "most_recent", "highest_rated", "name_asc", "name_desc", "oldest"
]


def create_character(
    *, session: Session, character_create: CharacterCreate, creator_id: uuid.UUID
) -> Character:
    """Creates a new character with status 'pending'."""
    db_obj = Character.model_validate(
        character_create, update={"creator_id": creator_id, "status": CharacterStatus.PENDING}
    )
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def get_character(*, session: Session, character_id: uuid.UUID) -> Character | None:
    """Gets a character by ID."""
    return session.get(Character, character_id)


def get_characters(
    *,
    session: Session,
    skip: int = 0,
    limit: int = 100,
    status: CharacterStatus | None = None,
    creator_id: uuid.UUID | None = None,
    search: str | None = None,
    category: str | None = None,
    sort_by: SortOption = "most_popular",
) -> Sequence[Character]:
    """Gets a list of characters with optional filters, search, and sorting."""
    statement = select(Character)
    
    # Apply filters
    if status is not None:
        statement = statement.where(Character.status == status)
    if creator_id is not None:
        statement = statement.where(Character.creator_id == creator_id)
    
    # Apply search filter
    if search and search.strip():
        search_term = f"%{search.strip()}%"
        statement = statement.where(
            or_(
                Character.name.ilike(search_term),
                Character.description.ilike(search_term),
                Character.category.ilike(search_term),
                Character.tags.ilike(search_term),
                Character.personality_traits.ilike(search_term),
                Character.scenario.ilike(search_term)
            )
        )
    
    # Apply category filter
    if category and category.strip() and category.lower() != "all":
        statement = statement.where(Character.category.ilike(f"%{category.strip()}%"))
    
    # Apply sorting
    if sort_by == "most_popular":
        statement = statement.order_by(desc(Character.popularity_score), desc(Character.created_at))
    elif sort_by == "most_recent":
        statement = statement.order_by(desc(Character.created_at))
    elif sort_by == "highest_rated":
        # For now, use popularity_score as rating, can be changed later
        statement = statement.order_by(desc(Character.popularity_score))
    elif sort_by == "name_asc":
        statement = statement.order_by(asc(Character.name))
    elif sort_by == "name_desc":
        statement = statement.order_by(desc(Character.name))
    elif sort_by == "oldest":
        statement = statement.order_by(asc(Character.created_at))
    else:
        # Default to most popular
        statement = statement.order_by(desc(Character.popularity_score), desc(Character.created_at))
    
    # Apply pagination
    statement = statement.offset(skip).limit(limit)
    
    characters = session.exec(statement).all()
    return characters


def get_characters_count(
    *,
    session: Session,
    status: CharacterStatus | None = None,
    creator_id: uuid.UUID | None = None,
    search: str | None = None,
    category: str | None = None,
) -> int:
    """Gets the count of characters with optional filters and search."""
    statement = select(func.count()).select_from(Character)
    
    # Apply filters
    if status is not None:
        statement = statement.where(Character.status == status)
    if creator_id is not None:
        statement = statement.where(Character.creator_id == creator_id)
    
    # Apply search filter
    if search and search.strip():
        search_term = f"%{search.strip()}%"
        statement = statement.where(
            or_(
                Character.name.ilike(search_term),
                Character.description.ilike(search_term),
                Character.category.ilike(search_term),
                Character.tags.ilike(search_term),
                Character.personality_traits.ilike(search_term),
                Character.scenario.ilike(search_term)
            )
        )
    
    # Apply category filter
    if category and category.strip() and category.lower() != "all":
        statement = statement.where(Character.category.ilike(f"%{category.strip()}%"))

    count = session.exec(statement).one()
    return count


def get_available_categories(*, session: Session, status: CharacterStatus | None = None) -> list[str]:
    """Gets list of available categories from existing characters."""
    statement = select(Character.category).distinct()
    
    if status is not None:
        statement = statement.where(Character.status == status)
    
    # Filter out null categories
    statement = statement.where(Character.category.is_not(None))
    statement = statement.where(Character.category != "")
    
    categories = session.exec(statement).all()
    # Remove None values and empty strings, sort alphabetically
    return sorted([cat for cat in categories if cat and cat.strip()])


def update_character(
    *, session: Session, db_character: Character, character_in: CharacterUpdate
) -> Character:
    """Updates an existing character."""
    update_data = character_in.model_dump(exclude_unset=True)
    db_character.sqlmodel_update(update_data)
    session.add(db_character)
    session.commit()
    session.refresh(db_character)
    return db_character


def update_character_by_user(
    *, session: Session, db_character: Character, character_in: CharacterUpdateUser, user_id: uuid.UUID
) -> Character:
    """Updates a character by its owner (user). Includes ownership verification."""
    if db_character.creator_id != user_id:
        raise ValueError("User does not have permission to update this character")
    
    # Convert user update schema to admin update schema
    character_update = CharacterUpdate(**character_in.model_dump(exclude_unset=True))
    return update_character(session=session, db_character=db_character, character_in=character_update)


def delete_character(*, session: Session, db_character: Character) -> None:
    """Deletes a character."""
    session.delete(db_character)
    session.commit() 