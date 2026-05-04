"""Local function tools shared across the Zava specialist agents.

These mirror the tools in the original TechWorkshop-L300 workshop
(inventoryCheck, discountLogic, cart manipulation) but are pure Python
so each hosted-agent container can run them without external services.
For production replace with calls to Cosmos DB / inventory APIs.
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Annotated, Any

from pydantic import Field

_DATA = Path(__file__).resolve().parent.parent / "data"


def _load_catalog() -> list[dict[str, Any]]:
    path = _DATA / "product_catalog.json"
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def inventory_check(
    product_ids: Annotated[list[str], Field(description="Zava product IDs, e.g. ['PROD0045']")],
) -> dict[str, Any]:
    """Look up stock level + warehouse location for the requested product IDs."""
    catalog = {p["id"]: p for p in _load_catalog()}
    rng = random.Random(42)
    results = []
    for pid in product_ids:
        item = catalog.get(pid)
        results.append(
            {
                "id": pid,
                "name": item["name"] if item else "Unknown product",
                "in_stock": rng.randint(0, 50),
                "location": rng.choice(["Seattle DC", "Dallas DC", "Newark DC"]),
            }
        )
    return {"items": results}


_LOYALTY_TIERS = {
    "C001": ("gold", 20),
    "C002": ("silver", 10),
    "C003": ("bronze", 5),
}


def calculate_discount(
    customer_id: Annotated[str, Field(description="Customer ID, e.g. C001")],
) -> dict[str, Any]:
    """Return the loyalty discount percentage for a customer."""
    tier, percent = _LOYALTY_TIERS.get(customer_id, ("standard", 0))
    return {"customer_id": customer_id, "tier": tier, "discount_percentage": percent}


# In-memory cart keyed by session - good enough for the workshop demo.
_CART: dict[str, list[dict[str, Any]]] = {}


def add_to_cart(
    session_id: Annotated[str, Field(description="Conversation/session id")],
    product_id: Annotated[str, Field(description="Product id to add")],
    quantity: Annotated[int, Field(description="Quantity, default 1")] = 1,
) -> dict[str, Any]:
    """Add a product to the session cart."""
    cart = _CART.setdefault(session_id, [])
    for line in cart:
        if line["product_id"] == product_id:
            line["quantity"] += quantity
            break
    else:
        cart.append({"product_id": product_id, "quantity": quantity})
    return {"cart": cart}


def view_cart(
    session_id: Annotated[str, Field(description="Conversation/session id")],
) -> dict[str, Any]:
    """Return the current contents of the session cart."""
    return {"cart": _CART.get(session_id, [])}


def clear_cart(
    session_id: Annotated[str, Field(description="Conversation/session id")],
) -> dict[str, Any]:
    """Empty the session cart."""
    _CART.pop(session_id, None)
    return {"cart": []}


def list_products(
    category: Annotated[str | None, Field(description="Optional category filter")] = None,
) -> dict[str, Any]:
    """List Zava products, optionally filtered by category."""
    catalog = _load_catalog()
    if category:
        catalog = [p for p in catalog if p.get("category", "").lower() == category.lower()]
    return {"products": catalog[:25]}
