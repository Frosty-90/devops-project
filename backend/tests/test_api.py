import os
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
if os.path.exists("test.db"):
    os.remove("test.db")  # fresh test database every run, never the real PostgreSQL

from fastapi.testclient import TestClient
from app.db import Base, engine
from app.main import app

Base.metadata.create_all(bind=engine)

client = TestClient(app)

def new_product(sku, **fields):
    response = client.post("/api/products", json={"sku": sku, "name": f"Product {sku}", **fields})
    assert response.status_code == 201, response.text
    return response.json()

def test_health():
    assert client.get("/health").json() == {"status": "UP"}

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["service"] == "StockPilot Inventory API"

def test_create_product():
    product = new_product("KB-001", category="Peripherals", quantity=40, reorder_level=10, unit_price=49.99)
    assert product["name"] == "Product KB-001"
    assert product["stock_status"] == "IN_STOCK"

def test_duplicate_sku_rejected():
    new_product("DUP-001")
    assert client.post("/api/products", json={"sku": "DUP-001", "name": "Again"}).status_code == 409

def test_negative_quantity_rejected():
    response = client.post("/api/products", json={"sku": "NEG-001", "name": "Bad", "quantity": -5})
    assert response.status_code == 422

def test_stock_status_thresholds():
    assert new_product("ST-1", quantity=0)["stock_status"] == "OUT_OF_STOCK"
    assert new_product("ST-2", quantity=5, reorder_level=5)["stock_status"] == "LOW_STOCK"
    assert new_product("ST-3", quantity=6, reorder_level=5)["stock_status"] == "IN_STOCK"

def test_update_product():
    product = new_product("UPD-001", unit_price=10)
    response = client.put(f"/api/products/{product['id']}", json={"unit_price": 12.5, "supplier": "Acme"})
    assert response.status_code == 200
    assert response.json()["unit_price"] == 12.5
    assert response.json()["supplier"] == "Acme"
    assert response.json()["sku"] == "UPD-001"

def test_adjust_stock_receive_and_ship():
    product = new_product("ADJ-001", quantity=10, reorder_level=3)
    received = client.post(f"/api/products/{product['id']}/adjust", json={"delta": 5}).json()
    assert received["quantity"] == 15
    shipped = client.post(f"/api/products/{product['id']}/adjust", json={"delta": -13}).json()
    assert shipped["quantity"] == 2
    assert shipped["stock_status"] == "LOW_STOCK"

def test_adjust_stock_cannot_go_negative():
    product = new_product("ADJ-002", quantity=3)
    response = client.post(f"/api/products/{product['id']}/adjust", json={"delta": -4})
    assert response.status_code == 400
    assert client.get(f"/api/products/{product['id']}").json()["quantity"] == 3

def test_delete_product():
    product = new_product("DEL-001")
    assert client.delete(f"/api/products/{product['id']}").status_code == 204
    assert client.get(f"/api/products/{product['id']}").status_code == 404

def test_missing_product_returns_404():
    assert client.get("/api/products/999999").status_code == 404
    assert client.post("/api/products/999999/adjust", json={"delta": 1}).status_code == 404

def test_stats():
    before = client.get("/api/products/stats").json()
    new_product("STAT-1", quantity=4, reorder_level=10, unit_price=2.5)
    new_product("STAT-2", quantity=0)
    after = client.get("/api/products/stats").json()
    assert after["products"] == before["products"] + 2
    assert after["units"] == before["units"] + 4
    assert after["lowStock"] == before["lowStock"] + 1
    assert after["outOfStock"] == before["outOfStock"] + 1
    assert round(after["inventoryValue"] - before["inventoryValue"], 2) == 10.0

def test_list_products_sorted_by_name():
    names = [p["name"] for p in client.get("/api/products").json()]
    assert names == sorted(names)
