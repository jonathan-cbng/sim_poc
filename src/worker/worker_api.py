"""
Message and address models for AP worker API.

This module defines the data models for messages exchanged between the control plane and the AP worker process. It uses
Pydantic v2 models with a union type and a discriminator (msg_type) to enable robust, type-safe serialization and
deserialization of heterogeneous message types.

The key feature is the Message class, which uses the 'msg_type' field as a discriminator to automatically decode
incoming JSON into the correct message type (APConnectInd, APRegisterReq, or APRegisterInd).
"""
#######################################################################################################################
# Imports
#######################################################################################################################

import logging
from enum import StrEnum
from typing import Any, Literal

import zmq
import zmq.asyncio
from pydantic import BaseModel, Field, PrivateAttr, RootModel, model_validator

from src.config import settings

#######################################################################################################################
# Globals
#######################################################################################################################

logger = logging.getLogger(__name__)

#######################################################################################################################
# Body
#######################################################################################################################


class MessageTypes(StrEnum):
    """
    Enum for message types used as discriminators in AP worker API messages.
    """

    HUB_CONNECT_IND = "hub_connect_ind"
    AP_REGISTER_REQ = "ap_register_req"
    AP_REGISTER_IND = "ap_register_ind"


class Address(BaseModel):
    """
    Address model representing the hierarchical address of a node.

    Attributes:
        net (int | None): Network index in nms.
        hub (int | None): Hub index in nms
        ap (int | None): AP index in nms.
        rt (int | None): RT index nms.
    """

    net: int | None = None
    hub: int | None = None
    ap: int | None = None
    rt: int | None = None

    _tag: str = PrivateAttr()
    _hash: int = PrivateAttr()

    model_config = {"frozen": True}

    @model_validator(mode="after")
    def check_hierarchy(self):
        """
        Validates the address hierarchy and sets the tag.

        Raises:
            ValueError: If the address hierarchy is invalid.
        Returns:
            Address: The validated Address instance.
        """
        if self.rt is not None and self.ap is None:
            raise ValueError("If 'rt' is set, 'ap' must also be set.")
        if self.ap is not None and self.hub is None:
            raise ValueError("If 'ap' is set, 'hub' must also be set.")
        if self.hub is not None and self.net is None:
            raise ValueError("If 'hub' is set, 'net' must also be set.")
        # Set _tag after validation
        tag = ""
        tag += f"N{self.net:02x}" if self.net is not None else ""
        tag += f"H{self.hub:02x}" if self.hub is not None else ""
        tag += f"A{self.ap:02x}" if self.ap is not None else ""
        tag += f"R{self.rt:02x}" if self.rt is not None else ""
        object.__setattr__(self, "_tag", tag)
        object.__setattr__(self, "_hash", hash(tag))
        return self

    @property
    def tag(self) -> str:
        """
        Returns the string tag representation of the address.

        Returns:
            str: The tag string.
        """
        return self._tag

    def __hash__(self) -> int:
        return self._hash

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Address):
            return False
        return self._hash == other._hash


class BaseMessageBody(BaseModel):
    """
    Base class for all message body models.

    Attributes:
        address (Address): The address of the node associated with the message.
    """

    address: Address


class HubConnectInd(BaseMessageBody):
    """
    Message indicating a hub has connected.

    Attributes:
        msg_type (Literal['hub_connect_ind']): Discriminator for this message type.
        address (Address): The address of the hub that connected.
    """

    msg_type: Literal[MessageTypes.HUB_CONNECT_IND] = MessageTypes.HUB_CONNECT_IND


class APRegisterReq(BaseMessageBody):
    """
    Message requesting AP registration.

    Attributes:
        msg_type (Literal['ap_register_req']): Discriminator for this message type.
        hub_auid (str): AUID of the hub to register with.
        heartbeat_seconds (int): Heartbeat interval in seconds.
    """

    msg_type: Literal[MessageTypes.AP_REGISTER_REQ] = MessageTypes.AP_REGISTER_REQ
    auid: str = Field(description="The auid of this node")
    hub_auid: str = Field(description="AUID of the hub to register with")
    heartbeat_seconds: int = settings.DEFAULT_HEARTBEAT_SECONDS
    azimuth_deg: int = Field(..., description="Azimuth in degrees to set on the AP", ge=0, le=360)


class APRegisterRsp(BaseMessageBody):
    """
    Message indicating an AP has been registered.

    Attributes:
        msg_type (Literal['ap_register_ind']): Discriminator for this message type.
        registered_at (str): ISO8601 timestamp of registration.
    """

    msg_type: Literal[MessageTypes.AP_REGISTER_IND] = MessageTypes.AP_REGISTER_IND
    registered_at: str


class Message(RootModel[HubConnectInd | APRegisterReq | APRegisterRsp]):
    """
    Union wrapper for AP worker messages, using 'msg_type' as a discriminator.

    The Message class allows you to parse any supported message type from JSON, and will automatically instantiate
    the correct model based on the 'msg_type' field.

    Example:
        >>> from src.worker.worker_api import Message
        >>> msg_json = '{"msg_type": "hub_connect_ind", "address": {"net": 1, "hub": 2, "ap": 3}}'
        >>> msg = Message.model_validate_json(msg_json)
        >>> type(msg.root)
        <class 'src.worker.worker_api.HubConnectInd'>
        >>> msg.root.address.net
        1
        >>> msg2 = Message(APRegisterReq(msg_type="ap_register_req", hub_auid="hub1"))
        >>> msg2.model_dump_json()
        '{"msg_type":"ap_register_req","address":...,"hub_auid":"hub1","num_rts":...}'
    """

    model_config = {"discriminator": "msg_type"}


class WorkerCtrl:
    """
    Top-level manager for the NMS network simulator.

    This class is intended to be a singleton instance that manages all networks. As such it also manages the ZeroMQ
    context and sockets for communication with worker processes (which are children of HubManager instances).
    """

    simulator = None

    async def listener(self, simulator) -> None:
        """
        Listens for incoming messages on the PULL socket and processes them.

        simulator: The SimulatorManager instance to route messages to the correct node.
        """
        while True:
            msg_bytes = await self.zmq_pull.recv()
            tag, msg_bytes = msg_bytes.split(b" ", 1)
            try:
                msg = Message.model_validate_json(msg_bytes)
                msg = msg.root  # This is the actual message inside the wrapper.
                logging.debug("Rx %s->ctrl: %r", str(tag), msg)  # All messages from a worker have an ap_address
                address = msg.address
                node = simulator.get_node(address)
            except Exception as e:
                logging.warning(f"Received non-JSON message: {msg_bytes!r} ({e})")
                continue
            match msg.msg_type:
                case MessageTypes.HUB_CONNECT_IND:
                    node.on_connect_ind(msg)
                case MessageTypes.AP_REGISTER_IND:
                    node.on_register(msg)
                case _:
                    logging.warning(f"Unknown event type: {msg.msg_type}")

    def send(self, msg) -> None:
        """
        Send a message to an AP via the PUB socket.

        Args:
            msg: The message to send - this could be a Message, or one of the message subtypes.
        """
        msg = msg if isinstance(msg, Message) else Message(msg)
        tag = msg.root.address.tag
        logging.debug("Tx ctrl->%s: %r", tag, msg)

        pub_message = f"{tag} {msg.model_dump_json()}"
        self.zmq_pub.send_string(pub_message)

    def setup_zmq(self, app, pub_port: int, pull_port: int) -> None:
        """
        Sets up ZeroMQ PUB and PULL sockets and binds them to the specified ports.

        Args:
            app: FastAPI application instance
            pub_port (int): Port number for the PUB socket
            pull_port (int): Port number for the PULL socket
        """
        self.zmq_ctx = zmq.asyncio.Context()
        self.zmq_pub = self.zmq_ctx.socket(zmq.PUB)
        self.zmq_pub.bind(f"tcp://*:{pub_port}")
        self.zmq_pull = self.zmq_ctx.socket(zmq.PULL)
        self.zmq_pull.bind(f"tcp://*:{pull_port}")
        app.state.zmq_ctx = self.zmq_ctx
        app.state.zmq_pub = self.zmq_pub
        app.state.zmq_pull = self.zmq_pull

    def teardown_zmq(self, app) -> None:
        """
        Tears down ZeroMQ sockets and context.

        Args:
            app: FastAPI application instance
        """
        if self.zmq_pub:
            self.zmq_pub.close()
        if self.zmq_pull:
            self.zmq_pull.close()
        if self.zmq_ctx:
            self.zmq_ctx.term()
        app.state.zmq_ctx = None
        app.state.zmq_pub = None
        app.state.zmq_pull = None


worker_ctrl = WorkerCtrl()  # Singleton instance of the simulator manager - this is the top-level data structure

#######################################################################################################################
# End of file
#######################################################################################################################
