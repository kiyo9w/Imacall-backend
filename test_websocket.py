#!/usr/bin/env python3
import asyncio
import websockets
import json
import sys

async def test_websocket():
    # Get values from command line or use defaults
    conversation_id = sys.argv[1] if len(sys.argv) > 1 else "fa0ac6fd-3307-425e-9239-814b4f101584"
    token = sys.argv[2] if len(sys.argv) > 2 else "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NDc0MTI2MjUsInN1YiI6IjgwZDgyODk2LWU3ODItNDRlMi05ODBjLWQ3NmViN2M0YTViMCJ9.tEWTDLA8tetOQglvX5hiR7tVUt02FQhaCtK5g0SIfWs"
    
    # Try different auth methods with the /api/v1 prefix
    conversation_uris = [
        # Original with token in query param
        f"wss://imacall-backend.onrender.com/api/v1/conversations/ws/{conversation_id}?token={token}",
        
        # Try with Authorization header instead of query param
        {
            "uri": f"wss://imacall-backend.onrender.com/api/v1/conversations/ws/{conversation_id}",
            "headers": {"Authorization": f"Bearer {token}"}
        },
        
        # Try without /api/v1 prefix (for completeness)
        f"wss://imacall-backend.onrender.com/conversations/ws/{conversation_id}?token={token}"
    ]
    
    # Add the debug websocket endpoint tests
    debug_uris = [
        "wss://imacall-backend.onrender.com/api/v1/debug/ws-echo",
        "wss://imacall-backend.onrender.com/ws-health",
        "wss://imacall-backend.onrender.com/api/v1/ws-health",
    ]
    
    # First test the conversations endpoints
    print("\n=== TESTING CONVERSATION ENDPOINTS ===")
    for uri_data in conversation_uris:
        headers = {}
        if isinstance(uri_data, dict):
            uri = uri_data["uri"]
            headers = uri_data.get("headers", {})
        else:
            uri = uri_data
            
        print(f"\nTesting connection to: {uri}")
        print(f"Headers: {headers}")
        
        try:
            async with websockets.connect(uri, extra_headers=headers, ping_interval=None) as websocket:
                print(f"Connected successfully to {uri}")
                
                # Wait for connection confirmation or error response
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    print(f"Received: {response}")
                except asyncio.TimeoutError:
                    print("No initial response received (timeout)")
                
                # Send a test message
                test_message = {
                    "type": "text",
                    "content": "Hello, this is a test message"
                }
                await websocket.send(json.dumps(test_message))
                print(f"Sent: {test_message}")
                
                # Wait for response
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    print(f"Received response: {response}")
                except asyncio.TimeoutError:
                    print("No response received to test message (timeout)")
                
        except Exception as e:
            print(f"Connection failed: {e}")
    
    # Then test the debug endpoints
    print("\n=== TESTING DEBUG ENDPOINTS ===")
    for uri in debug_uris:
        print(f"\nTesting connection to: {uri}")
        try:
            async with websockets.connect(uri, ping_interval=None) as websocket:
                print(f"Connected successfully to {uri}")
                
                # Wait for connection confirmation or error response
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    print(f"Received: {response}")
                except asyncio.TimeoutError:
                    print("No initial response received (timeout)")
                
                # Send a test message
                test_message = "Hello, this is a debug test message"
                await websocket.send(test_message)
                print(f"Sent: {test_message}")
                
                # Wait for response
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    print(f"Received response: {response}")
                except asyncio.TimeoutError:
                    print("No response received to test message (timeout)")
                
        except Exception as e:
            print(f"Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_websocket())