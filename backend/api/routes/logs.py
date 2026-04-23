import asyncio
import json
from collections import deque
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/logs", tags=["logs"])

# In-memory log store
_log_store: deque = deque(maxlen=1000)


def add_log(level: str, message: str, task_id: Optional[str] = None, agent: Optional[str] = None) -> None:
    _log_store.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": level.upper(),
        "message": message,
        "task_id": task_id,
        "agent": agent,
    })


def _filter_logs(
    logs: List[Dict[str, Any]],
    level: Optional[str],
    task_id: Optional[str],
    limit: int,
) -> List[Dict[str, Any]]:
    result = list(logs)
    if level:
        result = [l for l in result if l.get("level", "").upper() == level.upper()]
    if task_id:
        result = [l for l in result if l.get("task_id") == task_id]
    return result[-limit:]


@router.get("")
async def get_logs(
    limit: int = Query(default=100, ge=1, le=1000),
    level: Optional[str] = Query(default=None),
    task_id: Optional[str] = Query(default=None),
):
    logs = _filter_logs(list(_log_store), level, task_id, limit)
    return {"logs": logs, "count": len(logs)}


@router.get("/stream")
async def stream_logs(
    limit: int = Query(default=50, ge=1, le=500),
    level: Optional[str] = Query(default=None),
    task_id: Optional[str] = Query(default=None),
):
    """SSE endpoint for streaming logs."""
    async def event_generator():
        last_index = max(0, len(_log_store) - limit)
        while True:
            current_logs = list(_log_store)
            new_logs = current_logs[last_index:]
            if new_logs:
                for log in new_logs:
                    if level and log.get("level", "").upper() != level.upper():
                        continue
                    if task_id and log.get("task_id") != task_id:
                        continue
                    yield f"data: {json.dumps(log)}\n\n"
                last_index = len(current_logs)
            await asyncio.sleep(0.5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.delete("")
async def clear_logs():
    _log_store.clear()
    return {"message": "Logs cleared"}
