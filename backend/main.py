"""Entry point for running the XandriX Engineer backend."""
import uvicorn
from backend.config import API_HOST, API_PORT
from backend.api.main import app

if __name__ == "__main__":
    uvicorn.run(
        "backend.api.main:app",
        host=API_HOST,
        port=API_PORT,
        reload=False,
        log_level="info",
    )
