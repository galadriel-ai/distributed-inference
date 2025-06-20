import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel
from starlette.middleware.cors import CORSMiddleware

import settings
from distributedinference import api_logger
from distributedinference import dependencies
from distributedinference.domain.node import set_nodes_inactive
from distributedinference.domain.node.jobs import health_check_job
from distributedinference.domain.node.jobs import metrics_update_job
from distributedinference.domain.node.jobs import save_daily_usage_job
from distributedinference.domain.node.jobs import save_tokens_job
from distributedinference.domain.orchestration.jobs import monitor_tee_instances
from distributedinference.repository import connection
from distributedinference.routers import main_router
from distributedinference.service.exception_handlers.exception_handlers import (
    custom_exception_handler,
)
from distributedinference.service.middleware.client_version_validation_middleware import (
    ClientVersionValidationMiddleware,
)
from distributedinference.service.middleware.ip_whitelist_middleware import (
    IpWhitelistMiddleware,
)
from distributedinference.service.middleware.main_middleware import MainMiddleware
from distributedinference.service.middleware.request_enrichment_middleware import (
    RequestEnrichmentMiddleware,
)
from distributedinference.service.middleware.faucet_rate_limit_middleware import (
    FaucetRateLimitMiddleware,
)
from distributedinference.service.node.protocol import protocol_handler

logger = api_logger.get()


@asynccontextmanager
async def lifespan(_: FastAPI):
    connection.init_defaults()
    dependencies.init_globals()

    metrics_task = asyncio.create_task(
        metrics_update_job.execute(
            dependencies.get_metrics_queue_repository(),
            dependencies.get_node_repository(),
        )
    )
    protocol_task = asyncio.create_task(
        protocol_handler.execute(
            dependencies.get_protocol_handler(),
            dependencies.get_metrics_queue_repository(),
            dependencies.get_node_repository(),
            dependencies.get_connected_node_repository(),
        )
    )
    health_task = asyncio.create_task(
        health_check_job.execute(
            dependencies.get_node_repository(),
            dependencies.get_connected_node_repository(),
            dependencies.get_analytics(),
            dependencies.get_protocol_handler(),
        )
    )
    save_daily_usage_task = asyncio.create_task(
        save_daily_usage_job.execute(
            dependencies.get_tokens_repository(),
            dependencies.get_tokens_queue_repository(),
        )
    )
    save_tokens_task = asyncio.create_task(
        save_tokens_job.execute(
            dependencies.get_tokens_repository(),
            dependencies.get_tokens_queue_repository(),
        )
    )
    monitor_tee_task = asyncio.create_task(
        monitor_tee_instances.execute(
            dependencies.get_agent_repository(),
            dependencies.get_tee_orchestration_repository(),
            dependencies.get_aws_storage_repository(),
        )
    )
    yield

    # Clean up resources and database before shutting down
    logger.info("Shutdown Signal received. Cleaning up...")
    await set_nodes_inactive.execute(
        dependencies.get_node_repository(),
        dependencies.get_connected_node_repository(),
    )
    metrics_task.cancel()
    protocol_task.cancel()
    health_task.cancel()
    save_daily_usage_task.cancel()
    save_tokens_task.cancel()
    monitor_tee_task.cancel()
    await asyncio.gather(
        metrics_task,
        protocol_task,
        health_task,
        save_daily_usage_task,
        save_tokens_task,
        monitor_tee_task,
        return_exceptions=True,
    )
    logger.info("Cleanup complete.")


app = FastAPI(lifespan=lifespan)

app.include_router(
    main_router.router,
)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="API",
        version="1.0.0",
        description="API version 1.0.0",
        routes=app.routes,
        servers=_get_servers(),
    )
    openapi_schema["info"]["contact"] = {"name": "", "email": ""}
    openapi_schema["info"]["x-logo"] = {"url": ""}
    openapi_schema["x-readme"] = {
        "samples-languages": ["curl", "node", "javascript", "python"]
    }
    app.openapi_schema = openapi_schema
    return app.openapi_schema


def _get_servers():
    servers = []
    if settings.is_production():
        base_url = settings.API_BASE_URL
        if base_url.endswith("/"):
            base_url = base_url[:-1]
        servers.append({"url": base_url})
    else:
        base_url = settings.API_BASE_URL
        if base_url.endswith("/"):
            base_url = base_url[:-1]
        servers.append({"url": f"{base_url}:{settings.API_PORT}"})
    return servers


app.openapi = custom_openapi

# order of middleware matters! first middleware called is the last one added
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(MainMiddleware)
app.add_middleware(ClientVersionValidationMiddleware)
app.add_middleware(IpWhitelistMiddleware)
app.add_middleware(FaucetRateLimitMiddleware)
app.add_middleware(RequestEnrichmentMiddleware)

# exception handlers run AFTER the middlewares!
# Handles API error responses
app.add_exception_handler(Exception, custom_exception_handler)

API_TITLE = "Distributed inference"
API_DESCRIPTION = "Distributed inference"


class ApiInfo(BaseModel):
    title: str
    description: str

    class Config:
        json_schema_extra = {
            "example": {
                "title": API_TITLE,
                "description": API_DESCRIPTION,
            }
        }


def get_api_info() -> ApiInfo:
    return ApiInfo(title=API_TITLE, description=API_DESCRIPTION)


@app.get(
    "/",
    summary="Returns API information",
    description="Returns API information",
    response_description="API information with title and description.",
    response_model=ApiInfo,
)
def root():
    return get_api_info()
