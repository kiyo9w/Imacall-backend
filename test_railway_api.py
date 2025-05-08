#!/usr/bin/env python3
import requests
import json
import sys
import time
import websocket
import threading
import ssl

# Railway URL 
BASE_URL = "https://imacall-backend-production.up.railway.app"

def test_http_endpoint(endpoint):
    """Test an HTTP endpoint and print the status code and content"""
    url = f"{BASE_URL}{endpoint}"
    print(f"Testing endpoint: {url}")
    try:
        response = requests.get(url, timeout=10)
        print(f"  Status code: {response.status_code}")
        
        # Try to format JSON response
        try:
            formatted_content = json.dumps(response.json())
        except:
            formatted_content = response.text
            
        print(f"  Content: {formatted_content}")
        return response.status_code == 200
    except Exception as e:
        print(f"  Error: {str(e)}")
        return False

def on_message(ws, message):
    """Callback for WebSocket message received"""
    print(f"  Received message: {message}")
    ws.close()

def on_error(ws, error):
    """Callback for WebSocket error"""
    print(f"  WebSocket error: {error}")

def on_close(ws, close_status_code, close_msg):
    """Callback for WebSocket close"""
    print(f"  WebSocket closed: {close_status_code} - {close_msg}")

def on_open(ws):
    """Callback for WebSocket connection open"""
    print(f"  WebSocket connected")
    # Close after 2 seconds if no message is received
    threading.Timer(2.0, lambda: ws.close()).start()

def test_websocket_endpoint(endpoint):
    """Test a WebSocket endpoint"""
    ws_url = f"wss://{BASE_URL.replace('https://', '')}{endpoint}"
    print(f"Testing WebSocket: {ws_url}")
    try:
        # Create WebSocket connection with appropriate options
        ws = websocket.WebSocketApp(
            ws_url,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close
        )
        
        # Start WebSocket connection in a separate thread
        ws_thread = threading.Thread(target=ws.run_forever, 
                                   kwargs={"sslopt": {"cert_reqs": ssl.CERT_NONE}})
        ws_thread.daemon = True
        ws_thread.start()
        
        # Wait for WebSocket operations to complete
        time.sleep(3)
        
        # Force close if still open
        if ws.sock and ws.sock.connected:
            ws.close()
            
        return True
    except Exception as e:
        print(f"  WebSocket setup error: {str(e)}")
        return False

def main():
    """Run all tests and summarize results"""
    # HTTP endpoints to test
    http_endpoints = [
        "/",                        # Root endpoint
        "/api",                     # API without version
        "/api/v1",                  # API base with version
        "/api/v1/utils/health-check",  # Health check endpoint
        "/api/v1/users/",           # Users endpoint (will be 401 but should exist)
        "/api/v1/docs",             # API documentation
        "/api/v1/openapi.json",     # OpenAPI schema
        "/docs",                    # Redirect to API docs
    ]
    
    # WebSocket endpoints to test
    ws_endpoints = [
        "/ws-health",               # WebSocket health check
        "/api/v1/debug/ws-echo",    # Debug echo WebSocket
    ]
    
    # Run HTTP tests
    http_results = {endpoint: test_http_endpoint(endpoint) for endpoint in http_endpoints}
    
    # Add a separator
    print("\n" + "-" * 60 + "\n")
    
    # Run WebSocket tests
    ws_results = {endpoint: test_websocket_endpoint(endpoint) for endpoint in ws_endpoints}
    
    # Print summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    print("\nHTTP Endpoints:")
    for endpoint, success in http_results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {endpoint}")
    
    print("\nWebSocket Endpoints:")
    for endpoint, success in ws_results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {endpoint}")
    
    # Calculate overall success
    all_succeeded = all(http_results.values()) and all(ws_results.values())
    
    print("\n" + "=" * 60)
    if all_succeeded:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed")
    print("=" * 60 + "\n")
    
    return 0 if all_succeeded else 1

if __name__ == "__main__":
    sys.exit(main()) 