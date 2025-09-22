"""
rt.py

Defines the RT (Remote Terminal) class for the network simulation worker. Handles RT state and communication with the
controller.

This module is responsible for simulating Remote Terminals (RTs) in the network simulation. The RT class inherits from
Node and communicates with the controller via WorkerComms.

Usage:
    Used internally by the worker process to manage RT lifecycle and state.
"""
#######################################################################################################################
# Imports
#######################################################################################################################

from src.worker.comms import WorkerComms
from src.worker.node import Node

#######################################################################################################################
# Globals
#######################################################################################################################

#######################################################################################################################
# Body
#######################################################################################################################


class RT(Node):
    """
    Class representing a Remote Terminal (RT) in the network simulation.

    Handles RT state and communication with the controller.

    Args:
        address: The address of the RT node.
        comms (WorkerComms): Communication link to the controller.
    """

    def __init__(self, address, comms: WorkerComms):
        """
        Initialize an RT instance.

        Args:
            address: The address of the RT node.
            comms (WorkerComms): Communication link to the controller.
        """
        super().__init__(address, comms)
        self.parent_auid = None
        self.heartbeat_secs = None
        self.auid = None


#######################################################################################################################
# End of file
#######################################################################################################################
