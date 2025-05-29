import uuid
import datetime
from enum import Enum
from typing import List, Optional
from datetime import timezone
import re # Import re for parsing tags string
import json # Import json for safer parsing if possible

from pydantic import EmailStr, field_validator
from sqlmodel import Field, Relationship, SQLModel, Column, Text
from sqlalchemy import Column, String, UniqueConstraint


# Shared properties
class UserBase(SQLModel):
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    is_active: bool = True
    is_superuser: bool = False
    full_name: str | None = Field(default=None, max_length=255)


# Properties to receive via API on creation
class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=40)


class UserRegister(SQLModel):
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=40)
    full_name: str | None = Field(default=None, max_length=255)


# Properties to receive via API on update, all are optional
class UserUpdate(UserBase):
    email: EmailStr | None = Field(default=None, max_length=255)  # type: ignore
    password: str | None = Field(default=None, min_length=8, max_length=40)


class UserUpdateMe(SQLModel):
    full_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = Field(default=None, max_length=255)


class UpdatePassword(SQLModel):
    current_password: str = Field(min_length=8, max_length=40)
    new_password: str = Field(min_length=8, max_length=40)


# Database model, database table inferred from class name
class User(UserBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    hashed_password: str
    items: list["Item"] = Relationship(back_populates="owner", cascade_delete=True)
    created_characters: list["Character"] = Relationship(
        back_populates="creator", cascade_delete=True
    )
    conversations: list["Conversation"] = Relationship(
        back_populates="user", cascade_delete=True
    )


# Properties to return via API, id is always required
class UserPublic(UserBase):
    id: uuid.UUID


class UsersPublic(SQLModel):
    data: list[UserPublic]
    count: int


# Shared properties
class ItemBase(SQLModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=255)


# Properties to receive on item creation
class ItemCreate(ItemBase):
    pass


# Properties to receive on item update
class ItemUpdate(ItemBase):
    title: str | None = Field(default=None, min_length=1, max_length=255)  # type: ignore


# Database model, database table inferred from class name
class Item(ItemBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    owner_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE"
    )
    owner: User | None = Relationship(back_populates="items")


# Properties to return via API, id is always required
class ItemPublic(ItemBase):
    id: uuid.UUID
    owner_id: uuid.UUID


class ItemsPublic(SQLModel):
    data: list[ItemPublic]
    count: int


# Generic message
class Message(SQLModel):
    message: str


# JSON payload containing access token
class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"


# Contents of JWT token
class TokenPayload(SQLModel):
    sub: str | None = None


class NewPassword(SQLModel):
    token: str
    new_password: str = Field(min_length=8, max_length=40)


# Moved CharacterStatus definition here, before CharacterBase
class CharacterStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


# Shared properties
class CharacterBase(SQLModel):
    name: str = Field(index=True, max_length=100)
    description: str | None = Field(default=None, sa_column=Column(Text))
    image_url: str | None = None
    greeting_message: str | None = Field(default=None, sa_column=Column(Text))
    # V1 Detail Fields
    scenario: str | None = Field(default=None, sa_column=Column(Text))
    category: str | None = Field(default=None, index=True)
    language: str | None = Field(default=None, index=True)
    # Store as JSON/Text, handle serialization if needed - adjusted type hint and added validator
    tags: list[str] | str | None = Field(default=None, sa_column=Column(Text))
    voice_id: str | None = Field(default=None) # For TTS service integration
    # V3 Personality Fields
    personality_traits: str | None = Field(default=None, sa_column=Column(Text)) # E.g., "Curious, Witty, Cautious" or detailed description
    writing_style: str | None = Field(default=None, sa_column=Column(Text)) # E.g., "Formal, Concise, Uses emojis"
    background: str | None = Field(default=None, sa_column=Column(Text)) # Character's history
    knowledge_scope: str | None = Field(default=None, sa_column=Column(Text)) # What the character knows/doesn't know
    quirks: str | None = Field(default=None, sa_column=Column(Text)) # Unique habits or behaviors
    emotional_range: str | None = Field(default=None, sa_column=Column(Text)) # How the character expresses emotions
    # Popularity/Rating (V2) - Placeholder for now
    popularity_score: int = Field(default=0)
    # Admin fields
    status: CharacterStatus = Field(default=CharacterStatus.PENDING)
    is_public: bool = Field(default=True) # Whether it appears in public lists after approval
    is_featured: bool = Field(default=False)
    admin_feedback: str | None = Field(default=None, sa_column=Column(Text)) # Feedback on rejection/changes
    fallback_response: str | None = Field(default=None, sa_column=Column(Text)) # Fallback response for AI errors

    @field_validator("tags", mode="before")
    @classmethod
    def parse_tags(cls, v):
        if isinstance(v, str):
            # Handle PostgreSQL array string format '{tag1,tag2}' or JSON string '["tag1", "tag2"]' or simple comma-separated 'tag1,tag2'
            if v.startswith('{') and v.endswith('}'):
                # Attempt to parse PostgreSQL-style array string: {tag1,"tag 2",tag3}
                # This simple regex handles basic cases without escaped commas/quotes within tags
                tags = re.findall(r'[^",\s][^,"]*[^",\s]*', v.strip('{}'))
                # Strip quotes if present (handles "{'tag1','tag2'}" or '{"tag1","tag2"}')
                return [tag.strip('\'"') for tag in tags if tag]
            elif v.startswith('[') and v.endswith(']'):
                # Attempt to parse as JSON list
                try:
                    return json.loads(v)
                except json.JSONDecodeError:
                    # Fallback for malformed JSON - treat as single tag? or return empty?
                     return [v] # Or raise ValueError? For now, treat as single tag.
            else:
                 # Assume comma-separated string: "tag1, tag2, tag3"
                 return [tag.strip() for tag in v.split(',') if tag.strip()]
        elif isinstance(v, list):
            # Already a list, ensure elements are strings
            return [str(item) for item in v]
        # Handle None or other types gracefully
        return v


# Properties to receive via API on creation (user submission)
class CharacterCreate(CharacterBase):
    pass


# Properties to receive via API on update (admin only)
class CharacterUpdate(SQLModel):
    # Only include fields a user OR admin might update
    # Admin might update more via a separate schema if needed, but let's keep it simple for now
    name: str | None = Field(default=None, max_length=100) # Keep max_length for name
    description: str | None = None
    image_url: str | None = None
    greeting_message: str | None = None
    scenario: str | None = None
    category: str | None = None
    language: str | None = None
    tags: list[str] | None = None
    voice_id: str | None = None
    personality_traits: str | None = None
    writing_style: str | None = None
    background: str | None = None
    knowledge_scope: str | None = None
    quirks: str | None = None
    emotional_range: str | None = None
    # Admin-only updatable fields (could be in a CharacterUpdateAdmin schema)
    status: CharacterStatus | None = None
    is_public: bool | None = None
    is_featured: bool | None = None
    admin_feedback: str | None = None


# Database model
class Character(CharacterBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    creator_id: uuid.UUID = Field(foreign_key="user.id", index=True)
    created_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(timezone.utc), nullable=False
    )
    updated_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(timezone.utc),
        nullable=False,
        sa_column_kwargs={"onupdate": lambda: datetime.datetime.now(timezone.utc)}
    )

    creator: "User" = Relationship(back_populates="created_characters")
    conversations: List["Conversation"] = Relationship(back_populates="character")


# Properties to return via API
class CharacterPublic(CharacterBase):
    id: uuid.UUID
    creator_id: uuid.UUID
    # Exclude sensitive fields like admin_feedback from public view if needed
    # For now, exposing most V1/V3 fields seems okay for profile viewing
    # We might refine this later based on UX/privacy needs
    # Omitting admin_feedback for now
    admin_feedback: str | None = Field(default=None, exclude=True)
    fallback_response: str | None = Field(default=None, exclude=True) # Exclude fallback from public view


class CharactersPublic(SQLModel):
    data: list[CharacterPublic]
    count: int


# ---------------- Conversation Models ----------------


class ConversationBase(SQLModel):
    user_id: uuid.UUID = Field(foreign_key="user.id")
    character_id: uuid.UUID = Field(foreign_key="character.id")
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.now, nullable=False)
    last_interaction_at: datetime.datetime | None = Field(default=None, index=True) # For sorting conversations


class ConversationCreate(SQLModel):
    character_id: uuid.UUID


# Database model
class Conversation(ConversationBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id", nullable=False)
    character_id: uuid.UUID = Field(foreign_key="character.id", nullable=False)
    created_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(timezone.utc)
    )

    user: User = Relationship(back_populates="conversations")
    character: Character = Relationship(back_populates="conversations")
    messages: List["Message"] = Relationship(back_populates="conversation", cascade_delete=True)


class ConversationPublic(ConversationBase):
    id: uuid.UUID
    # Optional fields for frontend convenience
    character_name: str | None = None
    character_image_url: str | None = None


class ConversationsPublic(SQLModel):
    data: list[ConversationPublic]
    count: int


# ---------------- Message Models ----------------


class MessageSender(str, Enum):
    USER = "user"
    AI = "ai"


class MessageBase(SQLModel):
    content: str = Field(max_length=5000) # Increased length? Consider Text if needed.
    conversation_id: uuid.UUID = Field(foreign_key="conversation.id")


class MessageCreate(SQLModel):
    content: str = Field(max_length=5000)


# Database model
class Message(MessageBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    conversation_id: uuid.UUID = Field(foreign_key="conversation.id", nullable=False)
    sender: MessageSender
    timestamp: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(timezone.utc)
    )

    conversation: Conversation = Relationship(back_populates="messages")


class MessagePublic(MessageBase):
    id: uuid.UUID
    conversation_id: uuid.UUID
    sender: MessageSender
    timestamp: datetime.datetime


class MessagesPublic(SQLModel):
    data: list[MessagePublic]
    count: int


# ---------------- AI Provider Configuration Model ----------------

class AIProviderConfigBase(SQLModel):
    active_provider_name: str = Field(sa_column=Column(String, default="gemini", index=True))

class AIProviderConfig(AIProviderConfigBase, table=True):
    __tablename__ = "ai_provider_config" # Explicit table name
    id: int | None = Field(default=1, primary_key=True) # Keep it simple with a single row

    # Ensure only one row can exist with id=1
    __table_args__ = (UniqueConstraint('id'),)


# Public schema for AIProviderConfig (if needed, but likely not directly exposed)
class AIProviderConfigPublic(AIProviderConfigBase):
    pass
