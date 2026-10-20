"""Command-line interface for the Inventory Management System.

Usage examples:
    python cli.py list
    python cli.py view 1
    python cli.py add --name "Milk" --brand "Brookside" --price 60 --stock 30
    python cli.py update 1 --price 700 --stock 20
    python cli.py delete 2
    python cli.py find --barcode 3017620422003
    python cli.py find --name "almond milk"
    python cli.py import --barcode 3017620422003 --price 650 --stock 10
    python cli.py enrich 1
"""
import argparse
import sys

import requests

API_URL = "http://127.0.0.1:5000"
TIMEOUT = 15


def call_api(method, path, **kwargs):
    """Send a request to the Flask API. Returns parsed JSON, or None after printing an error."""
    try:
        response = requests.request(method, f"{API_URL}{path}", timeout=TIMEOUT, **kwargs)
    except requests.exceptions.ConnectionError:
        print("Error: cannot reach the API. Start it first with: python app.py")
        return None
    except requests.exceptions.Timeout:
        print("Error: the API took too long to respond.")
        return None
    except requests.exceptions.RequestException as exc:
        print(f"Error: request failed ({exc})")
        return None

    try:
        body = response.json()
    except ValueError:
        print(f"Error: unexpected response from API (status {response.status_code})")
        return None

    if not response.ok:
        message = body.get("error", "Unknown error") if isinstance(body, dict) else "Unknown error"
        print(f"Error {response.status_code}: {message}")
        return None
    return body


def print_item(item):
    product = item.get("product", {})
    print(
        f"[{item.get('id')}] {product.get('product_name', '?')} | "
        f"{product.get('brands', '')} | KES {float(item.get('price', 0)):.2f} | "
        f"stock: {item.get('stock', 0)} | barcode: {item.get('barcode', '')}"
    )


def print_product(result):
    product = result.get("product", {})
    print(f"Name:        {product.get('product_name', '')}")
    print(f"Brand:       {product.get('brands', '')}")
    print(f"Ingredients: {product.get('ingredients_text', '') or 'N/A'}")
    if result.get("barcode"):
        print(f"Barcode:     {result['barcode']}")
    print("-" * 40)


def cmd_list(args):
    items = call_api("GET", "/inventory")
    if items is None:
        return 1
    if not items:
        print("Inventory is empty.")
        return 0
    for item in items:
        print_item(item)
    return 0


def cmd_view(args):
    item = call_api("GET", f"/inventory/{args.id}")
    if item is None:
        return 1
    print_item(item)
    print(f"    Ingredients: {item['product'].get('ingredients_text') or 'N/A'}")
    return 0


def cmd_add(args):
    payload = {
        "barcode": args.barcode,
        "price": args.price,
        "stock": args.stock,
        "product": {
            "product_name": args.name,
            "brands": args.brand,
            "ingredients_text": args.ingredients,
        },
    }
    item = call_api("POST", "/inventory", json=payload)
    if item is None:
        return 1
    print("Item added:")
    print_item(item)
    return 0


def cmd_update(args):
    payload = {}
    if args.price is not None:
        payload["price"] = args.price
    if args.stock is not None:
        payload["stock"] = args.stock
    if not payload:
        print("Error: provide --price and/or --stock.")
        return 1
    item = call_api("PATCH", f"/inventory/{args.id}", json=payload)
    if item is None:
        return 1
    print("Item updated:")
    print_item(item)
    return 0


def cmd_delete(args):
    result = call_api("DELETE", f"/inventory/{args.id}")
    if result is None:
        return 1
    print(result.get("message", "Item deleted."))
    return 0


def cmd_find(args):
    if not args.barcode and not args.name:
        print("Error: provide --barcode or --name.")
        return 1
    params = {"barcode": args.barcode} if args.barcode else {"name": args.name}
    result = call_api("GET", "/lookup", params=params)
    if result is None:
        return 1
    if isinstance(result, list):
        if not result:
            print("No products found.")
            return 0
        for match in result:
            print_product(match)
    else:
        print_product(result)
    return 0


def cmd_import(args):
    payload = {"barcode": args.barcode, "price": args.price, "stock": args.stock}
    item = call_api("POST", "/inventory/import", json=payload)
    if item is None:
        return 1
    print("Imported from OpenFoodFacts:")
    print_item(item)
    return 0


def cmd_enrich(args):
    payload = {"name": args.name} if args.name else {}
    item = call_api("POST", f"/inventory/{args.id}/enrich", json=payload)
    if item is None:
        return 1
    print("Item enriched:")
    print_item(item)
    print(f"    Ingredients: {item['product'].get('ingredients_text') or 'N/A'}")
    return 0


def build_parser():
    parser = argparse.ArgumentParser(description="Inventory Management CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("list", help="List all items")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("view", help="View one item")
    p.add_argument("id", type=int)
    p.set_defaults(func=cmd_view)

    p = sub.add_parser("add", help="Add a new item")
    p.add_argument("--name", required=True)
    p.add_argument("--brand", default="")
    p.add_argument("--ingredients", default="")
    p.add_argument("--barcode", default="")
    p.add_argument("--price", type=float, default=0.0)
    p.add_argument("--stock", type=int, default=0)
    p.set_defaults(func=cmd_add)

    p = sub.add_parser("update", help="Update price and/or stock")
    p.add_argument("id", type=int)
    p.add_argument("--price", type=float)
    p.add_argument("--stock", type=int)
    p.set_defaults(func=cmd_update)

    p = sub.add_parser("delete", help="Delete an item")
    p.add_argument("id", type=int)
    p.set_defaults(func=cmd_delete)

    p = sub.add_parser("find", help="Find a product on OpenFoodFacts")
    p.add_argument("--barcode")
    p.add_argument("--name")
    p.set_defaults(func=cmd_find)

    p = sub.add_parser("import", help="Import a product from OpenFoodFacts into inventory")
    p.add_argument("--barcode", required=True)
    p.add_argument("--price", type=float, default=0.0)
    p.add_argument("--stock", type=int, default=0)
    p.set_defaults(func=cmd_import)

    p = sub.add_parser("enrich", help="Fill an item's details from OpenFoodFacts")
    p.add_argument("id", type=int)
    p.add_argument("--name", help="Search by this name if the item has no barcode")
    p.set_defaults(func=cmd_enrich)

    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())