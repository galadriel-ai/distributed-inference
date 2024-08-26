import os
from pathlib import Path

from dotenv import load_dotenv

env_path = Path(".env")
load_dotenv(dotenv_path=env_path)

DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "passw0rd")
DB_DATABASE = os.getenv("DB_DATABASE", "inference")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", 5432)
