import os
from pathlib import Path

from dotenv import load_dotenv

env_path = Path(".") / ".env"
load_dotenv(dotenv_path=env_path)

ENVIRONMENT = os.getenv("PLATFORM_ENVIRONMENT", "local")

APPLICATION_NAME = "DISTRIBUTED_INFERENCE"
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1")
API_PORT = int(os.getenv("API_PORT", 5000))
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*")
LOG_FILE_PATH = "logs/logs.log"

DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "passw0rd")
DB_DATABASE = os.getenv("DB_DATABASE", "inference")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")

DB_USER_READ = os.getenv("DB_USER", "postgres")
DB_PASSWORD_READ = os.getenv("DB_PASSWORD", "passw0rd")
DB_DATABASE_READ = os.getenv("DB_DATABASE", "inference")
DB_HOST_READ = os.getenv("DB_HOST", "localhost")
DB_PORT_READ = os.getenv("DB_PORT", "5432")


def is_production():
    return ENVIRONMENT == "production"
