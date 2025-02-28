from typing import List

from fastapi import APIRouter

from distributedinference import api_logger
from distributedinference.routers.routes import agents_router
from distributedinference.routers.routes import chat_router
from distributedinference.routers.routes import images_router
from distributedinference.routers.routes import embedding_router
from distributedinference.routers.routes import network_router
from distributedinference.routers.routes import node_router
from distributedinference.routers.routes import metrics_router
from distributedinference.routers.routes import models_router
from distributedinference.routers.routes import faucet_router
from distributedinference.routers.routes import tool_router
from distributedinference.routers.routes import verified_chat_router
from distributedinference.routers.routes.dashboard import authentication_router
from distributedinference.routers.routes.dashboard import dashboard_router

TAG_ROOT = "root"

router = APIRouter(prefix="/v1")
logger = api_logger.get()

routers_to_include: List[APIRouter] = [
    # This is the order they show up in openapi.json
    agents_router.router,
    chat_router.router,
    images_router.router,
    embedding_router.router,
    tool_router.router,
    node_router.router,
    network_router.router,
    faucet_router.router,
    authentication_router.router,
    dashboard_router.router,
    metrics_router.router,
    models_router.router,
    verified_chat_router.router,
]

for router_to_include in routers_to_include:
    router.include_router(router_to_include)
