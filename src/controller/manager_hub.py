import logging
import uuid

from pydantic import Field

from src.controller.api import APCreateRequest
from src.controller.common import AP, RT, ControllerNode


class HubManager(ControllerNode):
    children: dict[int, AP] = {}
    auid: str = Field(default_factory=uuid.uuid4)

    async def add_ap(self, req: APCreateRequest, ap_idx=-1) -> AP:
        """
        Create & start an AP (optionally with initial RTs). If req.ap_id is
        -1, then a new ID will be assigned automatically. Once added to the local list,
        we start the AP simulator process.

        :param req: APCreateRequest object containing parameters for the new AP
        :return: The created AP object
        :raises HTTPException: If the specified index already exists

        """
        ap_idx = self.get_index(ap_idx)  # Will throw HTTPError if already exists
        new_ap = AP(index=ap_idx, parent_index=self.index, heartbeat_seconds=req.heartbeat_seconds)
        rts = {
            i: RT(index=i, parent_index=new_ap.index, heartbeat_seconds=req.heartbeat_seconds)
            for i in range(req.num_rts)
        }
        new_ap.children = rts
        self.children[ap_idx] = new_ap
        logging.info("Created AP %d with %d RTs", ap_idx, req.num_rts)
        new_ap.start_worker(self.parent_index, self.index, ap_idx)
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
