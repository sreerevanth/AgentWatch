"""WebSocket integration for streaming events"""

import json
import logging
from typing import Optional

from fastapi import WebSocket

from ..interceptors.base import TokenChunk

logger = logging.getLogger(__name__)


class StreamWebSocketManager:
    """Manages WebSocket connections for token streaming"""

    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, session_id: str, websocket: WebSocket):
        """Accept WebSocket connection"""
        await websocket.accept()
        self.active_connections[session_id] = websocket
        logger.info(f"WebSocket connected for session: {session_id}")

    def disconnect(self, session_id: str):
        """Remove WebSocket connection"""
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            logger.info(f"WebSocket disconnected for session: {session_id}")

    async def broadcast_token(self, session_id: str, token: TokenChunk):
        """Broadcast token to WebSocket"""
        if session_id not in self.active_connections:
            return

        websocket = self.active_connections[session_id]
        try:
            await websocket.send_text(
                json.dumps(
                    {
                        "type": "token",
                        "session_id": session_id,
                        "data": {
                            "content": token.content,
                            "index": token.index,
                            "status": token.status.value,
                            "status_reason": token.status_reason,
                            "is_tool_call": token.is_tool_call,
                            "timestamp": token.timestamp,
                        },
                    }
                )
            )
        except Exception as e:
            # Remove dead connection instead of just passing
            logger.warning(f"WebSocket send failed for session {session_id}: {e}")
            self.disconnect(session_id)

    async def broadcast_status(self, session_id: str, status: str, message: str):
        """Broadcast status update"""
        if session_id not in self.active_connections:
            return

        websocket = self.active_connections[session_id]
        try:
            await websocket.send_text(
                json.dumps(
                    {
                        "type": "status",
                        "session_id": session_id,
                        "status": status,
                        "message": message,
                    }
                )
            )
        except Exception as e:
            # Remove dead connection instead of just passing
            logger.warning(f"WebSocket status send failed for session {session_id}: {e}")
            self.disconnect(session_id)

    async def broadcast_blocked(self, session_id: str, reason: str, token_index: int):
        """Broadcast blocked event"""
        if session_id not in self.active_connections:
            return

        websocket = self.active_connections[session_id]
        try:
            await websocket.send_text(
                json.dumps(
                    {
                        "type": "blocked",
                        "session_id": session_id,
                        "data": {
                            "reason": reason,
                            "token_index": token_index,
                            "timestamp": self._get_timestamp(),
                        },
                    }
                )
            )
        except Exception as e:
            logger.warning(f"WebSocket blocked send failed for session {session_id}: {e}")
            self.disconnect(session_id)

    async def broadcast_error(self, session_id: str, error: str):
        """Broadcast error event"""
        if session_id not in self.active_connections:
            return

        websocket = self.active_connections[session_id]
        try:
            await websocket.send_text(
                json.dumps(
                    {
                        "type": "error",
                        "session_id": session_id,
                        "data": {
                            "error": error,
                            "timestamp": self._get_timestamp(),
                        },
                    }
                )
            )
        except Exception as e:
            logger.warning(f"WebSocket error send failed for session {session_id}: {e}")
            self.disconnect(session_id)

    def get_connection_count(self) -> int:
        """Get number of active connections"""
        return len(self.active_connections)

    def get_active_sessions(self) -> list[str]:
        """Get list of active session IDs"""
        return list(self.active_connections.keys())

    def is_connected(self, session_id: str) -> bool:
        """Check if session is connected"""
        return session_id in self.active_connections

    def _get_timestamp(self) -> str:
        """Get current timestamp as ISO string"""
        import datetime
        return datetime.datetime.now().isoformat()


# Singleton instance
stream_ws_manager = StreamWebSocketManager()