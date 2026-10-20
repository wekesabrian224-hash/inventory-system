# Mock database: a list of dicts that simulates storage while the server runs.
# Resets every time Flask restarts, which is fine for this lab.

inventory = [
    {
        "id": 1,
        "barcode": "3017620422003",
        "price": 650.00,   # our own business field (KES)
        "stock": 24,       # our own business field
        "status": 1,       # mirrors OpenFoodFacts' response shape
        "product": {       # the block that resembles OpenFoodFacts data
            "product_name": "Hazelnut Spread",
            "brands": "Nutella",
            "ingredients_text": "Sugar, palm oil, hazelnuts, cocoa, skimmed milk powder",
        },
    },
    {
        "id": 2,
        "barcode": "5449000000996",
        "price": 120.00,
        "stock": 80,
        "status": 1,
        "product": {
            "product_name": "Cola Soft Drink",
            "brands": "Coca-Cola",
            "ingredients_text": "Carbonated water, sugar, colour, acidity regulator, flavourings",
        },
    },
]


def get_next_id():
    """Return the next free ID. Using max()+1 avoids reusing the ID of a deleted item."""
    return max((item["id"] for item in inventory), default=0) + 1


def find_item(item_id):
    """Return the item with this ID, or None if it doesn't exist."""
    return next((item for item in inventory if item["id"] == item_id), None)