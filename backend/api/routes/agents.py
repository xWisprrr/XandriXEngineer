from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException

from utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/agents", tags=["agents"])

_agent_registry: Dict[str, Any] = {}


def get_agent_registry() -> Dict[str, Any]:
    if not _agent_registry:
        try:
            from agents.orchestrator import AgentOrchestrator
            orchestrator = AgentOrchestrator()
            _agent_registry.update(orchestrator.get_all_agents())
        except Exception as exc:
            logger.error(f"Failed to load agents: {exc}")
    return _agent_registry


@router.get("", response_model=List[Dict[str, Any]])
async def list_agents():
    registry = get_agent_registry()
    agents = []
    for name, info in registry.items():
        agents.append({
            "name": name,
            "status": info.get("status", "idle") if isinstance(info, dict) else getattr(info, "status", "idle"),
            "current_action": info.get("current_action", "") if isinstance(info, dict) else getattr(info, "current_action", ""),
        })
    return agents


@router.get("/{agent_name}/status")
async def get_agent_status(agent_name: str):
    registry = get_agent_registry()
    if agent_name not in registry:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")
    info = registry[agent_name]
    return {
        "name": agent_name,
        "status": info.get("status", "idle") if isinstance(info, dict) else getattr(info, "status", "idle"),
        "current_action": info.get("current_action", "") if isinstance(info, dict) else getattr(info, "current_action", ""),
    }


@router.post("/{agent_name}/reset")
async def reset_agent(agent_name: str):
    registry = get_agent_registry()
    if agent_name not in registry:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")
    info = registry[agent_name]
    if isinstance(info, dict):
        info["status"] = "idle"
        info["current_action"] = ""
    else:
        if hasattr(info, "status"):
            info.status = "idle"
        if hasattr(info, "current_action"):
            info.current_action = ""
    return {"message": f"Agent '{agent_name}' reset", "name": agent_name}
