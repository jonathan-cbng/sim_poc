import logging

from fastapi import FastAPI, Request
from pydantic import BaseModel

app = FastAPI()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("sim_poc")


class Address(BaseModel):
    ip: str
    port: int


class Route(BaseModel):
    src: Address
    dest: Address


@app.get("/which_ip")
async def which_ip(request: Request) -> Route:
    server_addr = request.scope.get("server", ("unknown", "unknown"))
    dest = Address(ip=server_addr[0], port=server_addr[1])
    source_addr = request.scope.get("client", ("unknown", "unknown"))
    source = Address(ip=source_addr[0], port=source_addr[1])
    logging.debug(f"Received request from {source.ip}:{source.port} to {dest.ip}:{dest.port}")
    return Route(src=source, dest=dest)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="::", port=8000, workers=1)
    print("Done")
