from typing import Dict, Optional
from uuid import UUID

import hashlib

from fastapi import Response

from prometheus_client import Counter

import settings
from distributedinference import api_logger
from distributedinference.analytics.analytics import Analytics
from distributedinference.analytics.analytics import AnalyticsEvent
from distributedinference.analytics.analytics import EventName
from distributedinference.domain.rate_limit import rate_limit_use_case
from distributedinference.domain.rate_limit.entities import UserRateLimitResponse
from distributedinference.domain.user.entities import User
from distributedinference.repository.blockchain_proof_repository import (
    AttestationProof,
    BlockchainProofRepository,
)
from distributedinference.repository.rate_limit_repository import RateLimitRepository
from distributedinference.repository.tee_api_repository import TeeApiRepository
from distributedinference.repository.tokens_queue_repository import (
    DailyUserModelUsageIncrement,
    TokensQueueRepository,
)
from distributedinference.repository.tokens_repository import TokensRepository
from distributedinference.repository.tokens_repository import UsageTokens
from distributedinference.repository.utils import utcnow
from distributedinference.repository.verified_completions_repository import (
    VerifiedCompletionsRepository,
)
from distributedinference.service import error_responses
from distributedinference.service.completions.utils import rate_limit_to_headers
from distributedinference.service.error_responses import RateLimitError
from distributedinference.service.verified_completions.entities import (
    ChatCompletionRequest,
)


MODEL_NAME = "verified_completions"
FINE_TUNE_MODEL_NAME = "fine_tune_verified_completions"

logger = api_logger.get()

blockchain_error_counter = Counter(
    "blockchain_errors", "Total number of blockchain errors"
)


async def execute(
    api_key: str,
    fine_tune_api_key: Optional[str],
    user: User,
    request: ChatCompletionRequest,
    response: Response,
    rate_limit_repository: RateLimitRepository,
    tee_repository: TeeApiRepository,
    tokens_repository: TokensRepository,
    tokens_queue_repository: TokensQueueRepository,
    blockchain_proof_repository: BlockchainProofRepository,
    verified_completions_repository: VerifiedCompletionsRepository,
    analytics: Analytics,
) -> Dict:
    if request.stream:
        raise error_responses.UnsupportedRequestParameterError(
            "Streaming is not yet supported for verified completions."
        )
    rate_limit_info = await rate_limit_use_case.execute(
        MODEL_NAME, user, tokens_repository, rate_limit_repository
    )
    rate_limit_headers = rate_limit_to_headers(rate_limit_info)
    if rate_limit_info.rate_limit_reason:
        analytics.track_event(
            user.uid,
            AnalyticsEvent(
                EventName.USER_RATE_LIMITED,
                {
                    "model": request.model,
                    "reason": rate_limit_info.rate_limit_reason.value,
                },
            ),
        )
        raise RateLimitError(rate_limit_headers)

    response_body = await tee_repository.completions(
        fine_tune_api_key, request.model_dump(exclude_unset=True)
    )
    if not response_body:
        raise error_responses.InternalServerAPIError()

    is_fine_tune_model = True if fine_tune_api_key else False
    await _save_usage(
        tokens_queue_repository, user.uid, response_body.get("usage", {}), is_fine_tune_model
    )
    try:
        attestation_doc = response_body["attestation"]
        attestation_hash = hashlib.sha256(attestation_doc.encode()).digest()

        proof = AttestationProof(
            hashed_data=bytes.fromhex(response_body["hash"]),
            public_key=bytes.fromhex(response_body["public_key"]),
            signature=bytes.fromhex(response_body["signature"]),
            attestation=attestation_hash,
        )
        tx_response = await blockchain_proof_repository.add_proof(proof)

        if not tx_response:
            raise Exception("Failed to add proof to blockchain")

        response_body["tx_hash"] = str(tx_response.value)

    except Exception as e:
        # Fail gracefully if we can't add the proof to the blockchain
        logger.error(f"Error adding proof to blockchain: {e}")
        blockchain_error_counter.inc()
        # Set tx_hash to empty string
        response_body["tx_hash"] = ""

    await _log_verified_completion(
        verified_completions_repository, api_key, request, response_body
    )
    response.headers.update(rate_limit_headers)
    return response_body


async def _log_verified_completion(
    verified_completions_repository: VerifiedCompletionsRepository,
    api_key: str,
    request: ChatCompletionRequest,
    response: Dict,
) -> None:
    exclude_keys = {
        "hash",
        "public_key",
        "signature",
        "attestation",
        "tx_hash",
    }
    original_response = {k: v for k, v in response.items() if k not in exclude_keys}

    await verified_completions_repository.insert_verified_completion(
        api_key=api_key,
        request=request.model_dump(),
        response=original_response,
        hash=response["hash"],
        public_key=response["public_key"],
        signature=response["signature"],
        attestation=response["attestation"],
        tx_hash=response["tx_hash"],
    )


async def _save_usage(
    tokens_queue_repository: TokensQueueRepository,
    user_uid: UUID,
    usage: Dict,
    is_fine_tune_model: bool,
):
    await tokens_queue_repository.push_token_usage(
        UsageTokens(
            consumer_user_profile_id=user_uid,
            producer_node_info_id=settings.GALADRIEL_NODE_INFO_ID,
            model_name=FINE_TUNE_MODEL_NAME if is_fine_tune_model else MODEL_NAME,
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            total_tokens=usage.get("total_tokens", 0),
        )
    )
    await tokens_queue_repository.push_daily_usage(
        DailyUserModelUsageIncrement(
            user_profile_id=user_uid,
            model_name=FINE_TUNE_MODEL_NAME if is_fine_tune_model else MODEL_NAME,
            tokens_count=usage.get("total_tokens", 0),
            requests_count=1,
        )
    )
