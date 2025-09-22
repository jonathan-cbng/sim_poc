from src.worker.comms import WorkerComms
from src.worker.node import Node


class RT(Node):
    def __init__(self, address, comms: WorkerComms):
        """
        Class representing a Remote Terminal (RT) in the network simulation.
        """
        super().__init__(address, comms)
        self.parent_auid = None
        self.heartbeat_secs = None
        self.auid = None
