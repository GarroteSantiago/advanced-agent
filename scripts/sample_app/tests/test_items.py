"""A minimal test exercising the items router."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_create_then_get_item() -> None:
    created = client.post("/items", json={"id": 1, "name": "widget", "price": 9.99})
    assert created.status_code == 201

    fetched = client.get("/items/1")
    assert fetched.status_code == 200
    assert fetched.json()["name"] == "widget"


def test_missing_item_is_404() -> None:
    assert client.get("/items/999").status_code == 404
