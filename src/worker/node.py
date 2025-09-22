from src.worker.comms import ControllerLink
from src.worker.worker_api_types import Address


class Node:
    """Base class for network nodes (APs and RTs)."""

    def __init__(self, address, comms: ControllerLink):
        self.comms = comms
        self.address = address
        nodes[self.address] = self

    def __del__(self):
        del nodes[self.address]


nodes: dict[Address, Node] = {}
