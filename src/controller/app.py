"""
Main application file for the Access Point (AP) controller using FastAPI.
Sets up the FastAPI application, includes the AP router, and manages the lifecycle
of the application including ZeroMQ socket setup and listener task.

As little logic as possible should be placed here; instead, it should be
delegated to the controller and router modules. This makes testing easier using pytest
fixtures and TestClient instances.
"""

import asyncio
import logging
from contextlib import asynccontextmanager

import urllib3
from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from src.config import settings
from src.controller.manager_ap import ap_ctrl
from src.controller.routes_ap import ap_router
from src.controller.routes_hub import hub_router
from src.controller.routes_network import network_router

if settings.SSL_CERT is None:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(
    level=logging.getLevelName(settings.LOG_LEVEL),
    format="%(levelname)s: %(asctime)s %(filename)s - %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    ap_ctrl.setup_zmq(app, settings.PUB_PORT, settings.PULL_PORT)
    listener_task = asyncio.create_task(ap_ctrl.listener())
    yield
    listener_task.cancel()
    ap_ctrl.teardown_zmq(app)


def get_app():
    app = FastAPI(lifespan=lifespan, title="NMS network simulator", version="0.0.1")
    app.include_router(network_router)
    app.include_router(hub_router)
    app.include_router(ap_router)

    @app.get("/", include_in_schema=False)
    def root():
        """
        Redirects to API docs
        """
        return RedirectResponse(url="/docs")

    return app
