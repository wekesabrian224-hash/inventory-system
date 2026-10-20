"""Client for the OpenFoodFacts API: lookup by barcode or by product name."""
import requests

BASE_URL = "https://world.openfoodfacts.org"
HEADERS = {"User-Agent": "InventoryManagementSystem/1.0 (student project)"}
TIMEOUT = 10
FIELDS = "code,product_name,brands,ingredients_text"


class OpenFoodFactsError(Exception):
    """Raised when the external API cannot be reached or returns bad data."""


def _get(url, params=None):
    try:
        response = requests.get(url, params=params, headers=HEADERS, timeout=TIMEOUT)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        raise OpenFoodFactsError(f"OpenFoodFacts request failed: {exc}") from exc
    except ValueError as exc:
        raise OpenFoodFactsError("OpenFoodFacts returned invalid JSON") from exc


def _clean(product):
    """Keep only the fields we store."""
    return {
        "product_name": product.get("product_name", "") or "",
        "brands": product.get("brands", "") or "",
        "ingredients_text": product.get("ingredients_text", "") or "",
    }


def fetch_by_barcode(barcode):
    """Return {"status": 1, "product": {...}} or None if the barcode is not found."""
    barcode = str(barcode).strip()
    if not barcode.isdigit():
        return None
    data = _get(f"{BASE_URL}/api/v2/product/{barcode}.json", {"fields": FIELDS})
    if data.get("status") != 1 or not data.get("product"):
        return None
    return {"status": 1, "product": _clean(data["product"])}


def search_by_name(name, limit=5):
    """Return a list of {"barcode", "status", "product"} matches (empty list if none)."""
    if not name or not name.strip():
        return []
    params = {
        "search_terms": name,
        "search_simple": 1,
        "action": "process",
        "json": 1,
        "page_size": limit,
        "fields": FIELDS,
    }
    data = _get(f"{BASE_URL}/cgi/search.pl", params)
    results = []
    for product in data.get("products", []):
        if product.get("product_name"):
            results.append({
                "barcode": product.get("code", ""),
                "status": 1,
                "product": _clean(product),
            })
    return results