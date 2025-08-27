"""
Main application file for the Access Point (AP) controller using FastAPI.
Sets up the FastAPI application, includes the AP router, and manages the lifecycle
of the application including ZeroMQ socket setup and listener task.

As little logic as possible should be placed here; instead, it should be
delegated to the controller and router modules. This makes testing easier using pytest
fixtures and TestClient instances.
"""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from src.ap_controller import ap_ctrl
from src.ap_routes import ap_router
from src.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    ap_ctrl.setup_zmq(app, settings.PUB_PORT, settings.PULL_PORT)
    listener_task = asyncio.create_task(ap_ctrl.listener())
    yield
    listener_task.cancel()
    ap_ctrl.teardown_zmq(app)


def get_app():
    app = FastAPI(lifespan=lifespan)
    app.include_router(ap_router)

    @app.get("/", include_in_schema=False)
    def root():
        """
        Redirects to API docs
        """
        return RedirectResponse(url="/docs")

    return app
