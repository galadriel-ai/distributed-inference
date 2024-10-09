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

# Rough estimate for 70% of lowest 3090 GPU node benchmark test
MINIMUM_COMPLETIONS_TOKENS_PER_SECOND = int(
    os.getenv("MINIMUM_COMPLETIONS_TOKENS_PER_SECOND", "264")
)

MAX_PARALLEL_REQUESTS_PER_NODE = int(os.getenv("MAX_PARALLEL_REQUESTS_PER_NODE", "20"))

METRICS_JOB_TIMEOUT_BETWEEN_RUNS_SECONDS = int(
    os.getenv("METRICS_JOB_TIMEOUT_BETWEEN_RUNS_SECONDS", "300")
)

# if prometheus py client will be used in multiprocessing mode, needs to point to an existing dir
PROMETHEUS_MULTIPROC_DIR = os.getenv("PROMETHEUS_MULTIPROC_DIR", None)

STYTCH_PROJECT_ID = os.getenv("STYTCH_PROJECT_ID", None)
STYTCH_SECRET = os.getenv("STYTCH_SECRET", None)
# Logged in user session duration (can use one token for this duration)
SESSION_DURATION_MINUTES = 2 * 24 * 60

# Protocols related settings
PROTOCOL_RESPONSE_CHECK_INTERVAL_IN_SECONDS = (
    3  # Protocol response check every 3 second
)
PING_PONG_PROTOCOL_NAME = "ping-pong"
GALADRIEL_PROTOCOL_CONFIG = {
    PING_PONG_PROTOCOL_NAME: {
        "version": "1.0",  # Version of the protocol
        "ping_interval_in_seconds": 600,  # Send ping every 10 minutes
        "ping_timeout_in_seconds": 10,  # Wait for pong response for 10 seconds
        "ping_miss_threshold": 3,  # If 3 consecutive pings are missed, mark the node as offline
    },
}

# Grafana API
GRAFANA_API_BASE_URL = os.getenv("GRAFANA_API_BASE_URL", None)
GRAFANA_API_KEY = os.getenv("GRAFANA_API_KEY", None)

RUN_CRON_JOBS = os.getenv("RUN_CRON_JOBS", False)
TESTING_API_KEY = os.getenv("TESTING_API_KEY", "")


def is_production():
    return ENVIRONMENT == "production"


def is_test():
    return ENVIRONMENT == "test"
