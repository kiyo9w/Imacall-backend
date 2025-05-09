#!/usr/bin/env python3
"""
Polling-based Conversation Test

This script tests the HTTP polling-based conversation endpoints
which provide an alternative to WebSockets for basic messaging.
"""

import asyncio
import json
import argparse
import sys
import logging
import time
from datetime import datetime
from typing import Dict, Any, List

import httpx

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("poll-test")

class ImacallPollingClient:
    """Client to test the polling-based message exchange API"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.api_url = f"{self.base_url}/api/v1"
        self.token = None
        self.user_id = None
        self.client = httpx.Client(timeout=30)
        
    def login(self, email: str, password: str) -> bool:
        """Login to the API and get access token"""
        logger.info(f"Attempting login to {self.api_url}/login/access-token")
        
        try:
            # Login request
            response = self.client.post(
                f"{self.api_url}/login/access-token",
                data={
                    "username": email,
                    "password": password
                },
                headers={
                    "Content-Type": "application/x-www-form-urlencoded"
                }
            )
            response.raise_for_status()
            
            # Extract token
            data = response.json()
            self.token = data["access_token"]
            
            # Get user info
            me_response = self.client.get(
                f"{self.api_url}/users/me",
                headers={
                    "Authorization": f"Bearer {self.token}"
                }
            )
            me_response.raise_for_status()
            me_data = me_response.json()
            self.user_id = me_data["id"]
            
            logger.info(f"Login successful! User ID: {self.user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Login failed: {str(e)}")
            return False
    
    def list_characters(self) -> List[Dict[str, Any]]:
        """Get a list of available characters"""
        if not self.token:
            logger.error("Not logged in")
            return []
            
        logger.info(f"Fetching characters from {self.api_url}/characters/")
        
        try:
            response = self.client.get(
                f"{self.api_url}/characters/",
                headers={
                    "Authorization": f"Bearer {self.token}"
                }
            )
            response.raise_for_status()
            
            data = response.json()
            characters = data.get("data", [])
            logger.info(f"Found {len(characters)} characters")
            return characters
            
        except Exception as e:
            logger.error(f"Failed to fetch characters: {str(e)}")
            return []
    
    def start_conversation(self, character_id: str) -> Dict[str, Any]:
        """Start a new conversation with a character"""
        if not self.token:
            logger.error("Not logged in")
            return None
            
        logger.info(f"Starting conversation with character {character_id}")
        
        try:
            response = self.client.post(
                f"{self.api_url}/conversations/",
                json={
                    "character_id": character_id
                },
                headers={
                    "Authorization": f"Bearer {self.token}"
                }
            )
            response.raise_for_status()
            
            conversation = response.json()
            logger.info(f"Conversation started with ID: {conversation['id']}")
            return conversation
            
        except Exception as e:
            logger.error(f"Failed to start conversation: {str(e)}")
            return None
    
    def send_message_poll(self, conversation_id: str, message: str, last_message_id: str = None) -> Dict[str, Any]:
        """Send a message and get the AI response using the polling endpoint"""
        if not self.token:
            logger.error("Not logged in")
            return None
            
        logger.info(f"Sending message via polling API: {message[:30]}...")
        
        try:
            # Build the URL with optional last_message_id parameter
            url = f"{self.api_url}/conversations/{conversation_id}/messages/poll"
            if last_message_id:
                url += f"?last_message_id={last_message_id}"
                
            response = self.client.post(
                url,
                json={
                    "content": message
                },
                headers={
                    "Authorization": f"Bearer {self.token}"
                }
            )
            response.raise_for_status()
            
            ai_message = response.json()
            logger.info(f"Received AI response: {ai_message['content'][:50]}...")
            return ai_message
            
        except Exception as e:
            logger.error(f"Failed to send message: {str(e)}")
            return None
    
    def get_latest_messages(self, conversation_id: str, since_timestamp: str = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Get the latest messages in a conversation"""
        if not self.token:
            logger.error("Not logged in")
            return []
            
        logger.info(f"Fetching latest messages for conversation {conversation_id}")
        
        try:
            # Build URL with optional parameters
            url = f"{self.api_url}/conversations/{conversation_id}/messages/latest?limit={limit}"
            if since_timestamp:
                url += f"&since_timestamp={since_timestamp}"
                
            response = self.client.get(
                url,
                headers={
                    "Authorization": f"Bearer {self.token}"
                }
            )
            response.raise_for_status()
            
            data = response.json()
            messages = data.get("data", [])
            logger.info(f"Retrieved {len(messages)} messages")
            return messages
            
        except Exception as e:
            logger.error(f"Failed to fetch messages: {str(e)}")
            return []

def run_polling_test(base_url: str, email: str, password: str) -> bool:
    """Run a complete polling-based conversation test"""
    client = ImacallPollingClient(base_url)
    
    # 1. Login
    if not client.login(email, password):
        logger.error("Login failed")
        return False
    
    # 2. List characters and pick one
    characters = client.list_characters()
    if not characters:
        logger.error("No characters found")
        return False
        
    # Pick the first character
    character = characters[0]
    logger.info(f"Using character: {character['name']} (ID: {character['id']})")
    
    # 3. Start a conversation
    conversation = client.start_conversation(character['id'])
    if not conversation:
        logger.error("Failed to start conversation")
        return False
        
    conversation_id = conversation['id']
    logger.info(f"Created conversation with ID: {conversation_id}")
    
    # 4. Send messages and get responses using the polling API
    messages = [
        "Hello! This is a test of the polling API.",
        "Can you tell me about yourself?",
        "What's the weather like where you are?"
    ]
    
    last_ai_message_id = None
    last_timestamp = None
    
    for msg in messages:
        # Send message and get response
        ai_response = client.send_message_poll(conversation_id, msg, last_ai_message_id)
        if not ai_response:
            logger.error(f"Failed to send message: {msg}")
            continue
            
        last_ai_message_id = ai_response['id']
        
        # Simulate UI interaction delay
        time.sleep(2)
        
        # Record the current timestamp for later polling
        last_timestamp = datetime.utcnow().isoformat()
    
    # 5. Test the get_latest_messages endpoint (simulating polling)
    if last_timestamp:
        logger.info(f"Testing message polling since: {last_timestamp}")
        
        # Send one more message
        extra_msg = "This message should be fetched by polling!"
        client.send_message_poll(conversation_id, extra_msg)
        
        # Now poll for new messages
        new_messages = client.get_latest_messages(conversation_id, since_timestamp=last_timestamp)
        
        if new_messages:
            logger.info(f"Successfully polled {len(new_messages)} new messages!")
            for msg in new_messages:
                logger.info(f"  {msg['sender']}: {msg['content'][:50]}...")
            return True
        else:
            logger.warning("No new messages retrieved by polling")
            
    return True

def main():
    parser = argparse.ArgumentParser(description="Test HTTP polling-based conversation API")
    parser.add_argument("--url", default="https://imacall-backend-production.up.railway.app", 
                      help="Base URL of the backend")
    parser.add_argument("--email", required=True, help="Email for login")
    parser.add_argument("--password", required=True, help="Password for login")
    
    args = parser.parse_args()
    
    success = run_polling_test(args.url, args.email, args.password)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 