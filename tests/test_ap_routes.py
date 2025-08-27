from starlette.status import HTTP_200_OK, HTTP_201_CREATED, HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND


# Test: Create & start an AP (optionally with initial RTs)
def test_create_ap(test_client):
    resp = test_client.post("/ap/", json={"index": -1, "heartbeat_seconds": 10, "num_rts": 2})
    assert resp.status_code == HTTP_201_CREATED
    ap_id = resp.json()
    assert isinstance(ap_id, int)


# Test: List all APs
def test_list_aps(test_client):
    # Create two APs
    test_client.post("/ap/", json={"index": -1, "heartbeat_seconds": 10, "num_rts": 1})
    test_client.post("/ap/", json={"index": -1, "heartbeat_seconds": 20, "num_rts": 2})
    resp = test_client.get("/ap/")
    assert resp.status_code == HTTP_200_OK
    aps = resp.json()
    assert isinstance(aps, dict)
    assert len(aps) >= 2  # noqa: PLR2004


# Test: Get status for a single AP
def test_get_ap(test_client):
    num_rts = 3
    hb_seconds = 15

    create_resp = test_client.post("/ap/", json={"index": -1, "heartbeat_seconds": hb_seconds, "num_rts": num_rts})
    ap_id = create_resp.json()
    resp = test_client.get(f"/ap/{ap_id}")
    assert resp.status_code == HTTP_200_OK
    ap = resp.json()
    assert ap["index"] == ap_id
    assert ap["heartbeat_seconds"] == hb_seconds
    assert len(ap["rts"]) == num_rts


# Test: Delete an AP
def test_delete_ap(test_client):
    create_resp = test_client.post("/ap/", json={"index": -1, "heartbeat_seconds": 10, "num_rts": 1})
    ap_id = create_resp.json()
    del_resp = test_client.delete(f"/ap/{ap_id}")
    assert del_resp.status_code == HTTP_200_OK
    msg = del_resp.json()
    assert f"AP {ap_id} deleted" in msg["message"]
    # Confirm AP is gone
    get_resp = test_client.get(f"/ap/{ap_id}")
    assert get_resp.status_code == HTTP_404_NOT_FOUND


# Test: Delete a non-existent AP
def test_delete_nonexistent_ap(test_client):
    resp = test_client.delete("/ap/9999")
    assert resp.status_code == HTTP_404_NOT_FOUND
    data = resp.json()
    assert "not found" in data["detail"].lower()


# Test: Re-adding an AP with the same index fails
def test_readding_ap_fails(test_client):
    # Create an AP
    resp1 = test_client.post("/ap/", json={"index": -1, "heartbeat_seconds": 10, "num_rts": 1})
    assert resp1.status_code == HTTP_201_CREATED
    ap_id = resp1.json()
    # Try to create the same AP again with the same index
    resp2 = test_client.post("/ap/", json={"index": ap_id, "heartbeat_seconds": 10, "num_rts": 1})
    assert resp2.status_code == HTTP_400_BAD_REQUEST
    data = resp2.json()
    assert "already exists" in data["detail"].lower()
