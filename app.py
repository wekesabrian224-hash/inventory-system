from flask import Flask, jsonify, request
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


if __name__ == "__main__":
    app.run(debug=True)
