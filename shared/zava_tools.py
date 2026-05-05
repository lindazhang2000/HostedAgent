"""Local function tools shared across the Zava specialist agents.

These mirror the tools in the original TechWorkshop-L300 workshop
(inventoryCheck, discountLogic, cart manipulation) but are pure Python
so each hosted-agent container can run them without external services.
For production replace with calls to Cosmos DB / inventory APIs.
"""

from __future__ import annotations

import json
import os
import random
import threading
from pathlib import Path
from typing import Annotated, Any

from agent_framework import tool
from pydantic import Field

_DATA = Path(__file__).resolve().parent.parent / "data"

# ---------------------------------------------------------------------------
# Cart persistence (Azure Storage Blob).
#
# Each hosted-agent container is ephemeral, so we cannot keep cart state in
# process memory: handoffs between specialist agents land on different
# containers and the in-memory list resets to empty. We persist a single JSON
# blob ("default.json") in a shared Storage account; AAD auth via the agent's
# managed identity.
# ---------------------------------------------------------------------------

_CART_BLOB_NAME = "default.json"
_blob_client_lock = threading.Lock()
_blob_client: Any = None


def _get_cart_blob():
    """Lazy-init a BlobClient pointing at the single demo cart blob.

    Lazy so non-cart agents (which don't set the env vars) keep importing
    this module without touching network/SDK code.
    """
    global _blob_client
    if _blob_client is not None:
        return _blob_client
    with _blob_client_lock:
        if _blob_client is not None:
            return _blob_client
        endpoint = os.environ["AZURE_STORAGE_BLOB_ENDPOINT"]
        container = os.environ.get("AZURE_STORAGE_CART_CONTAINER", "carts")
        # Imported lazily so the SDK isn't a hard dep for non-cart agents.
        from azure.identity import DefaultAzureCredential
        from azure.storage.blob import BlobServiceClient

        credential = DefaultAzureCredential()
        service = BlobServiceClient(account_url=endpoint, credential=credential)
        _blob_client = service.get_blob_client(container=container, blob=_CART_BLOB_NAME)
        return _blob_client


def _read_cart() -> list[dict[str, Any]]:
    from azure.core.exceptions import ResourceNotFoundError

    client = _get_cart_blob()
    try:
        data = client.download_blob().readall()
    except ResourceNotFoundError:
        return []
    if not data:
        return []
    try:
        payload = json.loads(data)
    except json.JSONDecodeError:
        return []
    return payload.get("items", []) if isinstance(payload, dict) else []


def _write_cart(items: list[dict[str, Any]]) -> None:
    client = _get_cart_blob()
    body = json.dumps({"items": items}).encode("utf-8")
    client.upload_blob(body, overwrite=True)


def _load_catalog() -> list[dict[str, Any]]:
    path = _DATA / "product_catalog.json"
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


@tool(approval_mode="never_require")
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


@tool(approval_mode="never_require")
def calculate_discount(
    customer_id: Annotated[str, Field(description="Customer ID, e.g. C001")],
) -> dict[str, Any]:
    """Return the loyalty discount percentage for a customer."""
    tier, percent = _LOYALTY_TIERS.get(customer_id, ("standard", 0))
    return {"customer_id": customer_id, "tier": tier, "discount_percentage": percent}


# Cart state is persisted in Azure Storage (see _read_cart / _write_cart above).
# We deliberately do NOT expose `session_id` as a tool argument: it would force
# the model to invent / ask for an id and would change across handoffs. For the
# demo we use a single shared blob; a real deployment would key by an
# authenticated user id (or a header propagated from the webapp).


@tool(approval_mode="never_require")
def add_to_cart(
    product_id: Annotated[str, Field(description="Product id to add")],
    quantity: Annotated[int, Field(description="Quantity, default 1")] = 1,
) -> dict[str, Any]:
    """Add a product to the cart."""
    items = _read_cart()
    for line in items:
        if line["product_id"] == product_id:
            line["quantity"] += quantity
            break
    else:
        items.append({"product_id": product_id, "quantity": quantity})
    _write_cart(items)
    return {"cart": items}


@tool(approval_mode="never_require")
def view_cart() -> dict[str, Any]:
    """Return the current contents of the cart."""
    return {"cart": _read_cart()}


@tool(approval_mode="never_require")
def clear_cart() -> dict[str, Any]:
    """Empty the cart."""
    _write_cart([])
    return {"cart": []}


@tool(approval_mode="never_require")
def list_products(
    category: Annotated[str | None, Field(description="Optional category filter")] = None,
) -> dict[str, Any]:
    """List Zava products, optionally filtered by category."""
    catalog = _load_catalog()
    if category:
        catalog = [p for p in catalog if p.get("category", "").lower() == category.lower()]
    return {"products": catalog[:25]}
