import os
from pathlib import Path

from dotenv import load_dotenv

env_path = Path(".") / ".env"
load_dotenv(dotenv_path=env_path)

ENVIRONMENT = os.getenv("PLATFORM_ENVIRONMENT", "local")

APPLICATION_NAME = "DISTRIBUTED_INFERENCE"
API_PORT = int(os.getenv("API_PORT", 5000))
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1/")
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*")
LOG_FILE_PATH = "logs/logs.log"


def is_production():
    return ENVIRONMENT == "production"
