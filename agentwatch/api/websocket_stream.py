"""WebSocket integration for streaming events"""
from typing import Optional
from fastapi import WebSocket
from ..interceptors.base import TokenChunk, TokenStatus
import json

class StreamWebSocketManager:
    """Manages WebSocket connections for token streaming"""
    
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}
        
    async def connect(self, session_id: str, websocket: WebSocket):
        """Accept WebSocket connection"""
        await websocket.accept()
        self.active_connections[session_id] = websocket
        
    def disconnect(self, session_id: str):
        """Remove WebSocket connection"""
        if session_id in self.active_connections:
            del self.active_connections[session_id]
    
    async def broadcast_token(self, session_id: str, token: TokenChunk):
        """Broadcast token to WebSocket"""
        if session_id in self.active_connections:
            try:
                await self.active_connections[session_id].send_text(
                    json.dumps({
                        "type": "token",
                        "session_id": session_id,
                        "data": {
                            "content": token.content,
                            "index": token.index,
                            "status": token.status.value,
                            "status_reason": token.status_reason,
                            "is_tool_call": token.is_tool_call,
                            "timestamp": token.timestamp
                        }
                    })
                )
            except Exception:
                pass
    
    async def broadcast_status(self, session_id: str, status: str, message: str):
        """Broadcast status update"""
        if session_id in self.active_connections:
            try:
                await self.active_connections[session_id].send_text(
                    json.dumps({
                        "type": "status",
                        "session_id": session_id,
                        "status": status,
                        "message": message
                    })
                )
            except Exception:
                pass

# Singleton instance
stream_ws_manager = StreamWebSocketManager()