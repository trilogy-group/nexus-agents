"""Event bus for publishing monitoring events via Redis Pub/Sub."""

import asyncio
import json
import logging
import os
import random
from typing import Optional, Dict, Any

import redis.asyncio as redis

from .models import MonitoringEvent


logger = logging.getLogger(__name__)


class EventBus:
    """Event bus for publishing monitoring events."""
    
    def __init__(self, redis_client: redis.Redis):
        """Initialize event bus with Redis client."""
        self.redis_client = redis_client
        
        # Configuration from environment
        self.enabled = os.getenv("NEXUS_MONITORING_ENABLED", "true").lower() == "true"
        self.events_channel = os.getenv("MONITORING_EVENTS_CHANNEL", "nexus:events")
        self.stats_channel = os.getenv("MONITORING_STATS_CHANNEL", "nexus:events:stats")
        self.project_channel_prefix = os.getenv("MONITORING_PROJECT_CHANNEL_PREFIX", "nexus:events:project:")
        self.max_event_size = int(os.getenv("MONITORING_MAX_EVENT_SIZE_BYTES", "8192"))
        
        # Retry configuration
        self.max_retries = 3
        self.base_delay = 0.1  # 100ms base delay
        self.max_delay = 1.0   # 1s max delay
        self.timeout = 0.2     # 200ms timeout for Redis operations
        
        logger.info(f"EventBus initialized - enabled: {self.enabled}, channel: {self.events_channel}")
    
    async def publish(self, event: MonitoringEvent, project_id: Optional[str] = None) -> bool:
        """Publish a monitoring event to Redis channels.
        
        Args:
            event: The monitoring event to publish
            project_id: Optional project ID for project-specific channel
            
        Returns:
            True if published successfully, False otherwise
        """
        if not self.enabled:
            return True  # No-op when disabled
        
        try:
            # Serialize event to JSON
            event_data = event.model_dump()
            
            # Truncate if too large
            event_json = json.dumps(event_data)
            if len(event_json.encode('utf-8')) > self.max_event_size:
                # Truncate meta field first
                if event_data.get('meta'):
                    event_data['meta'] = {"truncated": True, "original_size": len(event_json)}
                    event_json = json.dumps(event_data)
                
                # If still too large, truncate message and error
                if len(event_json.encode('utf-8')) > self.max_event_size:
                    if event_data.get('message'):
                        event_data['message'] = event_data['message'][:500] + "... [truncated]"
                    if event_data.get('error'):
                        event_data['error'] = event_data['error'][:500] + "... [truncated]"
                    event_json = json.dumps(event_data)
            
            # Publish to global channel
            success = await self._publish_with_retry(self.events_channel, event_json)
            
            # Publish to project-specific channel if project_id is provided
            if project_id and success:
                project_channel = f"{self.project_channel_prefix}{project_id}"
                await self._publish_with_retry(project_channel, event_json)
            
            # Publish stats events to stats channel
            if event.event_type in ["stats_snapshot", "queue_depth_update"]:
                await self._publish_with_retry(self.stats_channel, event_json)
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to publish monitoring event: {e}")
            return False
    
    async def _publish_with_retry(self, channel: str, message: str) -> bool:
        """Publish message to Redis channel with retry logic."""
        for attempt in range(self.max_retries + 1):
            try:
                # Use asyncio.wait_for for timeout
                await asyncio.wait_for(
                    self.redis_client.publish(channel, message),
                    timeout=self.timeout
                )
                return True
                
            except asyncio.TimeoutError:
                logger.warning(f"Redis publish timeout on attempt {attempt + 1}")
            except Exception as e:
                logger.warning(f"Redis publish error on attempt {attempt + 1}: {e}")
            
            # Exponential backoff with jitter
            if attempt < self.max_retries:
                delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                jitter = random.uniform(0, delay * 0.1)  # 10% jitter
                await asyncio.sleep(delay + jitter)
        
        logger.error(f"Failed to publish to {channel} after {self.max_retries + 1} attempts")
        return False
    
    async def publish_worker_event(self, event_type: str, worker_id: int, 
                                 current_task_id: Optional[str] = None,
                                 message: Optional[str] = None) -> bool:
        """Publish a worker-related event."""
        event = MonitoringEvent(
            event_type=event_type,
            worker_id=worker_id,
            task_id=current_task_id,
            message=message
        )
        return await self.publish(event)
    
    async def publish_task_event(self, event_type: str, task_id: str,
                               parent_task_id: Optional[str] = None,
                               project_id: Optional[str] = None,
                               task_type: Optional[str] = None,
                               worker_id: Optional[int] = None,
                               status: Optional[str] = None,
                               retry_count: Optional[int] = None,
                               duration_ms: Optional[int] = None,
                               error: Optional[str] = None,
                               meta: Optional[Dict[str, Any]] = None) -> bool:
        """Publish a task-related event."""
        event = MonitoringEvent(
            event_type=event_type,
            task_id=task_id,
            parent_task_id=parent_task_id,
            project_id=project_id,
            task_type=task_type,
            worker_id=worker_id,
            status=status,
            retry_count=retry_count,
            duration_ms=duration_ms,
            error=error,
            meta=meta
        )
        return await self.publish(event, project_id=project_id)
    
    async def publish_phase_event(self, event_type: str, phase: str,
                                parent_task_id: str,
                                project_id: Optional[str] = None,
                                counts: Optional[Dict[str, int]] = None,
                                message: Optional[str] = None) -> bool:
        """Publish a phase-related event."""
        event = MonitoringEvent(
            event_type=event_type,
            phase=phase,
            parent_task_id=parent_task_id,
            project_id=project_id,
            counts=counts,
            message=message
        )
        return await self.publish(event, project_id=project_id)
    
    async def publish_stats_snapshot(self, counts: Optional[Dict[str, int]] = None,
                                   queue_stats: Optional[Dict[str, int]] = None,
                                   workers_online: Optional[int] = None,
                                   parent_task_id: Optional[str] = None,
                                   project_id: Optional[str] = None) -> bool:
        """Publish a statistics snapshot event."""
        event = MonitoringEvent(
            event_type="stats_snapshot",
            parent_task_id=parent_task_id,
            project_id=project_id,
            counts=counts,
            queue=queue_stats,
            meta={"workers_online": workers_online} if workers_online is not None else None
        )
        return await self.publish(event, project_id=project_id)