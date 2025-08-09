"""WebSocket endpoint for real-time monitoring events."""

import asyncio
import json
import logging
import os
from typing import Optional, Set, List, Dict, Any
from contextlib import asynccontextmanager

import redis.asyncio as redis
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from fastapi.websockets import WebSocketState

from ..monitoring.models import MonitoringEvent, GlobalStats, QueueStats


logger = logging.getLogger(__name__)

router = APIRouter()


class MonitoringWebSocketManager:
    """Manages WebSocket connections for monitoring events."""
    
    def __init__(self, redis_client: redis.Redis):
        """Initialize WebSocket manager."""
        self.redis_client = redis_client
        self.active_connections: Set[WebSocket] = set()
        
        # Configuration
        self.events_channel = os.getenv("MONITORING_EVENTS_CHANNEL", "nexus:events")
        self.stats_channel = os.getenv("MONITORING_STATS_CHANNEL", "nexus:events:stats")
        self.project_channel_prefix = os.getenv("MONITORING_PROJECT_CHANNEL_PREFIX", "nexus:events:project:")
        self.ping_interval = 30  # seconds
        
        # Background tasks
        self._subscriber_task: Optional[asyncio.Task] = None
        self._ping_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def start(self):
        """Start the WebSocket manager background tasks."""
        if self._running:
            return
        
        self._running = True
        self._subscriber_task = asyncio.create_task(self._redis_subscriber())
        self._ping_task = asyncio.create_task(self._ping_clients())
        logger.info("MonitoringWebSocketManager started")
    
    async def stop(self):
        """Stop the WebSocket manager and clean up."""
        self._running = False
        
        if self._subscriber_task:
            self._subscriber_task.cancel()
            try:
                await self._subscriber_task
            except asyncio.CancelledError:
                pass
        
        if self._ping_task:
            self._ping_task.cancel()
            try:
                await self._ping_task
            except asyncio.CancelledError:
                pass
        
        # Close all connections
        for websocket in list(self.active_connections):
            await self.disconnect(websocket)
        
        logger.info("MonitoringWebSocketManager stopped")
    
    async def connect(self, websocket: WebSocket, 
                     project_id: Optional[str] = None,
                     task_id: Optional[str] = None,
                     event_types: Optional[List[str]] = None,
                     stats_only: bool = False):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        
        # Store connection with filters
        websocket.monitoring_filters = {
            "project_id": project_id,
            "task_id": task_id,
            "event_types": set(event_types) if event_types else None,
            "stats_only": stats_only
        }
        
        self.active_connections.add(websocket)
        logger.info(f"WebSocket connected with filters: {websocket.monitoring_filters}")
        
        # Send initial snapshot if available
        try:
            snapshot = await self._get_current_snapshot(project_id, task_id)
            if snapshot:
                await websocket.send_text(json.dumps(snapshot))
        except Exception as e:
            logger.warning(f"Failed to send initial snapshot: {e}")
    
    async def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        self.active_connections.discard(websocket)
        
        if websocket.client_state != WebSocketState.DISCONNECTED:
            try:
                await websocket.close()
            except Exception as e:
                logger.warning(f"Error closing WebSocket: {e}")
        
        logger.info("WebSocket disconnected")
    
    async def _redis_subscriber(self):
        """Subscribe to Redis channels and forward events to WebSocket clients."""
        try:
            pubsub = self.redis_client.pubsub()
            
            # Subscribe to global events and stats channels
            await pubsub.subscribe(self.events_channel, self.stats_channel)
            
            # Also subscribe to all project channels that have active connections
            # (For simplicity, we'll subscribe to the global channel and filter)
            
            logger.info(f"Subscribed to Redis channels: {self.events_channel}, {self.stats_channel}")
            
            async for message in pubsub.listen():
                if not self._running:
                    break
                
                if message["type"] == "message":
                    try:
                        event_data = json.loads(message["data"])
                        await self._broadcast_event(event_data)
                    except Exception as e:
                        logger.error(f"Error processing Redis message: {e}")
        
        except Exception as e:
            logger.error(f"Redis subscriber error: {e}")
        finally:
            try:
                await pubsub.unsubscribe()
                await pubsub.close()
            except Exception as e:
                logger.warning(f"Error closing Redis pubsub: {e}")
    
    async def _broadcast_event(self, event_data: Dict[str, Any]):
        """Broadcast event to all matching WebSocket connections."""
        if not self.active_connections:
            return
        
        # Create list of connections to avoid modification during iteration
        connections = list(self.active_connections)
        
        for websocket in connections:
            try:
                # Check if connection is still valid
                if websocket.client_state == WebSocketState.DISCONNECTED:
                    self.active_connections.discard(websocket)
                    continue
                
                # Apply filters
                if not self._event_matches_filters(event_data, websocket.monitoring_filters):
                    continue
                
                # Send event
                await websocket.send_text(json.dumps(event_data))
                
            except Exception as e:
                logger.warning(f"Error sending event to WebSocket: {e}")
                # Remove failed connection
                self.active_connections.discard(websocket)
    
    def _event_matches_filters(self, event_data: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """Check if event matches WebSocket filters."""
        # Stats only filter
        if filters.get("stats_only") and event_data.get("event_type") not in ["stats_snapshot", "queue_depth_update"]:
            return False
        
        # Project filter
        if filters.get("project_id") and event_data.get("project_id") != filters["project_id"]:
            return False
        
        # Task filter
        if filters.get("task_id") and event_data.get("parent_task_id") != filters["task_id"]:
            return False
        
        # Event type filter
        if filters.get("event_types") and event_data.get("event_type") not in filters["event_types"]:
            return False
        
        return True
    
    async def _ping_clients(self):
        """Send periodic pings to WebSocket clients."""
        while self._running:
            try:
                await asyncio.sleep(self.ping_interval)
                
                if not self.active_connections:
                    continue
                
                # Send ping to all connections
                connections = list(self.active_connections)
                for websocket in connections:
                    try:
                        if websocket.client_state == WebSocketState.CONNECTED:
                            await websocket.ping()
                        else:
                            self.active_connections.discard(websocket)
                    except Exception as e:
                        logger.warning(f"Error pinging WebSocket: {e}")
                        self.active_connections.discard(websocket)
            
            except Exception as e:
                logger.error(f"Error in ping task: {e}")
    
    async def _get_current_snapshot(self, project_id: Optional[str] = None, 
                                  task_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get current system snapshot for initial WebSocket data."""
        try:
            # Get queue depths
            queue_stats = {}
            for priority in ["high_priority", "normal_priority", "low_priority"]:
                queue_key = f"nexus:tasks:{priority}"
                depth = await self.redis_client.llen(queue_key)
                queue_stats[priority] = depth
            
            # Get worker heartbeats (count active workers)
            heartbeat_pattern = "nexus:worker:heartbeat:*"
            worker_keys = await self.redis_client.keys(heartbeat_pattern)
            workers_online = len(worker_keys)
            
            # Create snapshot event
            snapshot = {
                "event_id": "snapshot",
                "ts": MonitoringEvent().ts,
                "event_type": "stats_snapshot",
                "project_id": project_id,
                "parent_task_id": task_id,
                "queue": queue_stats,
                "meta": {
                    "workers_online": workers_online,
                    "snapshot": True
                }
            }
            
            return snapshot
            
        except Exception as e:
            logger.error(f"Error getting current snapshot: {e}")
            return None


# Global WebSocket manager instance
ws_manager: Optional[MonitoringWebSocketManager] = None


async def get_ws_manager() -> MonitoringWebSocketManager:
    """Get the global WebSocket manager instance."""
    global ws_manager
    if ws_manager is None:
        # Import here to avoid circular imports
        from ...api import redis_client
        if redis_client is None:
            raise RuntimeError("Redis client not initialized")
        ws_manager = MonitoringWebSocketManager(redis_client)
        await ws_manager.start()
    return ws_manager


@router.websocket("/ws/monitor")
async def websocket_monitor(
    websocket: WebSocket,
    project_id: Optional[str] = Query(None, description="Filter events by project ID"),
    task_id: Optional[str] = Query(None, description="Filter events by parent task ID"),
    types: Optional[str] = Query(None, description="Comma-separated list of event types to include"),
    stats_only: bool = Query(False, description="Only receive stats events")
):
    """WebSocket endpoint for real-time monitoring events.
    
    Query parameters:
    - project_id: Filter events by project ID
    - task_id: Filter events by parent research task ID
    - types: Comma-separated event types (e.g., "task_started,task_completed")
    - stats_only: Only receive stats_snapshot and queue_depth_update events
    """
    manager = await get_ws_manager()
    
    # Parse event types filter
    event_types = None
    if types:
        event_types = [t.strip() for t in types.split(",") if t.strip()]
    
    try:
        await manager.connect(
            websocket=websocket,
            project_id=project_id,
            task_id=task_id,
            event_types=event_types,
            stats_only=stats_only
        )
        
        # Keep connection alive and handle client messages
        while True:
            try:
                # Wait for client messages (mostly for connection keep-alive)
                message = await websocket.receive_text()
                
                # Handle client commands if needed
                if message == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
                
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                break
    
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
    finally:
        await manager.disconnect(websocket)


@router.get("/monitor/snapshot")
async def get_monitoring_snapshot(
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    task_id: Optional[str] = Query(None, description="Filter by parent task ID")
):
    """Get current monitoring snapshot (fallback for WebSocket failures)."""
    try:
        manager = await get_ws_manager()
        snapshot = await manager._get_current_snapshot(project_id, task_id)
        
        if snapshot:
            return snapshot
        else:
            return {
                "event_type": "stats_snapshot",
                "queue": {"high_priority": 0, "normal_priority": 0, "low_priority": 0},
                "meta": {"workers_online": 0, "snapshot": True, "error": "Unable to fetch current stats"}
            }
    
    except Exception as e:
        logger.error(f"Error getting monitoring snapshot: {e}")
        return {
            "event_type": "error",
            "error": f"Failed to get snapshot: {str(e)}"
        }