from typing import List

from fastapi import APIRouter

from distributedinference import api_logger
from distributedinference.routers.routes import chat_router
from distributedinference.routers.routes import network_router
from distributedinference.routers.routes import node_router
from distributedinference.routers.routes import metrics_router
from distributedinference.routers.routes.dashboard import authentication_router
from distributedinference.routers.routes.dashboard import dashboard_router

TAG_ROOT = "root"

router = APIRouter(prefix="/v1")
logger = api_logger.get()

routers_to_include: List[APIRouter] = [
    chat_router.router,
    node_router.router,
    network_router.router,
    metrics_router.router,
    authentication_router.router,
    dashboard_router.router,
]

for router_to_include in routers_to_include:
    router.include_router(router_to_include)
