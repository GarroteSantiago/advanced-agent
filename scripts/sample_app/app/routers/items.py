"""A single in-memory resource router: items."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/items", tags=["items"])

_ITEMS: dict[int, "Item"] = {}


class Item(BaseModel):
    id: int
    name: str
    price: float


@router.get("")
def list_items() -> list[Item]:
    return list(_ITEMS.values())


@router.post("", status_code=201)
def create_item(item: Item) -> Item:
    if item.id in _ITEMS:
        raise HTTPException(status_code=409, detail="item already exists")
    _ITEMS[item.id] = item
    return item


@router.get("/{item_id}")
def get_item(item_id: int) -> Item:
    if item_id not in _ITEMS:
        raise HTTPException(status_code=404, detail="item not found")
    return _ITEMS[item_id]
