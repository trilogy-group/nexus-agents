"""Monitoring event models and types."""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


def utc_now() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(timezone.utc)


class MonitoringEventType(Enum):
    """Types of monitoring events."""
    # Worker events
    WORKER_STARTED = "worker_started"
    WORKER_HEARTBEAT = "worker_heartbeat"
    WORKER_STOPPED = "worker_stopped"
    
    # Task lifecycle events
    TASK_ENQUEUED = "task_enqueued"
    TASK_STARTED = "task_started"
    TASK_RETRY = "task_retry"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_STALLED = "task_stalled"
    
    # Phase events (orchestrator phases)
    PHASE_STARTED = "phase_started"
    PHASE_COMPLETED = "phase_completed"
    
    # System events
    QUEUE_DEPTH_UPDATE = "queue_depth_update"
    STATS_SNAPSHOT = "stats_snapshot"


class MonitoringEvent(BaseModel):
    """Monitoring event schema."""
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    ts: str = Field(default_factory=lambda: utc_now().isoformat())
    event_type: str
    
    # Task/project identifiers
    project_id: Optional[str] = None
    parent_task_id: Optional[str] = None  # Research task ID
    task_id: Optional[str] = None  # Job ID from queue
    task_type: Optional[str] = None
    phase: Optional[str] = None
    
    # Worker information
    worker_id: Optional[int] = None
    
    # Task execution details
    retry_count: Optional[int] = None
    status: Optional[str] = None
    duration_ms: Optional[int] = None
    
    # Aggregated data
    counts: Optional[Dict[str, int]] = None  # {completed, failed, pending, queued}
    queue: Optional[Dict[str, int]] = None  # Depth by priority
    
    # Messages and errors
    message: Optional[str] = None
    error: Optional[str] = None
    
    # Additional metadata
    meta: Optional[Dict[str, Any]] = None


class WorkerHeartbeat(BaseModel):
    """Worker heartbeat data."""
    worker_id: int
    status: str = "active"
    current_task_id: Optional[str] = None
    last_seen: str = Field(default_factory=lambda: utc_now().isoformat())
    
    
class QueueStats(BaseModel):
    """Queue statistics."""
    high_priority: int = 0
    normal_priority: int = 0
    low_priority: int = 0
    total: int = 0


class GlobalStats(BaseModel):
    """Global system statistics."""
    workers_online: int = 0
    queue_stats: QueueStats = Field(default_factory=QueueStats)
    tasks_in_progress: int = 0
    error_rate_1m: float = 0.0
    error_rate_5m: float = 0.0
    events_per_second: float = 0.0
    timestamp: str = Field(default_factory=lambda: utc_now().isoformat())