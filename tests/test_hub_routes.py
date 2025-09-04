from starlette.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_404_NOT_FOUND


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


# Test: Create a hub (with default APs/RTs)
def test_create_hub_minimal(test_client):
    network_idx = create_network(test_client)
    resp = test_client.post(
        f"/network/{network_idx}/hub/", json={"num_aps": 0, "num_rts_per_ap": 0, "heartbeat_seconds": 10}
    )
    assert resp.status_code == HTTP_201_CREATED
    hub_id = resp.json()
    assert isinstance(hub_id, int)


# Test: Create a hub with APs and RTs
def test_create_hub_with_aps_rts(test_client):
    network_idx = create_network(test_client)
    num_aps = 2
    num_rts = 3
    resp = test_client.post(
        f"/network/{network_idx}/hub/", json={"num_aps": num_aps, "num_rts_per_ap": num_rts, "heartbeat_seconds": 10}
    )
    assert resp.status_code == HTTP_201_CREATED
    hub_id = resp.json()
    # Get the hub and check children
    hub_resp = test_client.get(f"/network/{network_idx}/hub/{hub_id}")
    assert hub_resp.status_code == HTTP_200_OK
    hub = hub_resp.json()
    assert len(hub["children"]) == num_aps
    for ap in hub["children"].values():
        assert len(ap["children"]) == num_rts


# Test: List all hubs
def test_list_hubs(test_client):
    network_idx = create_network(test_client)
    test_client.post(f"/network/{network_idx}/hub/", json={"num_aps": 1, "num_rts_per_ap": 1, "heartbeat_seconds": 10})
    test_client.post(f"/network/{network_idx}/hub/", json={"num_aps": 2, "num_rts_per_ap": 2, "heartbeat_seconds": 10})
    resp = test_client.get(f"/network/{network_idx}/hub/")
    assert resp.status_code == HTTP_200_OK
    hubs = resp.json()
    assert isinstance(hubs, dict)
    assert len(hubs) >= 2  # noqa: PLR2004


# Test: Get a single hub
def test_get_hub(test_client):
    network_idx = create_network(test_client)
    create_resp = test_client.post(
        f"/network/{network_idx}/hub/", json={"num_aps": 1, "num_rts_per_ap": 2, "heartbeat_seconds": 10}
    )
    hub_id = create_resp.json()
    resp = test_client.get(f"/network/{network_idx}/hub/{hub_id}")
    assert resp.status_code == HTTP_200_OK
    hub = resp.json()
    assert hub["index"] == hub_id
    assert len(hub["children"]) == 1


# Test: Get a non-existent hub
def test_get_nonexistent_hub(test_client):
    network_idx = create_network(test_client)
    resp = test_client.get(f"/network/{network_idx}/hub/9999")
    assert resp.status_code == HTTP_404_NOT_FOUND
    data = resp.json()
    assert "not found" in data["detail"].lower()


# Test: Delete a hub
def test_delete_hub(test_client):
    network_idx = create_network(test_client)
    create_resp = test_client.post(
        f"/network/{network_idx}/hub/", json={"num_aps": 1, "num_rts_per_ap": 1, "heartbeat_seconds": 10}
    )
    hub_id = create_resp.json()
    del_resp = test_client.delete(f"/network/{network_idx}/hub/{hub_id}")
    assert del_resp.status_code == HTTP_200_OK
    msg = del_resp.json()
    assert f"Hub {hub_id} deleted" in msg["message"]
    # Confirm hub is gone
    get_resp = test_client.get(f"/network/{network_idx}/hub/{hub_id}")
    assert get_resp.status_code == HTTP_404_NOT_FOUND


# Test: Delete a non-existent hub
def test_delete_nonexistent_hub(test_client):
    network_idx = create_network(test_client)
    resp = test_client.delete(f"/network/{network_idx}/hub/9999")
    assert resp.status_code == HTTP_404_NOT_FOUND
    data = resp.json()
    assert "not found" in data["detail"].lower()


# Test: Deleting a hub removes its APs
def test_delete_hub_removes_aps(test_client):
    network_idx = create_network(test_client)
    resp = test_client.post(
        f"/network/{network_idx}/hub/", json={"num_aps": 2, "num_rts_per_ap": 1, "heartbeat_seconds": 10}
    )
    hub_id = resp.json()
    hub = test_client.get(f"/network/{network_idx}/hub/{hub_id}").json()
    ap_ids = [int(ap_id) for ap_id in hub["children"]]
    test_client.delete(f"/network/{network_idx}/hub/{hub_id}")
    for ap_id in ap_ids:
        ap_resp = test_client.get(f"/network/{network_idx}/hub/{hub_id}/ap/{ap_id}")
        assert ap_resp.status_code == HTTP_404_NOT_FOUND
