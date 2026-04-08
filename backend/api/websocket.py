import asyncio
import json
from typing import Dict, Optional
from fastapi import WebSocket, WebSocketDisconnect
from core.event_bus import EventType, event_bus
from utils.logger import get_logger

logger = get_logger(__name__)


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, client_id: str) -> None:
        await websocket.accept()
        self._connections[client_id] = websocket
        logger.info(f"WebSocket connected: {client_id} (total: {len(self._connections)})")

    def disconnect(self, client_id: str) -> None:
        self._connections.pop(client_id, None)
        logger.info(f"WebSocket disconnected: {client_id} (remaining: {len(self._connections)})")

    async def send_to_client(self, client_id: str, message: dict) -> None:
        ws = self._connections.get(client_id)
        if ws:
            try:
                await ws.send_text(json.dumps(message))
            except Exception as exc:
                logger.warning(f"Failed to send to {client_id}: {exc}")
                self.disconnect(client_id)

    async def broadcast(self, message: dict) -> None:
        disconnected: list = []
        for client_id, ws in list(self._connections.items()):
            try:
                await ws.send_text(json.dumps(message))
            except Exception:
                disconnected.append(client_id)
        for cid in disconnected:
            self.disconnect(cid)

    def get_connected_clients(self) -> list:
        return list(self._connections.keys())


connection_manager = ConnectionManager()


def _make_event_handler(msg_type: str):
    async def handler(event_type, data) -> None:
        await connection_manager.broadcast({
            "type": msg_type,
            "event": event_type if isinstance(event_type, str) else event_type.value,
            "data": data,
        })
    return handler


def register_event_handlers() -> None:
    """Subscribe connection_manager to all event bus events and broadcast."""
    for event_type in EventType:
        event_bus.subscribe(event_type, _make_event_handler(event_type.value))


async def websocket_endpoint(websocket: WebSocket, client_id: str) -> None:
    await connection_manager.connect(websocket, client_id)
    try:
        # Send welcome message
        await connection_manager.send_to_client(client_id, {
            "type": "connected",
            "data": {"client_id": client_id, "message": "Connected to XandriXEngineer"},
        })
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                msg = json.loads(data)
                msg_type = msg.get("type", "")
                # Echo back a ping as pong
                if msg_type == "ping":
                    await connection_manager.send_to_client(client_id, {"type": "pong"})
            except asyncio.TimeoutError:
                # Send keepalive
                await connection_manager.send_to_client(client_id, {"type": "keepalive"})
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        connection_manager.disconnect(client_id)
    except Exception as exc:
        logger.error(f"WebSocket error for {client_id}: {exc}")
        connection_manager.disconnect(client_id)
