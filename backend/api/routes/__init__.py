from api.routes.tasks import router as tasks_router
from api.routes.agents import router as agents_router
from api.routes.files import router as files_router
from api.routes.logs import router as logs_router

__all__ = ["tasks_router", "agents_router", "files_router", "logs_router"]
