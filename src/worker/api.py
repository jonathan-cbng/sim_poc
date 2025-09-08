"""
Message and address models for AP worker API.

This module defines the data models for messages exchanged between the control plane and the AP worker process. It uses
Pydantic v2 models with a union type and a discriminator (msg_type) to enable robust, type-safe serialization and
deserialization of heterogeneous message types.

The key feature is the Message class, which uses the 'msg_type' field as a discriminator to automatically decode
incoming JSON into the correct message type (APConnectInd, APRegisterReq, or APRegistered).
"""

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, RootModel


class MessageTypes(StrEnum):
    AP_CONNECT_IND = "ap_connect_ind"
    AP_REGISTER_REQ = "ap_register_req"
    AP_REGISTER_IND = "ap_register_ind"


class ApAddress(BaseModel):
    """
    Address of an Access Point (AP) in the simulated network.

    Attributes:
        net (int): Network index.
        hub (int): Hub index within the network.
        ap (int): AP index within the hub.
    """

    net: int
    hub: int
    ap: int

    def get_ap(self, nms):
        """
        Resolve this address to an AP object in the given NMS.

        Args:
            nms: The network management system instance.

        Returns:
            The AP object at this address.
        """
        return nms.get_network(self.net).get_hub(self.hub).get_ap(self.ap)


class APConnectInd(BaseModel):
    """
    Message indicating an AP has connected.

    Attributes:
        msg_type (Literal['ap_connect_ind']): Discriminator for this message type.
        ap_address (ApAddress): The address of the AP that connected.
    """

    msg_type: Literal[MessageTypes.AP_CONNECT_IND] = MessageTypes.AP_CONNECT_IND
    ap_address: ApAddress


class APRegisterReq(BaseModel):
    """
    Message requesting AP registration.

    Attributes:
        msg_type (Literal['ap_register_req']): Discriminator for this message type.
    """

    msg_type: Literal[MessageTypes.AP_REGISTER_REQ] = MessageTypes.AP_REGISTER_REQ


class APRegisterInd(BaseModel):
    """
    Message indicating an AP has been registered.

    Attributes:
        msg_type (Literal['ap_register_ind']): Discriminator for this message type.
        ap_address (ApAddress): The address of the registered AP.
        registered_at (str): ISO8601 timestamp of registration.
    """

    msg_type: Literal[MessageTypes.AP_REGISTER_IND] = MessageTypes.AP_REGISTER_IND
    ap_address: ApAddress
    registered_at: str


class Message(RootModel[APConnectInd | APRegisterReq | APRegisterInd]):
    """
    Union wrapper for AP worker messages, using 'msg_type' as a discriminator.

    The Message class allows you to parse any supported message type from JSON, and will automatically instantiate
    the correct model based on the 'msg_type' field.

    Example:
        >>> from src.worker.api import Message
        >>> msg_json = '{"msg_type": "ap_connect_ind", "ap_address": {"net": 1, "hub": 2, "ap": 3}}'
        >>> msg = Message.model_validate_json(msg_json)
        >>> type(msg.root)
        <class 'src.worker_api.APConnectInd'>
        >>> msg.root.ap_address.net
        1
        >>> msg2 = Message(APRegisterReq(msg_type="ap_register_req"))
        >>> msg2.model_dump_json()
        '{"msg_type":"ap_register_req"}'
    """

    model_config = {"discriminator": "msg_type"}
