"""Inventory specialist."""

from __future__ import annotations

import asyncio

from shared.agent_host import build_agent, serve
from shared.zava_tools import inventory_check

INSTRUCTIONS = """
You are the Zava Inventory specialist. When a user asks about stock for one
or more products, call `inventory_check` with the matching product IDs and
report stock levels and warehouse locations.

Reply in JSON: {"answer": str, "items": [{"id": str, "name": str,
"in_stock": int, "location": str}]}.
""".strip()


async def main() -> None:
    agent = build_agent(
        name="inventory",
        instructions=INSTRUCTIONS,
        tools=[inventory_check],
    )
    await serve(agent)


if __name__ == "__main__":
    asyncio.run(main())
