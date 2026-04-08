"""
XandriX Engineer - Central Configuration
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent

# LLM Configuration
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")  # openai | anthropic | ollama | groq
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "")  # For Ollama or custom endpoints
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.2"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "8192"))

# Server Configuration
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")

# Storage
DATA_DIR = Path(os.getenv("DATA_DIR", str(BASE_DIR / "data")))
PROJECTS_DIR = DATA_DIR / "projects"
MEMORY_DB_PATH = DATA_DIR / "memory.db"
TASKS_DB_PATH = DATA_DIR / "tasks.db"
LOGS_DIR = DATA_DIR / "logs"

# Agent Configuration
MAX_ITERATIONS = int(os.getenv("MAX_ITERATIONS", "50"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "5"))
AGENT_TIMEOUT = int(os.getenv("AGENT_TIMEOUT", "300"))  # seconds
PARALLEL_AGENTS = int(os.getenv("PARALLEL_AGENTS", "3"))

# Docker Configuration
DOCKER_ENABLED = os.getenv("DOCKER_ENABLED", "true").lower() == "true"
DOCKER_IMAGE_BASE = os.getenv("DOCKER_IMAGE_BASE", "ubuntu:22.04")
DOCKER_WORKSPACE = os.getenv("DOCKER_WORKSPACE", "/workspace")

# Tool Configuration
WEB_SEARCH_API_KEY = os.getenv("WEB_SEARCH_API_KEY", "")
WEB_SEARCH_ENGINE = os.getenv("WEB_SEARCH_ENGINE", "duckduckgo")  # duckduckgo | serpapi
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

# Ensure directories exist
for d in [DATA_DIR, PROJECTS_DIR, LOGS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Supported Languages
SUPPORTED_LANGUAGES = {
    "python": {
        "extensions": [".py"],
        "runner": "python3",
        "package_manager": "pip",
        "compile": False,
    },
    "javascript": {
        "extensions": [".js", ".mjs"],
        "runner": "node",
        "package_manager": "npm",
        "compile": False,
    },
    "typescript": {
        "extensions": [".ts", ".tsx"],
        "runner": "ts-node",
        "package_manager": "npm",
        "compile": True,
        "compiler": "tsc",
    },
    "c": {
        "extensions": [".c"],
        "runner": None,
        "package_manager": None,
        "compile": True,
        "compiler": "gcc",
    },
    "cpp": {
        "extensions": [".cpp", ".cc", ".cxx"],
        "runner": None,
        "package_manager": None,
        "compile": True,
        "compiler": "g++",
    },
    "java": {
        "extensions": [".java"],
        "runner": "java",
        "package_manager": "maven",
        "compile": True,
        "compiler": "javac",
    },
    "go": {
        "extensions": [".go"],
        "runner": "go run",
        "package_manager": "go",
        "compile": True,
        "compiler": "go build",
    },
    "rust": {
        "extensions": [".rs"],
        "runner": None,
        "package_manager": "cargo",
        "compile": True,
        "compiler": "rustc",
    },
    "bash": {
        "extensions": [".sh", ".bash"],
        "runner": "bash",
        "package_manager": None,
        "compile": False,
    },
    "sql": {
        "extensions": [".sql"],
        "runner": "sqlite3",
        "package_manager": None,
        "compile": False,
    },
}
