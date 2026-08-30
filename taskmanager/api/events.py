from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import WebSocket

from taskmanager.core.broker import RedisBroker

logger = logging.getLogger(__name__)


class WebSocketEventManager:
    """Manages active browser WebSocket clients and relays Redis events in real time."""

    def __init__(self, broker: RedisBroker):
        self.broker = broker
        self.active_connections: set[WebSocket] = set()
        self._listener_task: asyncio.Task[None] | None = None
        self._running = False

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self.active_connections.discard(websocket)

    async def broadcast(self, message: dict[str, Any]) -> None:
        """Sends a JSON message to all connected clients."""
        if not self.active_connections:
            return

        dead_connections: set[WebSocket] = set()
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                dead_connections.add(connection)

        for dead in dead_connections:
            self.active_connections.discard(dead)

    async def start_listener(self) -> None:
        """Subscribes to Redis Pub/Sub and relays events to connected WebSockets."""
        self._running = True
        self._listener_task = asyncio.create_task(self._listen_loop())

    async def stop_listener(self) -> None:
        self._running = False
        if self._listener_task and not self._listener_task.done():
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass

    async def _listen_loop(self) -> None:
        try:
            async for event in self.broker.subscribe_events():
                if not self._running:
                    break
                await self.broadcast(event)
        except asyncio.CancelledError:
            pass
        except Exception as err:
            logger.warning(f"WebSocket listener encountered error: {err}")
