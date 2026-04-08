import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "XandriXEngineer"
    VERSION: str = "1.0.0"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    WORKSPACE_DIR: str = "./workspace"
    LOG_LEVEL: str = "INFO"

    MAX_RETRIES: int = 3
    RETRY_DELAY: float = 2.0

    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    MODEL_PROVIDER: str = "openai"
    DEFAULT_MODEL: str = "gpt-4o"

    CHROMA_PERSIST_DIR: str = "./data/chroma"
    MAX_CONCURRENT_TASKS: int = 5
    TASK_TIMEOUT: int = 300

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()
