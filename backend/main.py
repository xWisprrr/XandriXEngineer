import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.routes.tasks import router as tasks_router
from api.routes.agents import router as agents_router
from api.routes.files import router as files_router
from api.routes.logs import router as logs_router
from api.websocket import websocket_endpoint, register_event_handlers
from config import settings
from core.agent_loop import agent_loop
from tools.registry import initialize_registry
from utils.logger import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.VERSION}")
    os.makedirs(settings.WORKSPACE_DIR, exist_ok=True)
    os.makedirs(settings.CHROMA_PERSIST_DIR, exist_ok=True)

    # Initialize tools
    initialize_registry()
    logger.info("Tool registry initialized")

    # Register WebSocket event handlers
    register_event_handlers()
    logger.info("Event handlers registered")

    # Start agent loop
    await agent_loop.start()
    logger.info("Agent loop started")

    yield

    # Shutdown
    logger.info("Shutting down agent loop...")
    await agent_loop.stop()
    logger.info(f"{settings.APP_NAME} shutdown complete")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="Autonomous AI Software Engineer",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(tasks_router)
app.include_router(agents_router)
app.include_router(files_router)
app.include_router(logs_router)


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.VERSION,
        "debug": settings.DEBUG,
    }


@app.websocket("/ws/{client_id}")
async def websocket_handler(websocket: WebSocket, client_id: str):
    await websocket_endpoint(websocket, client_id)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
