# Inventory Management System

A Flask REST API for managing retail inventory, with OpenFoodFacts integration and a command-line interface (CLI).

## Features
- CRUD (Create, Read, Update, Delete) endpoints for inventory items
- Fetch product details from the OpenFoodFacts API by barcode or name
- Import products from OpenFoodFacts straight into the inventory
- CLI for every operation, with error handling for bad input and API failures
- Test suite using pytest and unittest.mock

## Installation

```bash
git clone https://github.com/wekesabrian-224hash/inventory-system.git
cd inventory-system
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Running

Start the API (terminal 1):

```bash
python app.py
```

Use the CLI (terminal 2):

```bash
python cli.py list
```

The API runs at `http://127.0.0.1:5000`. Data is stored in an in-memory list (`data.py`), so it resets when the server restarts.

## Project structure

```
app.py             Flask routes
data.py            Mock database array and helpers
openfoodfacts.py   OpenFoodFacts API client
cli.py             Command-line interface
tests/             pytest test suites
```

## Item format

```json
{
  "id": 1,
  "barcode": "3017620422003",
  "price": 650.0,
  "stock": 24,
  "status": 1,
  "product": {
    "product_name": "Hazelnut Spread",
    "brands": "Nutella",
    "ingredients_text": "Sugar, palm oil, hazelnuts, cocoa"
  }
}
```

`price` and `stock` are our own business data; `product` mirrors the OpenFoodFacts response.

## API endpoints

| Method | Endpoint | Description | Success | Errors |
|---|---|---|---|---|
| GET | `/inventory` | List all items | 200 | |
| GET | `/inventory/<id>` | Get one item | 200 | 404 |
| POST | `/inventory` | Add an item (`product.product_name` required) | 201 | 400 |
| PATCH | `/inventory/<id>` | Update price, stock, barcode or product fields | 200 | 400, 404 |
| DELETE | `/inventory/<id>` | Delete an item | 200 | 404 |
| GET | `/lookup?barcode=` or `?name=` | Search OpenFoodFacts (nothing saved) | 200 | 400, 404, 502 |
| POST | `/inventory/import` | Fetch by barcode and add to inventory | 201 | 400, 404, 502 |
| POST | `/inventory/<id>/enrich` | Fill an item's details from OpenFoodFacts | 200 | 404, 502 |

Errors are returned as `{"error": "message"}`. A `502` means OpenFoodFacts could not be reached.

### Example

```bash
curl -X POST http://127.0.0.1:5000/inventory \
  -H "Content-Type: application/json" \
  -d '{"price": 50, "stock": 10, "product": {"product_name": "Biscuits"}}'
```

## CLI usage

```bash
python cli.py list                                   # all items
python cli.py view 1                                 # one item
python cli.py add --name "Milk" --brand "Brookside" --price 60 --stock 30
python cli.py update 1 --price 700 --stock 20        # price and/or stock
python cli.py delete 2
python cli.py find --barcode 3017620422003           # search OpenFoodFacts by barcode
python cli.py find --name "almond milk"              # search by name
python cli.py import --barcode 3017620422003 --price 650 --stock 10
python cli.py enrich 1                               # fill details from OpenFoodFacts
```

## Running tests

```bash
pytest -v
```

External API calls are mocked with `unittest.mock`, so tests need no internet connection.

## Git workflow
Each feature was built on its own branch (`feature/crud-api`, `feature/external-api`, `feature/cli`, `feature/tests`, `docs/readme`), merged into `main` through a pull request, and the branch deleted.