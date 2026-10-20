def test_get_all(client):
    response = client.get("/inventory")
    assert response.status_code == 200
    assert len(response.get_json()) == 2


def test_get_one(client):
    response = client.get("/inventory/1")
    assert response.status_code == 200
    assert response.get_json()["id"] == 1


def test_get_one_not_found(client):
    response = client.get("/inventory/999")
    assert response.status_code == 404
    assert "error" in response.get_json()


def test_post_creates_item(client):
    payload = {"price": 50, "stock": 10, "product": {"product_name": "Biscuits", "brands": "Demo"}}
    response = client.post("/inventory", json=payload)
    assert response.status_code == 201
    body = response.get_json()
    assert body["id"] == 3
    assert body["product"]["product_name"] == "Biscuits"
    assert len(client.get("/inventory").get_json()) == 3


def test_post_missing_name(client):
    response = client.post("/inventory", json={"price": 10, "product": {}})
    assert response.status_code == 400


def test_post_invalid_json(client):
    response = client.post("/inventory", data="not json", content_type="text/plain")
    assert response.status_code == 400


def test_post_negative_price(client):
    payload = {"price": -5, "product": {"product_name": "Bad"}}
    assert client.post("/inventory", json=payload).status_code == 400


def test_patch_updates_only_sent_fields(client):
    response = client.patch("/inventory/1", json={"price": 700})
    assert response.status_code == 200
    body = response.get_json()
    assert body["price"] == 700
    assert body["stock"] == 24  # unchanged


def test_patch_not_found(client):
    assert client.patch("/inventory/999", json={"price": 1}).status_code == 404


def test_patch_invalid_stock(client):
    assert client.patch("/inventory/1", json={"stock": "many"}).status_code == 400


def test_delete_removes_item(client):
    response = client.delete("/inventory/1")
    assert response.status_code == 200
    assert client.get("/inventory/1").status_code == 404


def test_delete_not_found(client):
    assert client.delete("/inventory/999").status_code == 404


def test_new_id_not_reused_after_delete(client):
    client.delete("/inventory/2")
    payload = {"product": {"product_name": "New"}}
    assert client.post("/inventory", json=payload).get_json()["id"] == 2