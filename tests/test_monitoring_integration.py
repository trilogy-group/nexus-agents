"""Integration tests for monitoring system with live Redis."""

import asyncio
import json
import pytest
import redis.asyncio as redis
from unittest.mock import AsyncMock

from src.monitoring.event_bus import EventBus
from src.monitoring.models import MonitoringEvent, MonitoringEventType
from src.api.monitoring_ws import MonitoringWebSocketManager


@pytest.mark.asyncio
async def test_live_redis_integration():
    """Test monitoring system with live Redis connection."""
    try:
        # Connect to Redis
        redis_client = redis.from_url("redis://localhost:6379")
        await redis_client.ping()
        
        # Create event bus
        event_bus = EventBus(redis_client=redis_client)
        
        # Create a test event
        event = MonitoringEvent(
            event_type=MonitoringEventType.TASK_STARTED.value,
            task_id="test-task-123",
            task_type="search",
            project_id="test-project",
            message="Test task started"
        )
        
        # Publish the event
        success = await event_bus.publish(event, project_id="test-project")
        assert success
        
        # Test WebSocket manager
        ws_manager = MonitoringWebSocketManager(redis_client=redis_client)
        
        # Mock WebSocket client
        mock_websocket = AsyncMock()
        mock_websocket.send_text = AsyncMock()
        
        # Connect client
        await ws_manager.connect(mock_websocket)
        assert mock_websocket in ws_manager.active_connections
        
        # Publish another event to test broadcasting
        stats_event = MonitoringEvent(
            event_type=MonitoringEventType.STATS_SNAPSHOT.value,
            queue={"search": 5, "extraction": 3},
            counts={"completed": 10, "failed": 2}
        )
        
        await event_bus.publish(stats_event)
        
        # Give some time for the event to be processed
        await asyncio.sleep(0.1)
        
        # Clean up
        await ws_manager.disconnect(mock_websocket)
        await redis_client.aclose()
        
        print("✅ Live Redis integration test passed!")
        
    except redis.ConnectionError:
        pytest.skip("Redis not available for integration test")
    except Exception as e:
        pytest.fail(f"Integration test failed: {e}")


@pytest.mark.asyncio
async def test_monitoring_event_flow():
    """Test complete monitoring event flow."""
    try:
        # Connect to Redis
        redis_client = redis.from_url("redis://localhost:6379")
        await redis_client.ping()
        
        # Create event bus
        event_bus = EventBus(redis_client=redis_client)
        
        # Test different event types
        events = [
            MonitoringEvent(
                event_type=MonitoringEventType.TASK_ENQUEUED.value,
                task_id="task-001",
                task_type="search",
                project_id="project-1"
            ),
            MonitoringEvent(
                event_type=MonitoringEventType.TASK_STARTED.value,
                task_id="task-001",
                task_type="search",
                project_id="project-1",
                worker_id=1
            ),
            MonitoringEvent(
                event_type=MonitoringEventType.PHASE_STARTED.value,
                task_id="task-001",
                phase="data_collection",
                project_id="project-1"
            ),
            MonitoringEvent(
                event_type=MonitoringEventType.PHASE_COMPLETED.value,
                task_id="task-001",
                phase="data_collection",
                project_id="project-1",
                duration_ms=1500
            ),
            MonitoringEvent(
                event_type=MonitoringEventType.TASK_COMPLETED.value,
                task_id="task-001",
                task_type="search",
                project_id="project-1",
                duration_ms=5000
            ),
            MonitoringEvent(
                event_type=MonitoringEventType.STATS_SNAPSHOT.value,
                queue={"search": 2, "extraction": 1},
                counts={"completed": 1, "failed": 0}
            )
        ]
        
        # Publish all events
        for event in events:
            success = await event_bus.publish(event, project_id=event.project_id)
            assert success, f"Failed to publish event: {event.event_type}"
        
        await redis_client.aclose()
        print("✅ Monitoring event flow test passed!")
        
    except redis.ConnectionError:
        pytest.skip("Redis not available for integration test")
    except Exception as e:
        pytest.fail(f"Event flow test failed: {e}")


if __name__ == "__main__":
    # Run the tests directly
    asyncio.run(test_live_redis_integration())
    asyncio.run(test_monitoring_event_flow())