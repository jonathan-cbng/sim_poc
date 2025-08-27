from fastapi import status


def test_root_redirect(test_client):
    """
    Check that GET / redirects to /docs
    """
    resp = test_client.get("/")
    assert resp.status_code == status.HTTP_200_OK
    # The TestClient follows redirects by default, so we should end up at /docs
    assert resp.url.path == "/docs"
