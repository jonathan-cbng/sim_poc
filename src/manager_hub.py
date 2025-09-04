import logging
import uuid

from pydantic import Field

from src.common import AP, RT, Node
from src.models_api import APCreateRequest


class HubManager(Node):
    children: dict[int, AP] = {}
    auid: str = Field(default_factory=uuid.uuid4)

    async def add_ap(self, req: APCreateRequest, index=-1) -> AP:
        """
        Create & start an AP (optionally with initial RTs). If req.ap_id is
        -1, then a new ID will be assigned automatically. Once added to the local list,
        we start the AP simulator process.

        :param req: APCreateRequest object containing parameters for the new AP
        :return: The created AP object
        :raises HTTPException: If the specified index already exists

        """
        index = self.get_index(index)  # Will throw HTTPError if already exists
        new_ap = AP(index=index, parent_index=self.index, heartbeat_seconds=req.heartbeat_seconds)
        rts = {
            i: RT(index=i, parent_index=new_ap.index, heartbeat_seconds=req.heartbeat_seconds)
            for i in range(req.num_rts)
        }
        new_ap.children = rts
        self.children[index] = new_ap
        logging.info("Created AP %d with %d RTs", index, req.num_rts)
        return new_ap

    async def remove_ap(self, id):
        """
        Stop and remove an AP and all underlying RTs. Once the AP has indicated it has stopped,
        then the handling process can also be terminated.
        """
        logging.info("Removing AP %d", id)
        self.remove_child(id)

    def get_ap(self, index) -> AP:
        return self.get_child_or_404(index)
