import logging
from fastapi import APIRouter, WebSocket

router = APIRouter(prefix="/debug", tags=["debug"])
logger = logging.getLogger(__name__)

@router.websocket("/ws-echo")
async def websocket_echo(websocket: WebSocket):
    """
    Simple WebSocket echo endpoint for debugging WebSocket connections.
    This endpoint accepts connections without authentication, making it
    easier to test if WebSockets work at all on Render.com.
    """
    logger.info(f"WS Echo: Connection attempted")
    logger.info(f"WS Echo: Headers: {websocket.headers}")
    
    try:
        await websocket.accept()
        logger.info(f"WS Echo: Connection accepted")
        
        # Send a welcome message
        await websocket.send_json({
            "type": "connected",
            "message": "WebSocket connection established to echo endpoint"
        })
        
        while True:
            # Echo any messages back to the client
            data = await websocket.receive_text()
            logger.info(f"WS Echo: Received message: {data}")
            await websocket.send_text(f"Echo: {data}")
            
    except Exception as e:
        logger.error(f"WS Echo: Error: {e}", exc_info=True)
        try:
            await websocket.close(code=1011)
        except:
            logger.error("WS Echo: Failed to close WebSocket") 