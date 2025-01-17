import settings
from distributedinference.repository.aws_storage_repository import AWSStorageRepository
from distributedinference.repository.agent_logs_repository import AgentLogsRepository
from distributedinference.repository.blockchain_proof_repository import (
    BlockchainProofRepository,
)
from distributedinference import api_logger
from distributedinference.analytics.analytics import Analytics
from distributedinference.analytics.posthog import init_posthog
from distributedinference.repository.authentication_api_repository import (
    AuthenticationApiRepository,
)
from distributedinference.repository.agent_repository import AgentRepository
from distributedinference.repository.billing_repository import BillingRepository
from distributedinference.repository.connected_node_repository import (
    ConnectedNodeRepository,
)

from distributedinference.repository.connection import get_session_provider
from distributedinference.repository.connection import get_session_provider_read
from distributedinference.repository.embedding_api_repository import (
    EmbeddingApiRepository,
)
from distributedinference.repository.grafana_api_repository import GrafanaApiRepository
from distributedinference.repository.metrics_queue_repository import (
    MetricsQueueRepository,
)
from distributedinference.repository.benchmark_repository import BenchmarkRepository
from distributedinference.repository.metrics_repository import MetricsRepository
from distributedinference.repository.node_repository import NodeRepository
from distributedinference.repository.node_stats_repository import NodeStatsRepository
from distributedinference.repository.tee_api_repository import TeeApiRepository
from distributedinference.repository.tee_orchestration_repository import (
    TeeOrchestrationRepository,
)
from distributedinference.repository.tokens_repository import TokensRepository
from distributedinference.repository.tokens_queue_repository import (
    TokensQueueRepository,
)
from distributedinference.repository.user_node_repository import UserNodeRepository
from distributedinference.repository.user_repository import UserRepository
from distributedinference.repository.rate_limit_repository import RateLimitRepository
from distributedinference.repository.verified_completions_repository import (
    VerifiedCompletionsRepository,
)
from distributedinference.service.node.protocol.protocol_handler import ProtocolHandler
from distributedinference.utils.google_cloud_storage import GoogleCloudStorage

_node_repository_instance: NodeRepository
_connected_node_repository_instance: ConnectedNodeRepository
_user_node_repository_instance: UserNodeRepository

_node_stats_repository_instance: NodeStatsRepository
_benchmark_repository_instance: BenchmarkRepository
_metrics_queue_repository: MetricsQueueRepository
_metrics_repository: MetricsRepository
_rate_limit_repository: RateLimitRepository
_billing_repository: BillingRepository
_tokens_queue_repository: TokensQueueRepository

_embedding_api_repository: EmbeddingApiRepository
_authentication_api_repository: AuthenticationApiRepository
_analytics: Analytics
_protocol_handler: ProtocolHandler

_grafana_api_repository: GrafanaApiRepository
_tee_api_repository: TeeApiRepository
_tee_orchestration_repository: TeeOrchestrationRepository
_blockchain_proof_repository: BlockchainProofRepository
_google_cloud_storage_client: GoogleCloudStorage
_aws_storage_repository: AWSStorageRepository

_verified_completions_repository: VerifiedCompletionsRepository
_agent_repository: AgentRepository
_agent_logs_repository: AgentLogsRepository


# pylint: disable=W0603, R0915
def init_globals():
    # TODO: refactor this, we shouldn't use globals
    global _node_repository_instance
    global _connected_node_repository_instance
    global _user_node_repository_instance
    global _node_stats_repository_instance
    global _benchmark_repository_instance
    global _metrics_queue_repository
    global _metrics_repository
    global _rate_limit_repository
    global _billing_repository
    global _tokens_queue_repository
    global _embedding_api_repository
    global _authentication_api_repository
    global _analytics
    global _protocol_handler
    global _grafana_api_repository
    global _tee_api_repository
    global _tee_orchestration_repository
    global _blockchain_proof_repository
    global _google_cloud_storage_client
    global _aws_storage_repository
    global _verified_completions_repository
    global _agent_repository
    global _agent_logs_repository

    _node_repository_instance = NodeRepository(
        get_session_provider(),
        get_session_provider_read(),
    )
    _connected_node_repository_instance = ConnectedNodeRepository(
        settings.MAX_PARALLEL_REQUESTS_PER_NODE,
        settings.MAX_PARALLEL_REQUESTS_PER_DATACENTER_NODE,
        settings.HOSTNAME,
    )
    _user_node_repository_instance = UserNodeRepository(
        get_session_provider(),
        get_session_provider_read(),
    )
    _node_stats_repository_instance = NodeStatsRepository(
        get_session_provider(), get_session_provider_read()
    )
    _benchmark_repository_instance = BenchmarkRepository(
        get_session_provider(), get_session_provider_read()
    )
    _metrics_queue_repository = MetricsQueueRepository()
    _metrics_repository = MetricsRepository(
        get_session_provider(), get_session_provider_read()
    )
    _rate_limit_repository = RateLimitRepository(
        get_session_provider(), get_session_provider_read()
    )
    _billing_repository = BillingRepository(
        get_session_provider(), get_session_provider_read()
    )
    _verified_completions_repository = VerifiedCompletionsRepository(
        get_session_provider(), get_session_provider_read()
    )
    _tokens_queue_repository = TokensQueueRepository()
    _agent_repository = AgentRepository(
        get_session_provider(), get_session_provider_read()
    )
    _agent_logs_repository = AgentLogsRepository(
        get_session_provider(), get_session_provider_read()
    )

    _analytics = Analytics(
        posthog=init_posthog(
            is_production=settings.is_production(),
            is_test=settings.is_test(),
        ),
        logger=api_logger.get(),
    )

    _embedding_api_repository = EmbeddingApiRepository(
        settings.EMBEDDING_API_BASE_URL, settings.SUPPORTED_EMBEDDING_MODELS[0]
    )
    if settings.is_production() or (
        settings.STYTCH_PROJECT_ID and settings.STYTCH_SECRET
    ):
        _authentication_api_repository = AuthenticationApiRepository()

    _protocol_handler = ProtocolHandler()
    if settings.GRAFANA_API_BASE_URL and settings.GRAFANA_API_KEY:
        _grafana_api_repository = GrafanaApiRepository(
            settings.GRAFANA_API_BASE_URL, settings.GRAFANA_API_KEY
        )
    if settings.TEE_API_BASE_URL and settings.OPENAI_API_KEY:
        _tee_api_repository = TeeApiRepository(
            settings.TEE_API_BASE_URL,
            settings.TEE_API_BASE_URL_2,
            settings.OPENAI_API_KEY,
        )
    if (
        settings.SOLANA_PROGRAM_ID
        and settings.SOLANA_RPC_URL
        and settings.SOLANA_KEYPAIR_DIR
    ):
        _blockchain_proof_repository = BlockchainProofRepository(
            settings.SOLANA_RPC_URL,
            settings.SOLANA_PROGRAM_ID,
            settings.SOLANA_KEYPAIR_DIR,
        )
    _google_cloud_storage_client = GoogleCloudStorage()
    _tee_orchestration_repository = TeeOrchestrationRepository(
        settings.TEE_HOST_BASE_URL
    )
    _aws_storage_repository = AWSStorageRepository(
        settings.AGENTS_MEMORY_STORAGE_BUCKET
    )


def get_node_repository() -> NodeRepository:
    return _node_repository_instance


def get_connected_node_repository() -> ConnectedNodeRepository:
    return _connected_node_repository_instance


def get_user_node_repository() -> UserNodeRepository:
    return _user_node_repository_instance


def get_node_stats_repository() -> NodeStatsRepository:
    return _node_stats_repository_instance


def get_benchmark_repository() -> BenchmarkRepository:
    return _benchmark_repository_instance


def get_user_repository() -> UserRepository:
    return UserRepository(get_session_provider(), get_session_provider_read())


def get_tokens_repository() -> TokensRepository:
    return TokensRepository(get_session_provider(), get_session_provider_read())


def get_metrics_queue_repository() -> MetricsQueueRepository:
    return _metrics_queue_repository


def get_metrics_repository() -> MetricsRepository:
    return _metrics_repository


def get_embedding_api_repository() -> EmbeddingApiRepository:
    return _embedding_api_repository


def get_authentication_api_repository() -> AuthenticationApiRepository:
    return _authentication_api_repository


def get_analytics() -> Analytics:
    return _analytics


def get_protocol_handler() -> ProtocolHandler:
    return _protocol_handler


def get_grafana_repository() -> GrafanaApiRepository:
    return _grafana_api_repository


def get_tee_repository() -> TeeApiRepository:
    return _tee_api_repository


def get_blockchain_proof_repository() -> BlockchainProofRepository:
    return _blockchain_proof_repository


def get_rate_limit_repository() -> RateLimitRepository:
    return _rate_limit_repository


def get_billing_repository() -> BillingRepository:
    return _billing_repository


def get_google_cloud_storage_client() -> GoogleCloudStorage:
    return _google_cloud_storage_client


def get_tokens_queue_repository() -> TokensQueueRepository:
    return _tokens_queue_repository


def get_verified_completions_repository() -> VerifiedCompletionsRepository:
    return _verified_completions_repository


def get_agent_repository() -> AgentRepository:
    return _agent_repository


def get_agent_logs_repository() -> AgentLogsRepository:
    return _agent_logs_repository


def get_tee_orchestration_repository() -> TeeOrchestrationRepository:
    return _tee_orchestration_repository


def get_aws_storage_repository() -> AWSStorageRepository:
    return _aws_storage_repository
