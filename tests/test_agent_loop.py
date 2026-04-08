import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import asyncio
import pytest
import pytest_asyncio
from datetime import datetime, timezone

from core.task_queue import Task, TaskQueue, TaskStatus, TaskStep
from core.event_bus import EventBus, EventType


@pytest.fixture
def queue():
    return TaskQueue()


@pytest.fixture
def sample_task():
    return Task(title="Test Task", description="A test task description", priority=5)


def test_task_creation(sample_task):
    assert sample_task.id is not None
    assert len(sample_task.id) > 0
    assert sample_task.title == "Test Task"
    assert sample_task.description == "A test task description"
    assert sample_task.status == TaskStatus.PENDING
    assert sample_task.priority == 5
    assert isinstance(sample_task.created_at, datetime)
    assert sample_task.steps == []
    assert sample_task.logs == []


def test_task_to_dict(sample_task):
    d = sample_task.to_dict()
    assert d["id"] == sample_task.id
    assert d["title"] == "Test Task"
    assert d["status"] == "pending"
    assert "created_at" in d
    assert d["steps"] == []


def test_task_status_transitions(queue, sample_task):
    queue.add_task(sample_task)

    # pending -> running
    queue.update_task(sample_task.id, status=TaskStatus.RUNNING)
    t = queue.get_task(sample_task.id)
    assert t.status == TaskStatus.RUNNING

    # running -> paused
    success = queue.pause_task(sample_task.id)
    assert success
    t = queue.get_task(sample_task.id)
    assert t.status == TaskStatus.PAUSED

    # paused -> pending (resume)
    success = queue.resume_task(sample_task.id)
    assert success
    t = queue.get_task(sample_task.id)
    assert t.status == TaskStatus.PENDING


def test_task_queue_ordering(queue):
    low = Task(title="Low", description="low", priority=1)
    high = Task(title="High", description="high", priority=10)
    medium = Task(title="Medium", description="medium", priority=5)

    queue.add_task(low)
    queue.add_task(high)
    queue.add_task(medium)

    # get_next_pending should return highest priority first
    next_task = queue.get_next_pending()
    assert next_task is not None
    assert next_task.title == "High"


def test_task_cancellation(queue, sample_task):
    queue.add_task(sample_task)
    success = queue.cancel_task(sample_task.id)
    assert success
    t = queue.get_task(sample_task.id)
    assert t.status == TaskStatus.CANCELLED


def test_task_queue_add_and_list(queue):
    t1 = Task(title="T1", description="d1")
    t2 = Task(title="T2", description="d2")
    queue.add_task(t1)
    queue.add_task(t2)
    tasks = queue.list_tasks()
    assert len(tasks) == 2


def test_task_queue_delete(queue, sample_task):
    queue.add_task(sample_task)
    success = queue.delete_task(sample_task.id)
    assert success
    assert queue.get_task(sample_task.id) is None


def test_task_queue_not_found(queue):
    assert queue.get_task("nonexistent-id") is None
    assert not queue.delete_task("nonexistent-id")


@pytest.mark.asyncio
async def test_event_bus_publish_subscribe():
    bus = EventBus()
    received = []

    async def handler(event_type, data):
        received.append((event_type, data))

    bus.subscribe(EventType.TASK_STARTED, handler)
    await bus.publish(EventType.TASK_STARTED, {"task_id": "123"})

    assert len(received) == 1
    assert received[0][1] == {"task_id": "123"}


@pytest.mark.asyncio
async def test_event_bus_unsubscribe():
    bus = EventBus()
    received = []

    async def handler(event_type, data):
        received.append(data)

    bus.subscribe(EventType.TASK_COMPLETED, handler)
    bus.unsubscribe(EventType.TASK_COMPLETED, handler)
    await bus.publish(EventType.TASK_COMPLETED, {"task_id": "456"})

    assert len(received) == 0


@pytest.mark.asyncio
async def test_event_bus_sync_handler():
    bus = EventBus()
    received = []

    def sync_handler(event_type, data):
        received.append(data)

    bus.subscribe(EventType.LOG_MESSAGE, sync_handler)
    await bus.publish(EventType.LOG_MESSAGE, {"message": "test"})
    assert len(received) == 1
