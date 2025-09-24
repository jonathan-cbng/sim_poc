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

from typing import Any

from src.worker.comms import WorkerComms
from src.worker.worker_api import Address, HeartbeatStatsReq, HeartbeatStatsRsp

#######################################################################################################################
# Globals
#######################################################################################################################

nodes: dict[Address, Any] = {}

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

    def __init__(self, address: Address, comms: WorkerComms, http_client):
        """
        Initialize a Node instance and register it in the global nodes dictionary.

        Args:
            address (Address): The address of the node.
            comms (WorkerComms): Communication link to the controller.
        """
        self.comms = comms
        self.parent = nodes.get(address.parent, None)
        self.address = address
        self.http_client = http_client
        self.heartbeat_state = HeartbeatStatsRsp(address=self.address)
        nodes[self.address] = self

    def __del__(self):
        """
        Deregister the node from the global nodes dictionary upon deletion.
        """
        if self.address in nodes:
            del nodes[self.address]

    def record_hb(self, success: bool):
        """
        Update the heartbeat statistics for the RT and its parent AP.

        Args:
            success (bool): Whether the heartbeat was successful.
        """
        self.heartbeat_state.local.record(success)
        if self.parent:
            self.parent.record_child_hb(success)

    def record_child_hb(self, success: bool):
        """
        Update the heartbeat statistics for the RT and its parent AP.

        Args:
            success (bool): Whether the heartbeat was successful.
        """
        self.heartbeat_state.children.record(success)
        if self.parent:
            self.parent.record_child_hb(success)

    async def on_heartbeat_stats_req(self, req: HeartbeatStatsReq) -> HeartbeatStatsRsp:
        """
        Handle a request for the node's heartbeat statistics.

        Returns:
            APHeartbeatStatsRsp: The current heartbeat statistics of the AP.
        """

        result = self.heartbeat_state
        if req.reset:
            self.heartbeat_state = HeartbeatStatsRsp(address=self.address)
        return result


#######################################################################################################################
# End of file
#######################################################################################################################
