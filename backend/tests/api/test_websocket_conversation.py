import asyncio
import json
import uuid
import pytest
from httpx import AsyncClient
import websockets
from fastapi import status
from fastapi.testclient import TestClient

from app.main import app
from app.tests.utils.utils import get_superuser_token_headers, get_normal_user_token_headers
from app.tests.utils.user import create_random_user
from app.tests.utils.utils import random_email, random_lower_string
from app.models import CharacterStatus


@pytest.mark.asyncio
async def test_websocket_conversation_flow():
    """
    Test the WebSocket conversation flow:
    1. Create a user and get token
    2. Create a character
    3. Approve the character (as admin)
    4. Create a conversation
    5. Connect to WebSocket
    6. Send and receive messages
    """
    # Setup test client
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Create a user and get token
        email = random_email()
        password = random_lower_string()
        full_name = random_lower_string()
        
        user_data = {
            "email": email,
            "password": password,
            "full_name": full_name,
        }
        
        await client.post("/api/v1/users/signup", json=user_data)
        
        # Login to get token
        login_data = {
            "username": email,
            "password": password,
        }
        
        login_response = await client.post("/api/v1/login/access-token", data=login_data)
        assert login_response.status_code == status.HTTP_200_OK
        
        tokens = login_response.json()
        user_token = tokens["access_token"]
        
        # Get superuser token for character approval
        admin_headers = get_superuser_token_headers()
        
        # Create a test character
        character_data = {
            "name": "Test WebSocket Character",
            "description": "A character for testing WebSockets",
            "greeting_message": "Hello! I'm a test character."
        }
        
        character_response = await client.post(
            "/api/v1/characters/submit",
            json=character_data,
            headers={"Authorization": f"Bearer {user_token}"}
        )
        
        assert character_response.status_code == status.HTTP_200_OK
        character = character_response.json()
        character_id = character["id"]
        
        # Approve the character (as admin)
        approve_response = await client.patch(
            f"/api/v1/admin/characters/{character_id}/approve",
            headers=admin_headers
        )
        
        assert approve_response.status_code == status.HTTP_200_OK
        
        # Create a conversation with the character
        conversation_data = {
            "character_id": character_id
        }
        
        conversation_response = await client.post(
            "/api/v1/conversations/",
            json=conversation_data,
            headers={"Authorization": f"Bearer {user_token}"}
        )
        
        assert conversation_response.status_code == status.HTTP_201_CREATED
        conversation = conversation_response.json()
        conversation_id = conversation["id"]
        
        # Connect to WebSocket
        uri = f"ws://test/api/v1/conversations/ws/{conversation_id}?token={user_token}"
        
        async with websockets.connect(uri) as websocket:
            # Send a text message
            await websocket.send(json.dumps({
                "type": "text",
                "content": "Hello, this is a test message!"
            }))
            
            # Expect to receive the message back (confirmation)
            response = await websocket.recv()
            message_data = json.loads(response)
            
            assert message_data["type"] == "message"
            assert message_data["data"]["content"] == "Hello, this is a test message!"
            assert message_data["data"]["sender"] == "user"
            
            # Expect typing notification
            response = await websocket.recv()
            typing_data = json.loads(response)
            
            assert typing_data["type"] == "typing"
            assert typing_data["data"]["is_typing"] == True
            
            # Expect AI response
            response = await websocket.recv()
            ai_message = json.loads(response)
            
            assert ai_message["type"] == "message"
            assert ai_message["data"]["sender"] == "ai"
            assert len(ai_message["data"]["content"]) > 0
            
            # Expect typing stopped notification
            response = await websocket.recv()
            typing_stopped = json.loads(response)
            
            assert typing_stopped["type"] == "typing"
            assert typing_stopped["data"]["is_typing"] == False
            
            # Close the WebSocket connection
            await websocket.close()


@pytest.mark.asyncio
async def test_websocket_authentication():
    """Test that WebSocket connections require proper authentication"""
    # Invalid token
    uri = f"ws://test/api/v1/conversations/ws/{uuid.uuid4()}?token=invalid_token"
    
    try:
        async with websockets.connect(uri) as websocket:
            # Should not reach here - connection should be rejected
            assert False, "WebSocket connection should have been rejected"
    except websockets.exceptions.WebSocketException:
        # Expected behavior - connection rejected
        pass
    
    # Missing token
    uri = f"ws://test/api/v1/conversations/ws/{uuid.uuid4()}"
    
    try:
        async with websockets.connect(uri) as websocket:
            # Should not reach here - connection should be rejected
            assert False, "WebSocket connection should have been rejected"
    except websockets.exceptions.WebSocketException:
        # Expected behavior - connection rejected
        pass


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_websocket_conversation_flow()) 