"""Tests for the monitoring system."""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from src.monitoring.event_bus import EventBus
from src.monitoring.models import (
    MonitoringEvent, 
    MonitoringEventType, 
    WorkerHeartbeat,
    QueueStats,
    GlobalStats
)
from src.api.monitoring_ws import MonitoringWebSocketManager


class TestEventBus:
    """Test the EventBus functionality."""

    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client."""
        redis_mock = AsyncMock()
        redis_mock.publish = AsyncMock()
        return redis_mock

    @pytest.fixture
    def event_bus(self, mock_redis):
        """Create EventBus with mocked Redis."""
        return EventBus(redis_client=mock_redis)

    @pytest.mark.asyncio
    async def test_publish_task_event(self, event_bus, mock_redis):
        """Test publishing a task event."""
        event = MonitoringEvent(
            event_type=MonitoringEventType.TASK_COMPLETED.value,
            task_id="test-task-123",
            task_type="search",
            status="completed",
            worker_id=1,
            duration_ms=1500
        )
        
        await event_bus.publish(event)
        
        # Verify Redis publish was called
        mock_redis.publish.assert_called_once()
        call_args = mock_redis.publish.call_args
        
        assert call_args[0][0] == "nexus:events"
        
        # Parse the published message
        published_data = json.loads(call_args[0][1])
        assert published_data["event_type"] == "task_completed"
        assert published_data["task_id"] == "test-task-123"
        assert published_data["status"] == "completed"
        assert published_data["duration_ms"] == 1500

    @pytest.mark.asyncio
    async def test_publish_phase_event(self, event_bus, mock_redis):
        """Test publishing a phase event."""
        event = MonitoringEvent(
            event_type=MonitoringEventType.PHASE_STARTED.value,
            phase="enumeration",
            parent_task_id="parent-123",
            project_id="project-456",
            message="Starting search space enumeration",
            counts={"domains": 5, "queries": 15}
        )
        
        await event_bus.publish(event)
        
        mock_redis.publish.assert_called_once()
        call_args = mock_redis.publish.call_args
        
        published_data = json.loads(call_args[0][1])
        assert published_data["event_type"] == "phase_started"
        assert published_data["phase"] == "enumeration"
        assert published_data["counts"]["domains"] == 5

    @pytest.mark.asyncio
    async def test_publish_worker_event(self, event_bus, mock_redis):
        """Test publishing a worker event."""
        event = MonitoringEvent(
            event_type=MonitoringEventType.WORKER_HEARTBEAT.value,
            worker_id=2,
            status="active"
        )
        
        await event_bus.publish(event)
        
        mock_redis.publish.assert_called_once()
        call_args = mock_redis.publish.call_args
        
        published_data = json.loads(call_args[0][1])
        assert published_data["event_type"] == "worker_heartbeat"
        assert published_data["worker_id"] == 2

    @pytest.mark.asyncio
    async def test_publish_stats_event(self, event_bus, mock_redis):
        """Test publishing a stats event."""
        event = MonitoringEvent(
            event_type=MonitoringEventType.STATS_SNAPSHOT.value,
            queue={"search": 5, "extraction": 3},
            counts={"completed": 10, "failed": 2}
        )
        
        await event_bus.publish(event)
        
        # Stats events are published to both main and stats channels
        assert mock_redis.publish.call_count == 2
        
        # Check both calls
        calls = mock_redis.publish.call_args_list
        channels = [call[0][0] for call in calls]
        assert "nexus:events" in channels
        assert "nexus:events:stats" in channels
        
        # Check the published data
        published_data = json.loads(calls[0][0][1])
        assert published_data["event_type"] == "stats_snapshot"
        assert published_data["queue"]["search"] == 5


class TestWebSocketManager:
    """Test the MonitoringWebSocketManager functionality."""

    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client."""
        redis_mock = AsyncMock()
        redis_mock.pubsub = MagicMock()
        pubsub_mock = AsyncMock()
        pubsub_mock.subscribe = AsyncMock()
        pubsub_mock.listen = AsyncMock()
        redis_mock.pubsub.return_value = pubsub_mock
        return redis_mock, pubsub_mock

    @pytest.fixture
    def websocket_manager(self, mock_redis):
        """Create MonitoringWebSocketManager with mocked Redis."""
        redis_mock, pubsub_mock = mock_redis
        manager = MonitoringWebSocketManager(redis_mock)
        return manager, pubsub_mock

    @pytest.mark.asyncio
    async def test_add_remove_client(self, websocket_manager):
        """Test adding and removing WebSocket clients."""
        manager, _ = websocket_manager
        
        # Mock WebSocket
        mock_ws = AsyncMock()
        mock_ws.send_text = AsyncMock()
        mock_ws.accept = AsyncMock()
        mock_ws.close = AsyncMock()
        mock_ws.client_state = "CONNECTED"
        mock_ws.monitoring_filters = {}
        
        # Add client
        await manager.connect(mock_ws)
        assert len(manager.active_connections) == 1
        
        # Remove client
        await manager.disconnect(mock_ws)
        assert len(manager.active_connections) == 0

    @pytest.mark.asyncio
    async def test_broadcast_to_clients(self, websocket_manager):
        """Test broadcasting messages to all clients."""
        manager, _ = websocket_manager
        
        # Add multiple mock clients
        mock_ws1 = AsyncMock()
        mock_ws2 = AsyncMock()
        mock_ws1.send_text = AsyncMock()
        mock_ws2.send_text = AsyncMock()
        mock_ws1.accept = AsyncMock()
        mock_ws2.accept = AsyncMock()
        mock_ws1.client_state = "CONNECTED"
        mock_ws2.client_state = "CONNECTED"
        
        await manager.connect(mock_ws1)
        await manager.connect(mock_ws2)
        
        # Broadcast message
        test_message = {"event_type": "test", "data": {"test": "data"}}
        await manager._broadcast_event(test_message)
        
        # Verify both clients received the message
        mock_ws1.send_text.assert_called_once_with(json.dumps(test_message))
        mock_ws2.send_text.assert_called_once_with(json.dumps(test_message))

    @pytest.mark.asyncio
    async def test_handle_failed_client(self, websocket_manager):
        """Test handling clients that fail to receive messages."""
        manager, _ = websocket_manager
        
        # Add client that will fail
        mock_ws = AsyncMock()
        mock_ws.send_text = AsyncMock(side_effect=Exception("Connection closed"))
        mock_ws.accept = AsyncMock()
        mock_ws.client_state = "CONNECTED"
        
        await manager.connect(mock_ws)
        assert len(manager.active_connections) == 1
        
        # Broadcast should remove failed client
        test_message = {"event_type": "test", "data": {}}
        await manager._broadcast_event(test_message)
        
        # Client should be removed after failure
        assert len(manager.active_connections) == 0


class TestMonitoringModels:
    """Test the monitoring data models."""

    def test_monitoring_event_creation(self):
        """Test creating MonitoringEvent."""
        event = MonitoringEvent(
            event_type=MonitoringEventType.TASK_COMPLETED.value,
            task_id="task-123",
            task_type="search",
            status="completed",
            worker_id=1,
            duration_ms=1500
        )
        
        assert event.event_type == "task_completed"
        assert event.task_id == "task-123"
        assert event.task_type == "search"
        assert event.status == "completed"
        assert event.worker_id == 1
        assert event.duration_ms == 1500

    def test_phase_event_creation(self):
        """Test creating phase event."""
        event = MonitoringEvent(
            event_type=MonitoringEventType.PHASE_STARTED.value,
            phase="extraction",
            parent_task_id="parent-123",
            message="Starting data extraction",
            counts={"sources": 10}
        )
        
        assert event.event_type == "phase_started"
        assert event.phase == "extraction"
        assert event.parent_task_id == "parent-123"
        assert event.message == "Starting data extraction"
        assert event.counts["sources"] == 10

    def test_worker_heartbeat_creation(self):
        """Test creating WorkerHeartbeat."""
        heartbeat = WorkerHeartbeat(
            worker_id=1,
            status="active",
            current_task_id="task-123"
        )
        
        assert heartbeat.worker_id == 1
        assert heartbeat.status == "active"
        assert heartbeat.current_task_id == "task-123"

    def test_monitoring_event_type_enum(self):
        """Test MonitoringEventType enum values."""
        assert MonitoringEventType.TASK_ENQUEUED.value == "task_enqueued"
        assert MonitoringEventType.TASK_STARTED.value == "task_started"
        assert MonitoringEventType.TASK_COMPLETED.value == "task_completed"
        assert MonitoringEventType.TASK_FAILED.value == "task_failed"
        assert MonitoringEventType.PHASE_STARTED.value == "phase_started"
        assert MonitoringEventType.PHASE_COMPLETED.value == "phase_completed"
        assert MonitoringEventType.WORKER_STARTED.value == "worker_started"
        assert MonitoringEventType.WORKER_STOPPED.value == "worker_stopped"
        assert MonitoringEventType.WORKER_HEARTBEAT.value == "worker_heartbeat"
        assert MonitoringEventType.STATS_SNAPSHOT.value == "stats_snapshot"


@pytest.mark.asyncio
async def test_monitoring_integration():
    """Integration test for the monitoring system."""
    # This test would require a running Redis instance
    # For now, we'll just test that the components can be imported and instantiated
    
    try:
        from src.monitoring.event_bus import EventBus
        from src.api.monitoring_ws import MonitoringWebSocketManager
        from src.monitoring.models import MonitoringEventType, MonitoringEvent
        
        # Test instantiation
        mock_redis = AsyncMock()
        event_bus = EventBus(redis_client=mock_redis)
        # Note: MonitoringWebSocketManager requires Redis client, so we'll skip instantiation
        
        # Test data model creation
        event = MonitoringEvent(
            event_type=MonitoringEventType.TASK_COMPLETED.value,
            task_id="integration-test",
            task_type="test",
            status="completed"
        )
        
        assert event.task_id == "integration-test"
        assert event_bus is not None
        
    except ImportError as e:
        pytest.fail(f"Failed to import monitoring components: {e}")


if __name__ == "__main__":
    # Run basic tests
    import sys
    sys.path.append('.')
    
    # Test imports
    try:
        from src.monitoring.event_bus import EventBus
        from src.monitoring.models import MonitoringEventType, MonitoringEvent
        from src.api.monitoring_ws import MonitoringWebSocketManager
        print("✓ All monitoring components imported successfully")
        
        # Test model creation
        event = MonitoringEvent(
            event_type=MonitoringEventType.TASK_STARTED.value,
            task_id="test-123",
            task_type="search",
            status="running"
        )
        print("✓ MonitoringEvent model created successfully")
        
        # Test enum values
        assert MonitoringEventType.TASK_STARTED.value == "task_started"
        print("✓ MonitoringEventType enum working correctly")
        
        print("\n✅ All basic monitoring tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        sys.exit(1)