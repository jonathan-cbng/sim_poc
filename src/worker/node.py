from src.worker.api_types import Address
from src.worker.comms import WorkerComms


class Node:
    """Base class for network nodes (APs and RTs)."""

    def __init__(self, address, comms: WorkerComms):
        self.comms = comms
        self.address = address
        nodes[self.address] = self

    def __del__(self):
        del nodes[self.address]


nodes: dict[Address, Node] = {}
