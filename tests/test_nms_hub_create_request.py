from src.nms_api import NmsHubCreateRequest


def test_hub_create_request_autofill():
    req = NmsHubCreateRequest(csni="test-csni")
    assert req.auid is not None
    assert req.id == f"ID_{req.auid}"
    assert req.name == f"NAME_{req.auid}"


def test_hub_create_request_preserve_id_name():
    req = NmsHubCreateRequest(csni="test-csni", id="custom_id", name="custom_name")
    assert req.id == "custom_id"
    assert req.name == "custom_name"
    assert req.auid is not None


def test_hub_create_request_empty_id_name():
    req = NmsHubCreateRequest(csni="test-csni", id="", name="")
    assert req.id == f"ID_{req.auid}"
    assert req.name == f"NAME_{req.auid}"
