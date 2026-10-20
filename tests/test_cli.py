from unittest.mock import Mock, patch

import requests

import cli

ITEM = {
    "id": 1, "barcode": "123", "price": 650.0, "stock": 24, "status": 1,
    "product": {"product_name": "Hazelnut Spread", "brands": "Nutella", "ingredients_text": "Sugar"},
}


def fake_response(json_data, status=200):
    response = Mock()
    response.ok = status < 400
    response.status_code = status
    response.json.return_value = json_data
    return response


def test_list_prints_items(capsys):
    with patch("cli.requests.request", return_value=fake_response([ITEM])):
        code = cli.main(["list"])
    assert code == 0
    assert "Hazelnut Spread" in capsys.readouterr().out


def test_list_empty(capsys):
    with patch("cli.requests.request", return_value=fake_response([])):
        assert cli.main(["list"]) == 0
    assert "empty" in capsys.readouterr().out.lower()


def test_view_item(capsys):
    with patch("cli.requests.request", return_value=fake_response(ITEM)):
        assert cli.main(["view", "1"]) == 0
    assert "Nutella" in capsys.readouterr().out


def test_view_not_found(capsys):
    with patch("cli.requests.request", return_value=fake_response({"error": "Item 9 not found"}, 404)):
        assert cli.main(["view", "9"]) == 1
    assert "not found" in capsys.readouterr().out


def test_add_sends_correct_payload():
    with patch("cli.requests.request", return_value=fake_response(ITEM, 201)) as mock_request:
        code = cli.main(["add", "--name", "Milk", "--brand", "Brookside", "--price", "60", "--stock", "30"])
    assert code == 0
    assert mock_request.call_args.args[0] == "POST"
    payload = mock_request.call_args.kwargs["json"]
    assert payload["product"]["product_name"] == "Milk"
    assert payload["price"] == 60.0
    assert payload["stock"] == 30


def test_update_sends_patch():
    with patch("cli.requests.request", return_value=fake_response(ITEM)) as mock_request:
        assert cli.main(["update", "1", "--price", "700", "--stock", "20"]) == 0
    assert mock_request.call_args.args[0] == "PATCH"
    assert mock_request.call_args.kwargs["json"] == {"price": 700.0, "stock": 20}


def test_update_requires_a_field(capsys):
    with patch("cli.requests.request") as mock_request:
        assert cli.main(["update", "1"]) == 1
    mock_request.assert_not_called()
    assert "provide" in capsys.readouterr().out.lower()


def test_delete(capsys):
    with patch("cli.requests.request", return_value=fake_response({"message": "Item 1 deleted"})) as mock_request:
        assert cli.main(["delete", "1"]) == 0
    assert mock_request.call_args.args[0] == "DELETE"
    assert "deleted" in capsys.readouterr().out


def test_find_by_barcode(capsys):
    result = {"status": 1, "product": ITEM["product"]}
    with patch("cli.requests.request", return_value=fake_response(result)) as mock_request:
        assert cli.main(["find", "--barcode", "123"]) == 0
    assert mock_request.call_args.kwargs["params"] == {"barcode": "123"}
    assert "Hazelnut Spread" in capsys.readouterr().out


def test_find_by_name_lists_matches(capsys):
    matches = [{"barcode": "1", "status": 1, "product": ITEM["product"]}]
    with patch("cli.requests.request", return_value=fake_response(matches)):
        assert cli.main(["find", "--name", "spread"]) == 0
    assert "Hazelnut Spread" in capsys.readouterr().out


def test_find_requires_argument(capsys):
    assert cli.main(["find"]) == 1


def test_import_command():
    with patch("cli.requests.request", return_value=fake_response(ITEM, 201)) as mock_request:
        assert cli.main(["import", "--barcode", "123", "--price", "100", "--stock", "5"]) == 0
    assert mock_request.call_args.args[1].endswith("/inventory/import")


def test_enrich_command():
    with patch("cli.requests.request", return_value=fake_response(ITEM)) as mock_request:
        assert cli.main(["enrich", "1"]) == 0
    assert mock_request.call_args.args[1].endswith("/inventory/1/enrich")


def test_connection_error_is_handled(capsys):
    with patch("cli.requests.request", side_effect=requests.exceptions.ConnectionError):
        assert cli.main(["list"]) == 1
    assert "cannot reach" in capsys.readouterr().out.lower()


def test_timeout_is_handled(capsys):
    with patch("cli.requests.request", side_effect=requests.exceptions.Timeout):
        assert cli.main(["list"]) == 1
    assert "too long" in capsys.readouterr().out.lower()