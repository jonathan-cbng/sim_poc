import logging

import zmq.asyncio
from fastapi import HTTPException
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND

from src.models import AP, RT, APCreateRequest


class APController:
    aps: dict[int, AP] = {}
    zmq_ctx: zmq.asyncio.Context = None
    zmq_pub: zmq.asyncio.Socket = None
    zmq_pull: zmq.asyncio.Socket = None

    async def add_ap(self, req: APCreateRequest) -> int:
        """
        Create & start an AP (optionally with initial RTs). If req.ap_id is
        -1, then a new ID will be assigned automatically. Once added to the local list,
        we start the AP simulator process.
        """
        index = req.index
        if index < 0:
            try:
                index = max(self.aps.keys()) + 1
            except ValueError:  # if aps is empty
                index = 0
        elif index in self.aps:
            raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=f"AP {index} already exists")
        rts = [RT(index=i, heartbeat_seconds=req.heartbeat_seconds) for i in range(req.num_rts)]
        new_ap = AP(index=index, heartbeat_seconds=req.heartbeat_seconds, rts=rts)
        self.aps[index] = new_ap
        logging.info("Created AP %d with %d RTs", index, req)
        return index

    async def remove_ap(self, id):
        """
        Stop and remove an AP and all underlying RTs. Once the AP has indicated it has stopped,
        then the handling process can also be terminated.
        """
        if id not in self.aps:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="AP not found")
        del self.aps[id]
        logging.info("Removed AP %d", id)

    async def listener(self):
        """
        Listens for incoming messages on the PULL socket and processes them.
        """
        while True:
            msg = await self.zmq_pull.recv()
            logging.debug("Received message: `%s`", msg)

    def setup_zmq(self, app, pub_port, pull_port):
        """
        Sets up ZeroMQ PUB and PULL sockets and binds them to the specified ports.

        :param app: FastAPI application instance
        :param pub_port: Port number for the PUB socket
        :param pull_port: Port number for the PULL socket
        :return: Tuple containing the PUB and PULL sockets
        """
        ctx = zmq.asyncio.Context()
        pub = ctx.socket(zmq.PUB)
        pub.bind(f"tcp://*:{pub_port}")
        pull = ctx.socket(zmq.PULL)
        pull.bind(f"tcp://*:{pull_port}")
        self.zmq_ctx = ctx
        self.zmq_pub = pub
        self.zmq_pull = pull

        return pub, pull

    def teardown_zmq(self, app):
        """
        Closes the PUB and PULL sockets and terminates the context.
        :param app: FastAPI application instance
        """
        if self.zmq_pub:
            self.zmq_pub.close()
            self.zmq_pub = None
        if self.zmq_pull:
            self.zmq_pull.close()
            self.zmq_pull = None
        if self.zmq_ctx:
            self.zmq_ctx.term()
            self.zmq_ctx = None


ap_ctrl = APController()
