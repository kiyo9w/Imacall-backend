# Placeholder for conversation management routes 

import uuid
from typing import Any, List, Sequence
import logging # Add logging

from fastapi import APIRouter, HTTPException, Depends, WebSocket, WebSocketDisconnect
from sqlmodel import Session

from app.api.deps import SessionDep, CurrentUser
from app import crud
from app.models import (
    Conversation, ConversationCreate, ConversationPublic, ConversationsPublic,
    Message, MessageCreate, MessagePublic, MessagesPublic, MessageSender,
    CharacterStatus, Character # Import Character
)
# Import AI service
from app.services import ai_service

router = APIRouter(prefix="/conversations", tags=["conversations"])
logger = logging.getLogger(__name__) # Add logger


@router.post("/", response_model=ConversationPublic, status_code=201)
def start_conversation(
    *, session: SessionDep, current_user: CurrentUser, conversation_in: ConversationCreate
) -> Any:
    """
    Start a new conversation with an approved character.
    """
    # Check if character exists and is approved
    character = crud.characters.get_character(
        session=session, character_id=conversation_in.character_id
    )
    if not character or character.status != CharacterStatus.APPROVED:
        raise HTTPException(status_code=404, detail="Approved character not found")

    try:
        conversation = crud.conversations.create_conversation(
            session=session, conversation_create=conversation_in, user_id=current_user.id
        )
    except ValueError as e:
        # Catch potential errors from CRUD (like character not found again, just in case)
        raise HTTPException(status_code=404, detail=str(e))

    # Optionally: Add the character's greeting message as the first AI message
    if character.greeting_message:
        crud.conversations.create_message(
            session=session,
            message_create=MessageCreate(content=character.greeting_message),
            conversation_id=conversation.id,
            sender=MessageSender.AI
        )
        session.refresh(conversation) # Refresh to potentially load the new message relationship

    return conversation


@router.get("/", response_model=ConversationsPublic)
def list_my_conversations(
    session: SessionDep, current_user: CurrentUser, skip: int = 0, limit: int = 100
) -> Any:
    """
    Retrieve conversations for the current user.
    """
    count = crud.conversations.get_user_conversations_count(
        session=session, user_id=current_user.id
    )
    conversations = crud.conversations.get_user_conversations(
        session=session, user_id=current_user.id, skip=skip, limit=limit
    )
    return ConversationsPublic(data=conversations, count=count)


@router.get("/{conversation_id}/messages", response_model=MessagesPublic)
def get_conversation_messages_route(
    session: SessionDep, current_user: CurrentUser, conversation_id: uuid.UUID, skip: int = 0, limit: int = 100
) -> Any:
    """
    Retrieve messages for a specific conversation owned by the current user.
    """
    conversation = crud.conversations.get_conversation(
        session=session, conversation_id=conversation_id
    )
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if conversation.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view these messages")

    count = crud.conversations.get_conversation_messages_count(
        session=session, conversation_id=conversation_id
    )
    messages = crud.conversations.get_conversation_messages(
        session=session, conversation_id=conversation_id, skip=skip, limit=limit
    )
    return MessagesPublic(data=messages, count=count)


@router.post("/{conversation_id}/messages", response_model=MessagePublic)
def send_message(
    *, 
    session: SessionDep, 
    current_user: CurrentUser, 
    conversation_id: uuid.UUID, 
    message_in: MessageCreate
) -> Any:
    """
    Send a message from the user to the conversation.
    Gets an AI response using the configured AI service.
    """
    conversation = crud.conversations.get_conversation(
        session=session, conversation_id=conversation_id
    )
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if conversation.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized for this conversation")

    # 1. Save the user's message
    user_message = crud.messages.create_message(
        session=session, 
        message_in=message_in, 
        conversation_id=conversation_id, 
        sender=MessageSender.USER
    )

    # 2. Get conversation history (limit to recent messages for context)
    #    Adjust limit as needed for context window vs performance
    history = crud.messages.get_messages_for_conversation(
        session=session, conversation_id=conversation_id, limit=20 # Example limit
    )
    # Ensure history includes the new user message
    # history.append(user_message) # crud already returns latest including user_message? check crud impl.
    # Let's assume crud.messages.get_messages_for_conversation gets the *latest* including the one just added.

    # 3. Call the AI service to get a response
    # Ensure the character object is loaded for personality details
    character = conversation.character # Assumes relationship is loaded or use crud
    if not character:
        # This shouldn't happen if conversation exists, but check
        char = crud.characters.get_character(session=session, character_id=conversation.character_id)
        if not char:
             raise HTTPException(status_code=404, detail="Character for conversation not found")
        character = char # Assign loaded character

    try:
        ai_response_content = ai_service.get_ai_response(character=character, history=history)
    except Exception as e:
        logger.error(f"AI service failed for conv {conversation_id}: {e}", exc_info=True)
        # Handle AI failure gracefully, maybe return the user message ID and an error indicator?
        # For now, raise internal server error
        raise HTTPException(status_code=500, detail="Failed to get AI response")

    # 4. Save the AI's response
    ai_message = crud.messages.create_message(
        session=session,
        # Create a MessageCreate object for the AI response
        message_in=MessageCreate(content=ai_response_content, conversation_id=conversation_id),
        conversation_id=conversation_id,
        sender=MessageSender.AI
    )

    # 5. Update conversation's last interaction time (optional but good for sorting)
    crud.conversations.update_conversation_last_interaction(session=session, db_conversation=conversation)

    # 6. Return the AI's message
    return ai_message


@router.delete("/{conversation_id}", status_code=204)
def delete_conversation_route(
    session: SessionDep, current_user: CurrentUser, conversation_id: uuid.UUID
) -> None:
    """
    Delete a conversation owned by the current user.
    """
    conversation = crud.conversations.get_conversation(
        session=session, conversation_id=conversation_id
    )
    if not conversation:
        # Idempotent delete: if not found, act as if deleted
        return None
    if conversation.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this conversation")

    crud.conversations.delete_conversation(session=session, db_conversation=conversation)
    return None # No content response 