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

from pydantic import BaseModel, PrivateAttr, RootModel, model_validator

from src.config import settings


class MessageTypes(StrEnum):
    HUB_CONNECT_IND = "hub_connect_ind"
    AP_REGISTER_REQ = "ap_register_req"
    AP_REGISTER_IND = "ap_register_ind"


class Address(BaseModel):
    net: int | None = None
    hub: int | None = None
    ap: int | None = None
    rt: int | None = None

    _tag: str = PrivateAttr()

    @model_validator(mode="after")
    def check_hierarchy(self):
        if self.rt is not None and self.ap is None:
            raise ValueError("If 'rt' is set, 'ap' must also be set.")
        if self.ap is not None and self.hub is None:
            raise ValueError("If 'ap' is set, 'hub' must also be set.")
        if self.hub is not None and self.net is None:
            raise ValueError("If 'hub' is set, 'net' must also be set.")
        # Set _tag after validation
        self._tag = ""
        self._tag += f"N{self.net:02x}" if self.net is not None else ""
        self._tag += f"H{self.hub:02x}" if self.hub is not None else ""
        self._tag += f"A{self.ap:02x}" if self.ap is not None else ""
        self._tag += f"R{self.rt:02x}" if self.rt is not None else ""

        return self

    @property
    def tag(self) -> str:
        return self._tag


class HubConnectInd(BaseModel):
    """
    Message indicating an AP has connected.

    Attributes:
        msg_type (Literal['ap_connect_ind']): Discriminator for this message type.
        address (HubAddress): The address of the AP that connected.
    """

    msg_type: Literal[MessageTypes.HUB_CONNECT_IND] = MessageTypes.HUB_CONNECT_IND
    address: Address


class APRegisterReq(BaseModel):
    """
    Message requesting AP registration.

    Attributes:
        msg_type (Literal['ap_register_req']): Discriminator for this message type.
    """

    msg_type: Literal[MessageTypes.AP_REGISTER_REQ] = MessageTypes.AP_REGISTER_REQ
    hub_auid: str  # AUID of the hub to register with
    num_rts: int = settings.DEFAULT_RTS_PER_AP


class APRegisterInd(BaseModel):
    """
    Message indicating an AP has been registered.

    Attributes:
        msg_type (Literal['ap_register_ind']): Discriminator for this message type.
        ap_address (Address): The address of the registered AP.
        registered_at (str): ISO8601 timestamp of registration.
    """

    msg_type: Literal[MessageTypes.AP_REGISTER_IND] = MessageTypes.AP_REGISTER_IND
    address: Address
    registered_at: str


class Message(RootModel[HubConnectInd | APRegisterReq | APRegisterInd]):
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
        >>> msg.root.address.net
        1
        >>> msg2 = Message(APRegisterReq(msg_type="ap_register_req"))
        >>> msg2.model_dump_json()
        '{"msg_type":"ap_register_req"}'
    """

    model_config = {"discriminator": "msg_type"}
