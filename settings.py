import os
from pathlib import Path
from uuid import UUID

from dotenv import load_dotenv

env_path = Path(".") / ".env"
load_dotenv(dotenv_path=env_path)

ENVIRONMENT = os.getenv("PLATFORM_ENVIRONMENT", "local")


def is_production():
    return ENVIRONMENT == "production"


def is_test():
    return ENVIRONMENT == "test"


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

DB_USER_READ = os.getenv("DB_USER_READ", "postgres")
DB_PASSWORD_READ = os.getenv("DB_PASSWORD_READ", "passw0rd")
DB_DATABASE_READ = os.getenv("DB_DATABASE_READ", "inference")
DB_HOST_READ = os.getenv("DB_HOST_READ", "localhost")
DB_PORT_READ = os.getenv("DB_PORT_READ", "5432")

# This should be unified to a sensible unified data format at some point
SUPPORTED_MODELS = [
    "neuralmagic/Meta-Llama-3.1-8B-Instruct-FP8",
    "neuralmagic/Meta-Llama-3.1-70B-Instruct-quantized.w4a16",
    "neuralmagic/Meta-Llama-3.1-405B-Instruct-quantized.w4a16",
    "hugging-quants/Meta-Llama-3.1-70B-Instruct-AWQ-INT4",
]
if not is_production():
    SUPPORTED_MODELS.append("hugging-quants/Meta-Llama-3.1-8B-Instruct-AWQ-INT4")

MODEL_NAME_MAPPING = {
    "llama3.1": "neuralmagic/Meta-Llama-3.1-8B-Instruct-FP8",
    "llama3.1:8b": "neuralmagic/Meta-Llama-3.1-8B-Instruct-FP8",
    "llama3.1-8b": "neuralmagic/Meta-Llama-3.1-8B-Instruct-FP8",
    "llama3.1:70b": "neuralmagic/Meta-Llama-3.1-70B-Instruct-quantized.w4a16",
    "llama3.1-70b": "neuralmagic/Meta-Llama-3.1-70B-Instruct-quantized.w4a16",
    "llama3.1:405b": "neuralmagic/Meta-Llama-3.1-405B-Instruct-quantized.w4a16",
    "llama3.1-405b": "neuralmagic/Meta-Llama-3.1-405B-Instruct-quantized.w4a16",
}
MODEL_MAX_TOKENS_MAPPING = {
    "neuralmagic/Meta-Llama-3.1-8B-Instruct-FP8": 8192,
    "neuralmagic/Meta-Llama-3.1-70B-Instruct-quantized.w4a16": 131072,
    "neuralmagic/Meta-Llama-3.1-405B-Instruct-quantized.w4a16": 131072,
    "hugging-quants/Meta-Llama-3.1-70B-Instruct-AWQ-INT4": 131072,
    "hugging-quants/Meta-Llama-3.1-8B-Instruct-AWQ-INT4": 8192,
}
MODELS_SUPPORTING_TOOLS = [
    "neuralmagic/Meta-Llama-3.1-70B-Instruct-quantized.w4a16",
    "neuralmagic/Meta-Llama-3.1-405B-Instruct-quantized.w4a16",
    "hugging-quants/Meta-Llama-3.1-70B-Instruct-AWQ-INT4",
]

# Rough estimate for 70% of lowest 3090 GPU node benchmark test
MINIMUM_COMPLETIONS_TOKENS_PER_SECOND = int(
    os.getenv("MINIMUM_COMPLETIONS_TOKENS_PER_SECOND", "264")
)
MINIMUM_COMPLETIONS_TOKENS_PER_SECOND_PER_MODEL = {
    # If model not found uses MINIMUM_COMPLETIONS_TOKENS_PER_SECOND as a fallback
    "neuralmagic/Meta-Llama-3.1-70B-Instruct-quantized.w4a16": 200,
    "neuralmagic/Meta-Llama-3.1-405B-Instruct-quantized.w4a16": 120,
}

SMALL_PROMPT_SIZE = 1000
MIN_TIME_TO_FIRST_TOKEN_SMALL_SEC = float(
    os.getenv("MIN_TIME_TO_FIRST_TOKEN_SMALL_SEC", 3.0)
)
MIN_TIME_TO_FIRST_TOKEN_BIG_SEC = float(
    os.getenv("MIN_TIME_TO_FIRST_TOKEN_BIG_SEC", 8.0)
)

EMBEDDING_API_BASE_URL = os.getenv("EMBEDDING_API_BASE_URL", None)
SUPPORTED_EMBEDDING_MODELS = [
    # https://huggingface.co/Alibaba-NLP/gte-large-en-v1.5
    "gte-large-en-v1.5",
]

MAX_PARALLEL_REQUESTS_PER_NODE = int(os.getenv("MAX_PARALLEL_REQUESTS_PER_NODE", "10"))
MAX_PARALLEL_REQUESTS_PER_DATACENTER_NODE = int(
    os.getenv("MAX_PARALLEL_REQUESTS_PER_DATACENTER_NODE", "20")
)

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
# Estimated latency (in ms) between different backend servers (e.g. EU west to US east)
BACKEND_NODE_LATENCY_MILLISECONDS = int(
    os.getenv("BACKEND_NODE_LATENCY_MILLISECONDS", 80)
)
NODE_HEALTH_CHECK_INTERVAL_SECONDS = int(os.getenv("NODE_HEALTH_CHECK_INTERVAL", "563"))

# Grafana API
GRAFANA_API_BASE_URL = os.getenv("GRAFANA_API_BASE_URL", None)
GRAFANA_API_KEY = os.getenv("GRAFANA_API_KEY", None)

# If it is False, it will still run the noise job
RUN_CRON_JOBS = os.getenv("RUN_CRON_JOBS", False)
TESTING_API_KEY = os.getenv("TESTING_API_KEY", "")

# Rate limit
DEFAULT_USAGE_TIER_UUID = "06706644-2409-7efd-8000-3371c5d632d3"
PAID_USAGE_TIER_UUID = "01928f3a-2f73-7c45-959e-a3e170c49a45"

# Health check job
HEALTH_CHECK_JOB_TIMEOUT_BETWEEN_RUNS_SECONDS = int(
    os.getenv("HEALTH_CHECK_JOB_TIMEOUT_BETWEEN_RUNS_SECONDS", "15")
)

GALADRIEL_USER_PROFILE_ID = UUID("00000000-0000-0000-0000-000000000000")
GALADRIEL_NODE_INFO_ID = UUID("00000000-0000-0000-0000-000000000001")

TOGETHER_AI_API_KEY = os.getenv("TOGETHER_AI_API_KEY", None)

SERPAPI_KEY = os.getenv("SERPAPI_KEY", None)

SLACK_CHANNEL_ID = os.getenv("SLACK_CHANNEL_ID")
SLACK_OAUTH_TOKEN = os.getenv("SLACK_OAUTH_TOKEN")

_peer_nodes = os.getenv("PEER_NODES_LIST", "").split(";")
# Remove duplicated nodes
PEER_NODES_LIST = list(set(_peer_nodes))

HOSTNAME = os.getenv("HOSTNAME", "")
