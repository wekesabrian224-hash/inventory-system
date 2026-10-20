from flask import Flask, jsonify, request

import openfoodfacts
from openfoodfacts import OpenFoodFactsError
from data import inventory, find_item, get_next_id

app = Flask(__name__)


def error(message, status):
    """Return a consistent JSON error so the CLI can always parse failures the same way."""
    return jsonify({"error": message}), status


def validate_numbers(data):
    """Check price/stock if present. Returns an error message, or None if valid."""
    if "price" in data:
        if not isinstance(data["price"], (int, float)) or isinstance(data["price"], bool) or data["price"] < 0:
            return "price must be a non-negative number"
    if "stock" in data:
        if not isinstance(data["stock"], int) or isinstance(data["stock"], bool) or data["stock"] < 0:
            return "stock must be a non-negative integer"
    return None


# READ ALL
@app.route("/inventory", methods=["GET"])
def get_inventory():
    return jsonify(inventory), 200


# READ ONE
@app.route("/inventory/<int:item_id>", methods=["GET"])
def get_item(item_id):
    item = find_item(item_id)
    if item is None:
        return error(f"Item {item_id} not found", 404)
    return jsonify(item), 200


# CREATE
@app.route("/inventory", methods=["POST"])
def add_item():
    data = request.get_json(silent=True)
    if not data:
        return error("Request body must be valid JSON", 400)

    product = data.get("product")
    if not isinstance(product, dict) or not product.get("product_name"):
        return error("product.product_name is required", 400)

    problem = validate_numbers(data)
    if problem:
        return error(problem, 400)

    new_item = {
        "id": get_next_id(),
        "barcode": data.get("barcode", ""),
        "price": data.get("price", 0),
        "stock": data.get("stock", 0),
        "status": 1,
        "product": {
            "product_name": product["product_name"],
            "brands": product.get("brands", ""),
            "ingredients_text": product.get("ingredients_text", ""),
        },
    }
    inventory.append(new_item)
    return jsonify(new_item), 201


# UPDATE (partial)
@app.route("/inventory/<int:item_id>", methods=["PATCH"])
def update_item(item_id):
    item = find_item(item_id)
    if item is None:
        return error(f"Item {item_id} not found", 404)

    data = request.get_json(silent=True)
    if not data:
        return error("Request body must be valid JSON", 400)

    problem = validate_numbers(data)
    if problem:
        return error(problem, 400)

    # Only update fields the client actually sent (that's what makes it PATCH, not PUT)
    for field in ("price", "stock", "barcode"):
        if field in data:
            item[field] = data[field]
    if isinstance(data.get("product"), dict):
        item["product"].update(data["product"])

    return jsonify(item), 200


# DELETE
@app.route("/inventory/<int:item_id>", methods=["DELETE"])
def delete_item(item_id):
    item = find_item(item_id)
    if item is None:
        return error(f"Item {item_id} not found", 404)
    inventory.remove(item)
    return jsonify({"message": f"Item {item_id} deleted"}), 200


# HELPER: search OpenFoodFacts without saving anything
@app.route("/lookup", methods=["GET"])
def lookup():
    barcode = request.args.get("barcode")
    name = request.args.get("name")
    if not barcode and not name:
        return error("Provide a 'barcode' or 'name' query parameter", 400)
    try:
        if barcode:
            result = openfoodfacts.fetch_by_barcode(barcode)
            if result is None:
                return error("No product found for that barcode", 404)
            return jsonify(result), 200
        return jsonify(openfoodfacts.search_by_name(name)), 200
    except OpenFoodFactsError as exc:
        return error(str(exc), 502)


# IMPORT: fetch from OpenFoodFacts by barcode and add to the inventory array
@app.route("/inventory/import", methods=["POST"])
def import_item():
    data = request.get_json(silent=True)
    if not data or not data.get("barcode"):
        return error("barcode is required", 400)
    problem = validate_numbers(data)
    if problem:
        return error(problem, 400)
    try:
        result = openfoodfacts.fetch_by_barcode(data["barcode"])
    except OpenFoodFactsError as exc:
        return error(str(exc), 502)
    if result is None:
        return error("No product found for that barcode", 404)

    new_item = {
        "id": get_next_id(),
        "barcode": str(data["barcode"]),
        "price": data.get("price", 0),
        "stock": data.get("stock", 0),
        "status": 1,
        "product": result["product"],
    }
    inventory.append(new_item)
    return jsonify(new_item), 201


# ENRICH: fill an existing item's product details from OpenFoodFacts
@app.route("/inventory/<int:item_id>/enrich", methods=["POST"])
def enrich_item(item_id):
    item = find_item(item_id)
    if item is None:
        return error(f"Item {item_id} not found", 404)
    data = request.get_json(silent=True) or {}
    try:
        if item.get("barcode"):
            result = openfoodfacts.fetch_by_barcode(item["barcode"])
        else:
            name = data.get("name") or item["product"].get("product_name", "")
            matches = openfoodfacts.search_by_name(name)
            result = matches[0] if matches else None
            if result and result.get("barcode"):
                item["barcode"] = result["barcode"]
    except OpenFoodFactsError as exc:
        return error(str(exc), 502)
    if result is None:
        return error("No match found on OpenFoodFacts", 404)

    for key, value in result["product"].items():
        if value:
            item["product"][key] = value
    return jsonify(item), 200


if __name__ == "__main__":
    app.run(debug=True)
