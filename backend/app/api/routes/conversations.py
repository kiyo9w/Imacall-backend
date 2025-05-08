# Placeholder for conversation management routes 

import uuid
from typing import Any, List, Sequence, Dict, Optional
import logging
import asyncio
from datetime import datetime
import json

from fastapi import APIRouter, HTTPException, Depends, WebSocket, WebSocketDisconnect, Query, status
from sqlmodel import Session

from app.api.deps import SessionDep, CurrentUser
from app import crud
from app.models import (
    Conversation, ConversationCreate, ConversationPublic, ConversationsPublic,
    Message, MessageCreate, MessagePublic, MessagesPublic, MessageSender,
    CharacterStatus, Character, User
)
# Import AI service
from app.services import ai_service

router = APIRouter(prefix="/conversations", tags=["conversations"])
logger = logging.getLogger(__name__) # Add logger

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        # Store active connections by conversation_id and user_id
        self.active_connections: Dict[uuid.UUID, Dict[uuid.UUID, WebSocket]] = {}
        
    async def connect(self, websocket: WebSocket, conversation_id: uuid.UUID, user_id: uuid.UUID):
        await websocket.accept()
        
        # Initialize dict for conversation_id if it doesn't exist
        if conversation_id not in self.active_connections:
            self.active_connections[conversation_id] = {}
            
        # Store the WebSocket connection for this user in this conversation
        self.active_connections[conversation_id][user_id] = websocket
        logger.info(f"User {user_id} connected to conversation {conversation_id}")
        
    def disconnect(self, conversation_id: uuid.UUID, user_id: uuid.UUID):
        """Remove a WebSocket connection when it disconnects."""
        if conversation_id in self.active_connections:
            if user_id in self.active_connections[conversation_id]:
                del self.active_connections[conversation_id][user_id]
                logger.info(f"User {user_id} disconnected from conversation {conversation_id}")
            
            # Clean up empty conversation entries
            if not self.active_connections[conversation_id]:
                del self.active_connections[conversation_id]
    
    async def send_message(self, conversation_id: uuid.UUID, user_id: uuid.UUID, message: Dict[str, Any]):
        """Send a message to a specific user in a conversation."""
        if (conversation_id in self.active_connections and 
            user_id in self.active_connections[conversation_id]):
            websocket = self.active_connections[conversation_id][user_id]
            await websocket.send_json(message)
            return True
        return False
    
    async def broadcast_to_conversation(self, conversation_id: uuid.UUID, message: Dict[str, Any]):
        """Broadcast a message to all users in a conversation."""
        if conversation_id in self.active_connections:
            disconnected_users = []
            for user_id, websocket in self.active_connections[conversation_id].items():
                try:
                    await websocket.send_json(message)
                except Exception as e:
                    logger.error(f"Error sending to user {user_id}: {e}")
                    disconnected_users.append(user_id)
            
            # Clean up disconnected users
            for user_id in disconnected_users:
                self.disconnect(conversation_id, user_id)

# Create a connection manager instance
manager = ConnectionManager()

# Helper function to authenticate WebSocket connection
async def get_user_from_token(
    websocket: WebSocket,
    session: Session = Depends(SessionDep),
    token: str = Query(None)
) -> Optional[User]:
    """Authenticate WebSocket connection using token query parameter."""
    logger.info(f"WebSocket auth: Starting authentication process with token: {token[:10]}..." if token else "WebSocket auth: No token provided")
    
    if not token:
        logger.error("WebSocket auth failed: No token provided")
        return None
    
    import jwt
    from app.core import security
    from app.core.config import settings
    from app.models import TokenPayload
    from jwt.exceptions import InvalidTokenError
    from pydantic import ValidationError
    
    try:
        logger.info(f"WebSocket auth: Decoding token with SECRET_KEY")
        
        # Decode the token using the same method as in get_current_user
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
        
        logger.info(f"WebSocket auth: Token decoded successfully, user_id={token_data.sub}")
        
        # Get the user from database
        user = session.get(User, token_data.sub)
        if not user:
            logger.error(f"WebSocket auth failed: User {token_data.sub} not found in database")
            return None
            
        if not user.is_active:
            logger.error(f"WebSocket auth failed: User {user.id} is not active")
            return None
        
        logger.info(f"WebSocket auth successful: User {user.id} authenticated")    
        return user
    except InvalidTokenError as e:
        logger.error(f"WebSocket auth failed: JWT validation error: {str(e)}")
        return None
    except ValidationError as e:
        logger.error(f"WebSocket auth failed: Payload validation error: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"WebSocket auth failed: Unexpected error: {str(e)}", exc_info=True)
        return None

# WebSocket endpoint for conversation messages
@router.websocket("/ws/{conversation_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    conversation_id: uuid.UUID,
    session: Session = Depends(SessionDep),
    token: str = Query(None)
):
    """WebSocket endpoint for real-time messaging in a conversation."""
    logger.info(f"WebSocket connection attempt for conversation: {conversation_id}")
    
    await websocket.accept()
    
    # Authenticate the WebSocket connection
    user = await get_user_from_token(websocket, session, token)
    if not user:
        logger.error(f"WebSocket auth failed: Invalid or missing token for conversation {conversation_id}")
        await websocket.send_json({"type": "error", "data": {"message": "Authentication failed"}})
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    
    logger.info(f"WS: User {user.id} authenticated, checking conversation access")
    
    # Check if conversation exists and user has access
    conversation = crud.conversations.get_conversation(
        session=session, conversation_id=conversation_id
    )
    
    # Log detailed information about the access issue
    if not conversation:
        logger.error(f"WebSocket connection rejected: Conversation {conversation_id} not found")
        await websocket.send_json({"type": "error", "data": {"message": "Conversation not found"}})
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    
    # Convert UUIDs to strings for comparison
    user_id_str = str(user.id)
    conversation_user_id_str = str(conversation.user_id)
    
    logger.info(f"WS access check: User ID={user_id_str}, Conversation owner ID={conversation_user_id_str}")
    
    # Perform the ownership check
    if user_id_str != conversation_user_id_str:
        logger.error(f"WebSocket permission denied: User {user_id_str} attempted to access conversation {conversation_id} owned by {conversation_user_id_str}")
        await websocket.send_json({"type": "error", "data": {"message": "You don't have permission to access this conversation"}})
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    
    logger.info(f"WS: Access granted to user {user_id_str} for conversation {conversation_id}")
    
    # Accept connection and store it
    await manager.connect(websocket, conversation_id, user.id)
    logger.info(f"WebSocket connection established for user {user.id} on conversation {conversation_id}")
    
    # Send initial connection confirmation
    await websocket.send_json({
        "type": "connected",
        "data": {
            "message": "WebSocket connection established",
            "conversation_id": str(conversation_id)
        }
    })
    
    try:
        while True:
            # Wait for messages from the client
            data = await websocket.receive_json()
            logger.info(f"WS: Received message from user {user.id}: {data.get('type', 'unknown')}")
            
            # Handle different message types
            message_type = data.get("type", "text")
            
            if message_type == "text":
                # Handle text messages (chat)
                await handle_text_message(session, websocket, conversation, user, data, conversation_id)
            elif message_type == "voice_call_request":
                # Handle voice call initiation
                await handle_voice_call_request(session, websocket, conversation, user, data, conversation_id)
            elif message_type == "voice_call_end":
                # Handle voice call termination
                await handle_voice_call_end(session, websocket, conversation, user, data, conversation_id)
            elif message_type == "ping":
                # Simple ping to keep connection alive
                await websocket.send_json({"type": "pong", "timestamp": datetime.now().isoformat()})
            else:
                # Unknown message type
                logger.warning(f"WS: Unknown message type: {message_type}")
                await websocket.send_json({
                    "type": "error",
                    "data": {"message": f"Unknown message type: {message_type}"}
                })
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: User {user.id}, conversation {conversation_id}")
        manager.disconnect(conversation_id, user.id)
    except json.JSONDecodeError:
        logger.error(f"WebSocket error: Invalid JSON received from user {user.id}")
        await websocket.send_json({"type": "error", "data": {"message": "Invalid message format"}})
        manager.disconnect(conversation_id, user.id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        try:
            await websocket.send_json({"type": "error", "data": {"message": "Server error occurred"}})
        except:
            pass
        manager.disconnect(conversation_id, user.id)

# Handler for text messages
async def handle_text_message(
    session: Session, 
    websocket: WebSocket,
    conversation: Conversation,
    user: User,
    data: dict,
    conversation_id: uuid.UUID
):
    # Extract message content
    content = data.get("content", "").strip()
    if not content:
        logger.warning(f"WS: Empty message content received from user {user.id}")
        return
    
    logger.info(f"WS: Processing text message from user {user.id} in conversation {conversation_id}")
    
    try:
        # Create and save user message
        user_message = crud.conversations.create_message(
            session=session,
            message_create=MessageCreate(content=content),
            conversation_id=conversation_id,
            sender=MessageSender.USER
        )
        
        logger.info(f"WS: User message saved with ID {user_message.id}")
        
        # Send confirmation of received message
        user_message_data = {
            "type": "message",
            "data": {
                "id": str(user_message.id),
                "content": user_message.content,
                "conversation_id": str(user_message.conversation_id),
                "sender": user_message.sender,
                "timestamp": user_message.timestamp.isoformat()
            }
        }
        send_result = await manager.send_message(conversation_id, user.id, user_message_data)
        if not send_result:
            logger.warning(f"WS: Failed to confirm message receipt to user {user.id}")
        
        # Get conversation history for AI context
        logger.info(f"WS: Fetching message history for conversation {conversation_id}")
        history = crud.conversations.get_conversation_messages(
            session=session, conversation_id=conversation_id, limit=20
        )
        
        # Get character for AI response
        character = crud.characters.get_character(
            session=session, character_id=conversation.character_id
        )
        if not character:
            logger.error(f"WS: Character {conversation.character_id} not found for conversation {conversation_id}")
            error_msg = {
                "type": "error",
                "data": {"message": "Character not found"}
            }
            await manager.send_message(conversation_id, user.id, error_msg)
            return
        
        logger.info(f"WS: Using character {character.id} ({character.name}) for AI response")
        
        # Inform client that AI is generating a response
        typing_notification = {
            "type": "typing",
            "data": {"character_id": str(character.id), "is_typing": True}
        }
        await manager.send_message(conversation_id, user.id, typing_notification)
        
        try:
            # Process AI response in background to not block the WebSocket
            logger.info(f"WS: Getting AI response from service for user {user.id}")
            ai_response_content = await asyncio.to_thread(
                ai_service.get_ai_response,
                character=character,
                history=history
            )
            
            logger.info(f"WS: AI response generated: {ai_response_content[:50]}...")
            
            # Create and save AI message
            ai_message = crud.conversations.create_message(
                session=session,
                message_create=MessageCreate(content=ai_response_content),
                conversation_id=conversation_id,
                sender=MessageSender.AI
            )
            
            logger.info(f"WS: AI message saved with ID {ai_message.id}")
            
            # Update last interaction time
            crud.conversations.update_conversation_last_interaction(
                session=session, db_conversation=conversation
            )
            
            # Send AI response to user
            ai_message_data = {
                "type": "message",
                "data": {
                    "id": str(ai_message.id),
                    "content": ai_message.content,
                    "conversation_id": str(ai_message.conversation_id),
                    "sender": ai_message.sender,
                    "timestamp": ai_message.timestamp.isoformat()
                }
            }
            send_result = await manager.send_message(conversation_id, user.id, ai_message_data)
            if not send_result:
                logger.warning(f"WS: Failed to send AI response to user {user.id}")
            else:
                logger.info(f"WS: AI response sent successfully to user {user.id}")
            
            # Send typing stopped notification
            typing_stopped = {
                "type": "typing",
                "data": {"character_id": str(character.id), "is_typing": False}
            }
            await manager.send_message(conversation_id, user.id, typing_stopped)
            
        except Exception as e:
            logger.error(f"WS: Error generating AI response: {e}", exc_info=True)
            error_msg = {
                "type": "error",
                "data": {"message": "Failed to generate AI response"}
            }
            await manager.send_message(conversation_id, user.id, error_msg)
            
            # Make sure to stop typing indicator
            typing_stopped = {
                "type": "typing",
                "data": {"character_id": str(character.id), "is_typing": False}
            }
            await manager.send_message(conversation_id, user.id, typing_stopped)
    except Exception as e:
        logger.error(f"WS: Unexpected error in handle_text_message: {e}", exc_info=True)
        try:
            error_msg = {
                "type": "error",
                "data": {"message": "Server error while processing your message"}
            }
            await manager.send_message(conversation_id, user.id, error_msg)
        except Exception as send_error:
            logger.error(f"WS: Failed to send error message: {send_error}")

# Placeholder for voice call request handling
async def handle_voice_call_request(
    session: Session, 
    websocket: WebSocket,
    conversation: Conversation,
    user: User,
    data: dict,
    conversation_id: uuid.UUID
):
    """
    Handle a request to start a voice call with the character.
    This is a placeholder for future voice calling functionality.
    """
    # Get character info
    character = crud.characters.get_character(
        session=session, character_id=conversation.character_id
    )
    
    if not character:
        await websocket.send_json({
            "type": "voice_call_error",
            "data": {"message": "Character not found"}
        })
        return
    
    # TODO: Implement actual voice call setup logic
    # This would include:
    # 1. Setting up a media server session
    # 2. Getting voice synthesis ready for the character
    # 3. Setting up speech recognition for the user
    
    # For now, just acknowledge the request with a placeholder
    await websocket.send_json({
        "type": "voice_call_initiated",
        "data": {
            "call_id": str(uuid.uuid4()),
            "character_id": str(character.id),
            "character_name": character.name,
            "message": "Voice calling functionality coming soon"
        }
    })

# Placeholder for voice call end handling
async def handle_voice_call_end(
    session: Session, 
    websocket: WebSocket,
    conversation: Conversation,
    user: User,
    data: dict,
    conversation_id: uuid.UUID
):
    """
    Handle the end of a voice call.
    This is a placeholder for future voice calling functionality.
    """
    call_id = data.get("call_id")
    
    # TODO: Implement actual voice call teardown logic
    # This would include:
    # 1. Closing the media server session
    # 2. Saving a transcript if available
    # 3. Cleaning up resources
    
    # For now, just acknowledge the request
    await websocket.send_json({
        "type": "voice_call_ended",
        "data": {
            "call_id": call_id,
            "message": "Voice call ended"
        }
    })

# WebSocket endpoint for voice communication
@router.websocket("/ws/voice/{conversation_id}")
async def voice_websocket_endpoint(
    websocket: WebSocket,
    conversation_id: uuid.UUID,
    session: Session = Depends(SessionDep),
    token: str = Query(None)
):
    """
    Dedicated WebSocket endpoint for voice communication.
    This handles binary audio data streaming between the user and AI character.
    """
    # Authenticate the WebSocket connection
    user = await get_user_from_token(websocket, session, token)
    if not user:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    
    # Check if conversation exists and user has access
    conversation = crud.conversations.get_conversation(
        session=session, conversation_id=conversation_id
    )
    if not conversation or conversation.user_id != user.id:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    
    # Get character for voice
    character = crud.characters.get_character(
        session=session, character_id=conversation.character_id
    )
    if not character:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    
    # Accept the WebSocket connection
    await websocket.accept()
    
    # Send initial connection success message
    await websocket.send_json({
        "type": "voice_connection_established",
        "data": {
            "character_id": str(character.id),
            "character_name": character.name,
            "message": "Voice connection established"
        }
    })
    
    # Track active call status
    call_active = True
    
    try:
        while call_active:
            # Wait for message (could be control message or binary audio data)
            message = await websocket.receive()
            
            # Check message type (text for control messages, bytes for audio)
            if "text" in message:
                # Handle control messages
                try:
                    data = json.loads(message["text"])
                    msg_type = data.get("type")
                    
                    if msg_type == "voice_call_end":
                        # End the call
                        await websocket.send_json({
                            "type": "voice_call_ended",
                            "data": {"message": "Call ended"}
                        })
                        call_active = False
                    elif msg_type == "ping":
                        # Keep-alive ping
                        await websocket.send_json({"type": "pong"})
                    elif msg_type == "speech_config":
                        # Update speech config (speed, tone, etc.)
                        await websocket.send_json({
                            "type": "speech_config_updated",
                            "data": {"message": "Speech configuration updated"}
                        })
                except json.JSONDecodeError:
                    await websocket.send_json({
                        "type": "error",
                        "data": {"message": "Invalid JSON in control message"}
                    })
            
            elif "bytes" in message:
                # Handle binary audio data
                audio_data = message["bytes"]
                
                # TODO: Process audio input
                # 1. Convert speech to text
                # 2. Pass text to AI
                # 3. Get AI response
                # 4. Convert response to speech
                # 5. Send audio back to client
                
                # For now, echo a placeholder response
                await websocket.send_json({
                    "type": "transcription",
                    "data": {
                        "text": "[Speech would be transcribed here]",
                        "is_final": True
                    }
                })
                
                # Simulate AI processing time
                await asyncio.sleep(1)
                
                # Send a text response first (useful for UI to show while audio generates)
                await websocket.send_json({
                    "type": "ai_response",
                    "data": {
                        "text": "This is a placeholder response. Voice synthesis would convert this to speech.",
                        "character_id": str(character.id)
                    }
                })
                
                # Then indicate audio response would follow in a real implementation
                await websocket.send_json({
                    "type": "audio_response_ready",
                    "data": {"message": "Audio response placeholder"}
                })
                
    except WebSocketDisconnect:
        logger.info(f"Voice WebSocket disconnected for user {user.id}, conversation {conversation_id}")
    except Exception as e:
        logger.error(f"Voice WebSocket error: {e}", exc_info=True)
    finally:
        # Perform cleanup
        # In a real implementation, this would release any voice synthesis/recognition resources
        logger.info(f"Voice connection closed for user {user.id}, conversation {conversation_id}")

# Keep the existing REST endpoints for compatibility
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
        greeting_message = Message(
            content=character.greeting_message,
            conversation_id=conversation.id,
            sender=MessageSender.AI
        )
        session.add(greeting_message)
        session.commit() # Commit the message

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
    user_message = crud.conversations.create_message(
        session=session, 
        message_create=message_in,
        conversation_id=conversation_id, 
        sender=MessageSender.USER
    )

    # 2. Get conversation history (limit to recent messages for context)
    #    Adjust limit as needed for context window vs performance
    history = crud.conversations.get_conversation_messages(
        session=session, conversation_id=conversation_id, limit=20 # Example limit
    )

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
    ai_message = crud.conversations.create_message(
        session=session,
        message_create=MessageCreate(content=ai_response_content),
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