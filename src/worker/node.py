"""
node.py

Defines the Node base class for network simulation worker nodes (APs and RTs).

This module provides the Node class, which is the base for all network nodes in the simulation, such as Access Points
(APs) and Remote Terminals (RTs). Each node is registered in a global nodes dictionary for lookup and management.
The class also handles automatic registration and deregistration of nodes to the global `nodes` dictionary.

Usage:
    Used internally by the worker process to manage node lifecycle and lookup.
"""
#######################################################################################################################
# Imports
#######################################################################################################################

from src.worker.api_types import Address
from src.worker.comms import WorkerComms

#######################################################################################################################
# Globals
#######################################################################################################################

nodes: dict[Address, "Node"] = {}

#######################################################################################################################
# Body
#######################################################################################################################


class Node:
    """
    Base class for network nodes (APs and RTs).

    Handles registration and deregistration of nodes in the global nodes dictionary.

    Args:
        address (Address): The address of the node.
        comms (WorkerComms): Communication link to the controller.
    """

    def __init__(self, address: Address, comms: WorkerComms):
        """
        Initialize a Node instance and register it in the global nodes dictionary.

        Args:
            address (Address): The address of the node.
            comms (WorkerComms): Communication link to the controller.
        """
        self.comms = comms
        self.address = address
        nodes[self.address] = self

    def __del__(self):
        """
        Deregister the node from the global nodes dictionary upon deletion.
        """
        if self.address in nodes:
            del nodes[self.address]


#######################################################################################################################
# End of file
#######################################################################################################################
