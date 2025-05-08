#!/usr/bin/env python3
"""
WebSocket Chat Client for Testing Imacall Conversations

This script provides a simple command-line interface to test the WebSocket-based 
chat functionality in the Imacall backend. It allows you to:

1. Login to get an access token
2. List available conversations
3. Connect to a conversation and chat with an AI character

Usage:
    python websocket_client.py --url https://your-backend-url.com

Requirements:
    pip install websockets httpx questionary colorama
"""

import json
import asyncio
import argparse
import sys
import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime

import websockets
import httpx
import questionary
from colorama import Fore, Style, init as colorama_init

# Initialize colorama for cross-platform colored output
colorama_init()

class ImacallClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.api_url = f"{self.base_url}/api/v1"
        self.token = None
        self.user_id = None
        self.http_client = httpx.AsyncClient(base_url=self.api_url, timeout=30.0)
    
    async def login(self, email: str, password: str) -> bool:
        """Login and get an access token"""
        try:
            login_data = {
                "username": email,  # OAuth2 form field is "username" even though it's an email
                "password": password
            }
            response = await self.http_client.post(
                "/login/access-token", 
                data=login_data
            )
            
            if response.status_code == 200:
                data = response.json()
                self.token = data["access_token"]
                # Get user info to have user_id
                me_response = await self.http_client.get(
                    "/users/me",
                    headers={"Authorization": f"Bearer {self.token}"}
                )
                if me_response.status_code == 200:
                    user_data = me_response.json()
                    self.user_id = user_data["id"]
                    print(f"{Fore.GREEN}Logged in as {user_data['email']} (User ID: {self.user_id}){Style.RESET_ALL}")
                    return True
            
            print(f"{Fore.RED}Login failed: {response.status_code} - {response.text}{Style.RESET_ALL}")
            return False
        except Exception as e:
            print(f"{Fore.RED}Error during login: {e}{Style.RESET_ALL}")
            return False
    
    async def list_conversations(self) -> List[Dict[str, Any]]:
        """Fetch user's conversations"""
        if not self.token:
            print(f"{Fore.RED}Not logged in. Please login first.{Style.RESET_ALL}")
            return []
        
        try:
            response = await self.http_client.get(
                "/conversations/",
                headers={"Authorization": f"Bearer {self.token}"}
            )
            
            if response.status_code == 200:
                data = response.json()
                conversations = data.get("data", [])
                print(f"{Fore.GREEN}Found {len(conversations)} conversations{Style.RESET_ALL}")
                return conversations
            
            print(f"{Fore.RED}Failed to fetch conversations: {response.status_code} - {response.text}{Style.RESET_ALL}")
            return []
        except Exception as e:
            print(f"{Fore.RED}Error fetching conversations: {e}{Style.RESET_ALL}")
            return []

    async def list_characters(self) -> List[Dict[str, Any]]:
        """Fetch available characters for starting a new conversation"""
        try:
            response = await self.http_client.get("/characters/")
            
            if response.status_code == 200:
                data = response.json()
                characters = data.get("data", [])
                print(f"{Fore.GREEN}Found {len(characters)} available characters{Style.RESET_ALL}")
                return characters
            
            print(f"{Fore.RED}Failed to fetch characters: {response.status_code} - {response.text}{Style.RESET_ALL}")
            return []
        except Exception as e:
            print(f"{Fore.RED}Error fetching characters: {e}{Style.RESET_ALL}")
            return []

    async def start_conversation(self, character_id: str) -> Optional[Dict[str, Any]]:
        """Start a new conversation with a character"""
        if not self.token:
            print(f"{Fore.RED}Not logged in. Please login first.{Style.RESET_ALL}")
            return None
        
        try:
            response = await self.http_client.post(
                "/conversations/",
                json={"character_id": character_id},
                headers={"Authorization": f"Bearer {self.token}"}
            )
            
            if response.status_code == 201:
                conversation = response.json()
                print(f"{Fore.GREEN}Started conversation with ID: {conversation['id']}{Style.RESET_ALL}")
                return conversation
            
            print(f"{Fore.RED}Failed to start conversation: {response.status_code} - {response.text}{Style.RESET_ALL}")
            return None
        except Exception as e:
            print(f"{Fore.RED}Error starting conversation: {e}{Style.RESET_ALL}")
            return None

    async def chat_with_websocket(self, conversation_id: str):
        """Start a WebSocket chat session with the given conversation"""
        if not self.token:
            print(f"{Fore.RED}Not logged in. Please login first.{Style.RESET_ALL}")
            return
        
        ws_url = f"{self.base_url.replace('http', 'ws')}/api/v1/conversations/ws/{conversation_id}?token={self.token}"
        
        try:
            async with websockets.connect(ws_url) as websocket:
                print(f"{Fore.GREEN}Connected to conversation {conversation_id}{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}Type your messages and press Enter. Type 'exit' to quit.{Style.RESET_ALL}")
                
                # Start a task to receive messages
                receiver_task = asyncio.create_task(self._receive_messages(websocket))
                
                try:
                    while True:
                        # Read message from user
                        message = await asyncio.get_event_loop().run_in_executor(
                            None, lambda: input(f"{Fore.CYAN}You: {Style.RESET_ALL}")
                        )
                        
                        if message.lower() == 'exit':
                            break
                        
                        # Send message to server
                        await websocket.send(json.dumps({
                            "type": "text",
                            "content": message
                        }))
                finally:
                    # Cancel receiver task when done
                    receiver_task.cancel()
                    try:
                        await receiver_task
                    except asyncio.CancelledError:
                        pass
                    
        except Exception as e:
            print(f"{Fore.RED}WebSocket error: {e}{Style.RESET_ALL}")
    
    async def _receive_messages(self, websocket):
        """Background task to receive messages from the WebSocket"""
        try:
            while True:
                message = await websocket.recv()
                data = json.loads(message)
                msg_type = data.get("type", "")
                
                if msg_type == "message":
                    msg_data = data.get("data", {})
                    sender = msg_data.get("sender", "unknown")
                    content = msg_data.get("content", "")
                    
                    if sender == "ai":
                        timestamp = datetime.fromisoformat(msg_data.get("timestamp", "")).strftime("%H:%M:%S")
                        print(f"{Fore.GREEN}[{timestamp}] AI: {content}{Style.RESET_ALL}")
                
                elif msg_type == "typing":
                    is_typing = data.get("data", {}).get("is_typing", False)
                    if is_typing:
                        print(f"{Fore.YELLOW}AI is typing...{Style.RESET_ALL}", end="\r")
                    else:
                        print(" " * 20, end="\r")  # Clear the typing indicator
                
                elif msg_type == "error":
                    error_msg = data.get("data", {}).get("message", "Unknown error")
                    print(f"{Fore.RED}Error: {error_msg}{Style.RESET_ALL}")
        
        except websockets.exceptions.ConnectionClosed:
            print(f"{Fore.RED}WebSocket connection closed{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}Error receiving messages: {e}{Style.RESET_ALL}")

    async def close(self):
        """Close the HTTP client"""
        await self.http_client.aclose()

async def main():
    parser = argparse.ArgumentParser(description="WebSocket Chat Client for Imacall API")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL of the Imacall backend")
    args = parser.parse_args()
    
    client = ImacallClient(args.url)
    
    try:
        # Login flow
        email = questionary.text("Email:").ask()
        if not email:
            return
        
        password = questionary.password("Password:").ask()
        if not password:
            return
        
        login_success = await client.login(email, password)
        if not login_success:
            return
        
        while True:
            # Main menu
            choice = questionary.select(
                "What would you like to do?",
                choices=[
                    "Start a new conversation",
                    "Continue an existing conversation",
                    "Exit"
                ]
            ).ask()
            
            if choice == "Exit":
                break
            
            elif choice == "Start a new conversation":
                characters = await client.list_characters()
                if not characters:
                    print(f"{Fore.YELLOW}No characters available. Try again later.{Style.RESET_ALL}")
                    continue
                
                char_choices = [
                    {"name": f"{char['name']} - {char.get('description', 'No description')[:50]}...", "value": char["id"]}
                    for char in characters
                ]
                
                selected_char = questionary.select(
                    "Select a character:",
                    choices=char_choices
                ).ask()
                
                if not selected_char:
                    continue
                
                conversation = await client.start_conversation(selected_char)
                if conversation:
                    await client.chat_with_websocket(conversation["id"])
            
            elif choice == "Continue an existing conversation":
                conversations = await client.list_conversations()
                if not conversations:
                    print(f"{Fore.YELLOW}No existing conversations found.{Style.RESET_ALL}")
                    continue
                
                conv_choices = [
                    {"name": f"Conversation with {conv.get('character_name', 'Unknown')} ({conv['id']})", "value": conv["id"]}
                    for conv in conversations
                ]
                
                selected_conv = questionary.select(
                    "Select a conversation:",
                    choices=conv_choices
                ).ask()
                
                if not selected_conv:
                    continue
                
                await client.chat_with_websocket(selected_conv)
    
    finally:
        await client.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0) 