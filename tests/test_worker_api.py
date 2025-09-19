"""
Unit tests for worker_api message classes.

These tests verify that the Pydantic discriminator (msg_type) correctly enables encoding and decoding of union message
types via the Message wrapper. The focus is on ensuring that the discriminator field is handled as expected for all
message variants.
"""

import pytest
from pydantic import ValidationError

from src.worker.worker_api import Address, APRegisterInd, APRegisterReq, HubConnectInd, Message


class TestMessageClasses:
    """
    Tests for AP message classes focusing on correct discriminator (msg_type) handling in the Message union wrapper.
    """

    def test_message_ap_connect_ind(self):
        """
        Checks that the discriminator (msg_type) correctly identifies and decodes an APConnectInd message via the
        Message wrapper.
        """
        addr = Address(net=1, hub=2, ap=3)
        conn_ind = Message(HubConnectInd(address=addr))
        data = conn_ind.model_dump_json()
        result = Message.model_validate_json(data).root
        assert result.msg_type == "hub_connect_ind"
        assert isinstance(result, HubConnectInd)

    def test_message_ap_register_req(self):
        """
        Checks that the discriminator (msg_type) correctly identifies and decodes an APRegisterReq message via the
        Message wrapper.
        """
        addr = Address(net=1, hub=2, ap=3)
        msg = APRegisterReq(address=addr, hub_auid="hub_auid", num_rts=5)
        reg_req = Message(msg)
        data = reg_req.model_dump_json()
        result = Message.model_validate_json(data).root
        assert result.msg_type == "ap_register_req"
        assert isinstance(result, APRegisterReq)

    def test_message_ap_register_ind(self):
        """
        Checks that the discriminator (msg_type) correctly identifies and decodes an APRegistered message via the
        Message wrapper.
        """
        addr = Address(net=1, hub=2, ap=3)
        reg_ind = Message(APRegisterInd(address=addr, registered_at="2025-09-08T12:00:00Z"))
        data = reg_ind.model_dump_json()
        result = Message.model_validate_json(data).root
        assert result.msg_type == "ap_register_ind"
        assert isinstance(result, APRegisterInd)

    def test_message_invalid_type(self):
        """
        Checks that an unknown msg_type in the discriminator raises a ValidationError when decoding via the
        Message wrapper.
        """
        bad_json = '{"msg_type": "unknown", "address": {"net": 1, "hub": 2, "ap": 3}}'
        with pytest.raises(ValidationError):
            Message.model_validate_json(bad_json)
