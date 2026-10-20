from unittest.mock import Mock, patch

import pytest
import requests

import openfoodfacts
from openfoodfacts import OpenFoodFactsError

SAMPLE = {
    "status": 1,
    "product": {
        "product_name": "Organic Almond Milk",
        "brands": "Silk",
        "ingredients_text": "Filtered water, almonds, cane sugar",
    },
}


def fake_response(json_data):
    response = Mock()
    response.json.return_value = json_data
    response.raise_for_status.return_value = None
    return response


# ---- client functions (requests.get is mocked) ----

def test_fetch_by_barcode_found():
    api_data = {"status": 1, "product": {"product_name": "Almond Milk", "brands": "Silk", "ingredients_text": "water"}}
    with patch("openfoodfacts.requests.get", return_value=fake_response(api_data)):
        result = openfoodfacts.fetch_by_barcode("123456")
    assert result["status"] == 1
    assert result["product"]["product_name"] == "Almond Milk"


def test_fetch_by_barcode_not_found():
    with patch("openfoodfacts.requests.get", return_value=fake_response({"status": 0})):
        assert openfoodfacts.fetch_by_barcode("123456") is None


def test_fetch_by_barcode_non_numeric():
    assert openfoodfacts.fetch_by_barcode("abc") is None


def test_fetch_by_barcode_network_error():
    with patch("openfoodfacts.requests.get", side_effect=requests.ConnectionError("down")):
        with pytest.raises(OpenFoodFactsError):
            openfoodfacts.fetch_by_barcode("123456")


def test_fetch_by_barcode_http_error():
    response = Mock()
    response.raise_for_status.side_effect = requests.HTTPError("500")
    with patch("openfoodfacts.requests.get", return_value=response):
        with pytest.raises(OpenFoodFactsError):
            openfoodfacts.fetch_by_barcode("123456")


def test_search_by_name_returns_matches_and_skips_unnamed():
    api_data = {"products": [
        {"code": "1", "product_name": "A", "brands": "B", "ingredients_text": "C"},
        {"code": "2"},
    ]}
    with patch("openfoodfacts.requests.get", return_value=fake_response(api_data)):
        results = openfoodfacts.search_by_name("milk")
    assert len(results) == 1
    assert results[0]["barcode"] == "1"


def test_search_by_name_empty_query():
    assert openfoodfacts.search_by_name("   ") == []


# ---- Flask routes that use the client (client functions are mocked) ----

def test_lookup_by_barcode(client):
    with patch("app.openfoodfacts.fetch_by_barcode", return_value=SAMPLE):
        response = client.get("/lookup?barcode=123")
    assert response.status_code == 200
    assert response.get_json()["product"]["brands"] == "Silk"


def test_lookup_by_name(client):
    matches = [{"barcode": "1", "status": 1, "product": SAMPLE["product"]}]
    with patch("app.openfoodfacts.search_by_name", return_value=matches):
        response = client.get("/lookup?name=almond")
    assert response.status_code == 200
    assert len(response.get_json()) == 1


def test_lookup_requires_parameter(client):
    assert client.get("/lookup").status_code == 400


def test_lookup_not_found(client):
    with patch("app.openfoodfacts.fetch_by_barcode", return_value=None):
        assert client.get("/lookup?barcode=123").status_code == 404


def test_lookup_api_failure_returns_502(client):
    with patch("app.openfoodfacts.fetch_by_barcode", side_effect=OpenFoodFactsError("down")):
        assert client.get("/lookup?barcode=123").status_code == 502


def test_import_adds_item_to_inventory(client):
    with patch("app.openfoodfacts.fetch_by_barcode", return_value=SAMPLE):
        response = client.post("/inventory/import", json={"barcode": "123", "price": 100, "stock": 5})
    assert response.status_code == 201
    assert response.get_json()["product"]["product_name"] == "Organic Almond Milk"
    assert len(client.get("/inventory").get_json()) == 3


def test_import_requires_barcode(client):
    assert client.post("/inventory/import", json={"price": 1}).status_code == 400


def test_import_not_found(client):
    with patch("app.openfoodfacts.fetch_by_barcode", return_value=None):
        assert client.post("/inventory/import", json={"barcode": "123"}).status_code == 404


def test_import_api_failure(client):
    with patch("app.openfoodfacts.fetch_by_barcode", side_effect=OpenFoodFactsError("down")):
        assert client.post("/inventory/import", json={"barcode": "123"}).status_code == 502


def test_enrich_existing_item_by_barcode(client):
    with patch("app.openfoodfacts.fetch_by_barcode", return_value=SAMPLE):
        response = client.post("/inventory/1/enrich")
    assert response.status_code == 200
    assert response.get_json()["product"]["ingredients_text"] == "Filtered water, almonds, cane sugar"
    assert response.get_json()["price"] == 650.00  # our own data untouched


def test_enrich_by_name_when_no_barcode(client):
    created = client.post("/inventory", json={"product": {"product_name": "Almond Milk"}}).get_json()
    matches = [{"barcode": "999", "status": 1, "product": SAMPLE["product"]}]
    with patch("app.openfoodfacts.search_by_name", return_value=matches):
        response = client.post(f"/inventory/{created['id']}/enrich")
    assert response.status_code == 200
    assert response.get_json()["barcode"] == "999"


def test_enrich_item_not_found(client):
    assert client.post("/inventory/999/enrich").status_code == 404