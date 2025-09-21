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

from pydantic import BaseModel, PrivateAttr, RootModel, model_validator

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
        num_rts (int): Number of RTs to register (default from settings).
    """

    msg_type: Literal[MessageTypes.AP_REGISTER_REQ] = MessageTypes.AP_REGISTER_REQ
    hub_auid: str  # AUID of the hub to register with
    num_rts: int = settings.DEFAULT_RTS_PER_AP


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


#######################################################################################################################
# End of file
#######################################################################################################################
