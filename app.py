import openfoodfacts
from openfoodfacts import OpenFoodFactsError



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