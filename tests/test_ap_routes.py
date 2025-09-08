import time

from starlette.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_404_NOT_FOUND

from src.controller.common import APState


# Helper to create a network and return its index
def create_network(client, **kwargs):
    req = {
        "csni": "test-csni",
        "hubs": 0,
        "aps_per_hub": 0,
        "ap_heartbeat_seconds": 10,
        "rts_per_ap": 0,
        "rt_heartbeat_seconds": 10,
    }
    req.update(kwargs)
    resp = client.post("/network/", json=req)
    assert resp.status_code == HTTP_201_CREATED
    return resp.json()


# Helper to create a hub and return its index
def create_hub(client, network_idx, **kwargs):
    req = {"num_aps": 0, "num_rts_per_ap": 0, "heartbeat_seconds": 10}
    req.update(kwargs)
    resp = client.post(f"/network/{network_idx}/hub/", json=req)
    assert resp.status_code == HTTP_201_CREATED
    return resp.json()


# Test: Create & start an AP (optionally with initial RTs)
def test_create_ap(test_client):
    network_idx = create_network(test_client)
    hub_idx = create_hub(test_client, network_idx)
    resp = test_client.post(
        f"/network/{network_idx}/hub/{hub_idx}/ap/",
        json={"heartbeat_seconds": 10, "num_rts": 2, "rt_heartbeat_seconds": 10},
    )
    assert resp.status_code == HTTP_201_CREATED
    ap_id = resp.json()
    assert isinstance(ap_id, int)
    # Wait for AP to reach CONNECTED state
    timeout = 1.0
    interval = 0.1
    start = time.time()
    while True:
        status_resp = test_client.get(f"/network/{network_idx}/hub/{hub_idx}/ap/{ap_id}")
        assert status_resp.status_code == HTTP_200_OK
        ap = status_resp.json()
        if ap.get("state") == APState.REGISTERED:
            break
        if time.time() - start > timeout:
            raise AssertionError(f"AP did not reach REGISTERED state. last state: {ap.get('state')}")
        time.sleep(interval)


# Test: List all APs
def test_list_aps(test_client):
    network_idx = create_network(test_client)
    hub_idx = create_hub(test_client, network_idx)
    test_client.post(
        f"/network/{network_idx}/hub/{hub_idx}/ap/",
        json={"heartbeat_seconds": 10, "num_rts": 1, "rt_heartbeat_seconds": 10},
    )
    test_client.post(
        f"/network/{network_idx}/hub/{hub_idx}/ap/",
        json={"heartbeat_seconds": 20, "num_rts": 2, "rt_heartbeat_seconds": 10},
    )
    resp = test_client.get(f"/network/{network_idx}/hub/{hub_idx}/ap/")
    assert resp.status_code == HTTP_200_OK
    aps = resp.json()
    assert isinstance(aps, dict)
    assert len(aps) >= 2  # noqa: PLR2004


# Test: Get status for a single AP
def test_get_ap(test_client):
    network_idx = create_network(test_client)
    hub_idx = create_hub(test_client, network_idx)
    num_rts = 3
    hb_seconds = 15
    create_resp = test_client.post(
        f"/network/{network_idx}/hub/{hub_idx}/ap/",
        json={"heartbeat_seconds": hb_seconds, "num_rts": num_rts, "rt_heartbeat_seconds": 10},
    )
    ap_id = create_resp.json()
    resp = test_client.get(f"/network/{network_idx}/hub/{hub_idx}/ap/{ap_id}")
    assert resp.status_code == HTTP_200_OK
    ap = resp.json()
    assert ap["index"] == ap_id
    assert ap["heartbeat_seconds"] == hb_seconds
    assert len(ap["children"]) == num_rts


# Test: Delete an AP
def test_delete_ap(test_client):
    network_idx = create_network(test_client)
    hub_idx = create_hub(test_client, network_idx)
    create_resp = test_client.post(
        f"/network/{network_idx}/hub/{hub_idx}/ap/",
        json={"heartbeat_seconds": 10, "num_rts": 1, "rt_heartbeat_seconds": 10},
    )
    ap_id = create_resp.json()
    del_resp = test_client.delete(f"/network/{network_idx}/hub/{hub_idx}/ap/{ap_id}")
    assert del_resp.status_code == HTTP_200_OK
    msg = del_resp.json()
    assert f"AP {ap_id} deleted" in msg["message"]
    # Confirm AP is gone
    get_resp = test_client.get(f"/network/{network_idx}/hub/{hub_idx}/ap/{ap_id}")
    assert get_resp.status_code == HTTP_404_NOT_FOUND


# Test: Delete a non-existent AP
def test_delete_nonexistent_ap(test_client):
    network_idx = create_network(test_client)
    hub_idx = create_hub(test_client, network_idx)
    resp = test_client.delete(f"/network/{network_idx}/hub/{hub_idx}/ap/9999")
    assert resp.status_code == HTTP_404_NOT_FOUND
    data = resp.json()
    assert "not found" in data["detail"].lower()
