"""
Unit tests for worker_api message classes.

These tests verify that the Pydantic discriminator (msg_type) correctly enables encoding and decoding of union message
types via the Message wrapper. The focus is on ensuring that the discriminator field is handled as expected for all
message variants.
"""
# ruff: noqa: PLR2004
#######################################################################################################################
# Imports
#######################################################################################################################

import pytest
from pydantic import ValidationError

from src.worker.worker_api_types import Address, APRegisterReq, APRegisterRsp, HubConnectInd, Message

#######################################################################################################################
# Body
#######################################################################################################################


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
        reg_ind = Message(APRegisterRsp(address=addr, registered_at="2025-09-08T12:00:00Z"))
        data = reg_ind.model_dump_json()
        result = Message.model_validate_json(data).root
        assert result.msg_type == "ap_register_ind"
        assert isinstance(result, APRegisterRsp)

    def test_message_invalid_type(self):
        """
        Checks that an unknown msg_type in the discriminator raises a ValidationError when decoding via the
        Message wrapper.
        """
        bad_json = '{"msg_type": "unknown", "address": {"net": 1, "hub": 2, "ap": 3}}'
        with pytest.raises(ValidationError):
            Message.model_validate_json(bad_json)


class TestAddress:
    """
    Unit tests for the Address model, verifying hierarchy validation, immutability, equality, hashing, and
    representation.
    """

    def test_valid_hierarchy(self):
        """
        Test that a valid Address hierarchy is accepted and the tag is generated correctly.
        """
        addr = Address(net=1, hub=2, ap=3, rt=4)
        assert addr.net == 1
        assert addr.hub == 2
        assert addr.ap == 3
        assert addr.rt == 4
        assert addr.tag == "N01H02A03R04"

    def test_invalid_hierarchy_rt_without_ap(self):
        """
        Test that setting 'rt' without 'ap' raises a ValueError.
        """
        with pytest.raises(ValueError):
            Address(net=1, hub=2, rt=4)

    def test_invalid_hierarchy_ap_without_hub(self):
        """
        Test that setting 'ap' without 'hub' raises a ValueError.
        """
        with pytest.raises(ValueError):
            Address(net=1, ap=3)

    def test_invalid_hierarchy_hub_without_net(self):
        """
        Test that setting 'hub' without 'net' raises a ValueError.
        """
        with pytest.raises(ValueError):
            Address(hub=2)

    def test_immutable_fields(self):
        """
        Test that Address fields are immutable after instantiation.
        """
        addr = Address(net=1, hub=2, ap=3)
        with pytest.raises(ValidationError):
            addr.net = 99
        with pytest.raises(ValidationError):
            addr.hub = 99
        with pytest.raises(ValidationError):
            addr.ap = 99
        with pytest.raises(ValidationError):
            addr.rt = 99

    def test_hash_and_equality(self):
        """
        Test that Address instances with the same values are equal and hash to the same value.
        """
        addr1 = Address(net=1, hub=2, ap=3)
        addr2 = Address(net=1, hub=2, ap=3)
        addr3 = Address(net=1, hub=2, ap=4)
        assert addr1 == addr2
        assert hash(addr1) == hash(addr2)
        assert addr1 != addr3
        d = {addr1: "foo"}
        assert d[addr2] == "foo"

    def test_repr(self):
        """
        Test that the repr of Address contains the class name and is evaluable to an equal object.
        """
        addr = Address(net=1, hub=2, ap=3)
        assert "Address" in repr(addr)
        assert eval(repr(addr)) == addr


#######################################################################################################################
# End of file
#######################################################################################################################
