import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from src.ap_controller import listener, setup_zmq
from src.ap_routes import ap_router
from src.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    pub, pull = await setup_zmq(app, settings.PUB_PORT, settings.PULL_PORT)
    listener_task = asyncio.create_task(listener(pull))
    yield
    listener_task.cancel()


app = FastAPI(lifespan=lifespan)
app.include_router(ap_router)


@app.get("/", include_in_schema=False)
def root():
    """
    Redirects to API docs
    """
    return RedirectResponse(url="/docs")
