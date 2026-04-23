from typing import Any, Dict, List, Optional
from utils.logger import get_logger

logger = get_logger(__name__)


class ToolRegistry:
    _instance: Optional["ToolRegistry"] = None

    def __new__(cls) -> "ToolRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tools: Dict[str, Any] = {}
        return cls._instance

    def register(self, name: str, tool: Any) -> None:
        self._tools[name] = tool
        logger.debug(f"Registered tool: {name}")

    def get(self, name: str) -> Optional[Any]:
        return self._tools.get(name)

    def list_tools(self) -> List[str]:
        return list(self._tools.keys())

    async def execute_tool(self, name: str, method: str = "execute", **kwargs: Any) -> Any:
        tool = self._tools.get(name)
        if not tool:
            raise ValueError(f"Tool '{name}' not found")
        func = getattr(tool, method, None)
        if not func:
            raise AttributeError(f"Tool '{name}' has no method '{method}'")
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return await func(**kwargs)
        return func(**kwargs)


def initialize_registry() -> ToolRegistry:
    from tools.terminal import TerminalTool
    from tools.filesystem import FileSystemTool
    from tools.browser import BrowserTool
    from tools.git_tool import GitTool
    from config import settings

    registry = ToolRegistry()
    registry.register("terminal", TerminalTool(default_cwd=settings.WORKSPACE_DIR))
    registry.register("filesystem", FileSystemTool(base_dir=settings.WORKSPACE_DIR))
    registry.register("browser", BrowserTool())
    registry.register("git", GitTool(repo_path=settings.WORKSPACE_DIR))
    logger.info(f"Initialized tools: {registry.list_tools()}")
    return registry


tool_registry = ToolRegistry()
